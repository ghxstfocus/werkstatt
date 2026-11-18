"""Independent, frozen acceptance tests for high-risk Python changes.

The Spec Builder writes tests into a run-private directory below
``.werkstatt``. The code Builder receives neither those files nor their
assertions; it receives only the approved goal and implementation tasks.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any

from werkstatt.audit import audit

_SPEC_SYSTEM = """Du bist der unabhaengige Spec-Builder. Schreibe pytest-Tests,
die ausschliesslich beobachtbares, vom Nutzer gefordertes Verhalten pruefen.
Erstelle mindestens einen Test pro Akzeptanzkriterium und sinnvolle
Negativfaelle. Teste keine Implementierungsdetails und keine Konfiguration,
ausser der Auftrag fordert sie ausdruecklich. Die Tests muessen den aktuellen
Quellstand mit AssertionError rot machen, wenn das geforderte Verhalten fehlt.
Verwende nur Imports des Projektcodes und pytest. Keine Datei-, Netzwerk-,
Prozess- oder Umgebungszugriffe. Antworte als JSON: {\"tests\":[{\"id\":
\"AC1\",\"source\":\"vollstaendiger Python-Testcode\"}]}."""

_VALIDATOR_SYSTEM = """Du bist ein unabhaengiger Spec-Validator. Pruefe fuer jeden
Akzeptanzpunkt, ob der zugehoerige pytest-Code das geforderte Verhalten und
Negativfaelle prueft, ohne Implementierungsdetails zu fixieren. Die Tests
werden einem separaten Code-Builder nicht gezeigt. Antworte ausschliesslich
als JSON {\"complete\":true|false,\"uncovered\":[\"AC...\"],
\"invalid_tests\":[\"test_id: reason\"]}. Erfinde keine Anforderungen."""

_RISK_MARKER = re.compile(
    r"\b(?:security|auth\w*|credential\w*|permission\w*|berechtig\w*|"
    r"schema\w*|migration\w*|database|datenbank|transaction\w*|"
    r"concurr\w*|parallel\w*|async\w*|lease\w*|api|schnittstell\w*|"
    r"breaking\w*|kompatib\w*|refactor\w*|mehrere\s+datei\w*|"
    r"multi[- ]file|mehrere\s+module\w*|kritisch\w*|komplex\w*|"
    r"complex\w*|risk\w*|risik\w*|regress\w*|mehrdeutig\w*|"
    r"ambiguous|mehrschrittig\w*|multi[- ]step)\b",
    re.IGNORECASE,
)
_FORBIDDEN_IMPORTS = frozenset({
    "builtins", "ctypes", "importlib", "multiprocessing", "os",
    "pathlib", "requests", "shutil", "socket", "subprocess", "sys",
    "tempfile", "urllib",
})
_FORBIDDEN_CALLS = frozenset({
    "__import__", "breakpoint", "compile", "eval", "exec", "input",
    "open", "system", "popen", "run", "Popen", "check_call",
    "check_output", "urlopen",
})
MAX_SPEC_FILES = 8
MAX_SPEC_FILE_CHARS = 12_000
MAX_SPEC_TOTAL_CHARS = 48_000


def requires_spec_first(
    goal: str, *, criteria_count: int | None = None,
) -> bool:
    """Use Spec-First only for a bounded set of high-risk/ambiguous goals."""
    many_criteria = (
        isinstance(criteria_count, int)
        and not isinstance(criteria_count, bool)
        and criteria_count >= 3
    )
    return many_criteria or (
        isinstance(goal, str) and bool(_RISK_MARKER.search(goal))
    )


def _validate_test_source(
    source: object, *, allowed_modules: set[str] | None = None,
) -> tuple[bool, str, str | None]:
    if not isinstance(source, str) or not source.strip():
        return False, "empty_test_source", None
    if len(source) > MAX_SPEC_FILE_CHARS:
        return False, "test_source_too_large", None
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False, "test_source_syntax_error", None
    test_functions = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    if len(test_functions) != 1 or isinstance(
        test_functions[0], ast.AsyncFunctionDef,
    ):
        return False, "exactly_one_sync_test_function_required", None
    if any(
        isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef))
        and not (isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
        for node in tree.body
    ):
        return False, "unsupported_module_definition", None
    imported_names: set[str] = set()
    imported_modules: set[str] = set()
    modules = allowed_modules or set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name != "pytest" and item.name not in modules:
                    return False, "import_outside_current_source_evidence", None
                imported_names.add(item.asname or item.name.split(".", 1)[0])
                imported_modules.add(item.asname or item.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if (
                node.level
                or (module != "pytest" and module not in modules)
                or any(item.name == "*" for item in node.names)
            ):
                return False, "import_outside_current_source_evidence", None
            imported_names.update(item.asname or item.name for item in node.names)
            imported_modules.add(node.module or "")
    if any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _FORBIDDEN_CALLS
        for node in ast.walk(tree)
    ):
        return False, "forbidden_test_operation", None
    for ast_node in ast.walk(tree):
        if isinstance(ast_node, (ast.Import, ast.ImportFrom)):
            names = (
                [item.name.split(".", 1)[0] for item in ast_node.names]
                if isinstance(ast_node, ast.Import)
                else [(ast_node.module or "").split(".", 1)[0]]
            )
            if any(name in _FORBIDDEN_IMPORTS for name in names):
                return False, "forbidden_test_import", None
        if isinstance(ast_node, ast.Attribute) and ast_node.attr.startswith("__"):
            return False, "dunder_attribute_access", None
        if isinstance(ast_node, ast.Call):
            name = (
                ast_node.func.id if isinstance(ast_node.func, ast.Name)
                else ast_node.func.attr if isinstance(ast_node.func, ast.Attribute)
                else ""
            )
            root = (
                ast_node.func.value.id
                if isinstance(ast_node.func, ast.Attribute)
                and isinstance(ast_node.func.value, ast.Name) else ""
            )
            if name in _FORBIDDEN_CALLS or root in _FORBIDDEN_IMPORTS:
                return False, "forbidden_test_operation", None
            allowed_call = (
                isinstance(ast_node.func, ast.Name)
                and ast_node.func.id in imported_names
            ) or (
                isinstance(ast_node.func, ast.Attribute)
                and isinstance(ast_node.func.value, ast.Name)
                and ast_node.func.value.id in imported_modules
                and (
                    ast_node.func.value.id != "pytest"
                    or ast_node.func.attr in {"raises", "fail", "skip"}
                )
            )
            if not allowed_call:
                return False, "unapproved_test_call", None
    if any(
        not isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef))
        for node in tree.body
    ):
        return False, "module_level_execution_not_allowed", None
    return True, "ok", test_functions[0].name


def _source_evidence(state: Any) -> list[dict[str, str]]:
    """Read hash-current API surfaces, never implementation bodies."""
    root = Path(state.project_dir).resolve(strict=True)
    context = getattr(state, "explorer_context", {})
    raw_files = context.get("key_files") if isinstance(context, dict) else None
    records: list[dict[str, str]] = []
    total = 0
    for item in raw_files if isinstance(raw_files, list) else []:
        if not isinstance(item, dict):
            continue
        relative = item.get("file")
        if (
            not isinstance(relative, str)
            or relative.startswith("tests/")
            or not relative.endswith(".py")
        ):
            continue
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            continue
        try:
            current = (root / path).resolve(strict=True)
            current.relative_to(root)
            if not current.is_file() or current.stat().st_size > 24_000:
                continue
            raw = current.read_bytes()
            source = raw.decode("utf-8", errors="strict")
            tree = ast.parse(source)
        except (OSError, UnicodeError, RuntimeError, ValueError):
            continue
        except SyntaxError:
            continue
        if len(source) > 24_000:
            continue
        expected = item.get("source_sha256")
        digest = hashlib.sha256(raw).hexdigest()
        if item.get("source_complete") is not True or expected != digest:
            continue
        signatures: list[str] = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    signatures.append(
                        f"def {node.name}({ast.unparse(node.args)})"
                        + (
                            f" -> {ast.unparse(node.returns)}"
                            if node.returns is not None else ""
                        )
                    )
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                signatures.append(f"class {node.name}")
                for member in node.body:
                    if (
                        isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and not member.name.startswith("_")
                    ):
                        signatures.append(
                            f"  def {node.name}.{member.name}"
                            f"({ast.unparse(member.args)})"
                            + (
                                f" -> {ast.unparse(member.returns)}"
                                if member.returns is not None else ""
                            )
                        )
        surface = "\n".join(signatures)
        if not surface or len(surface) > 6_000 or total + len(surface) > 12_000:
            continue
        records.append({
            "path": path.as_posix(),
            "sha256": digest,
            "surface_sha256": hashlib.sha256(surface.encode()).hexdigest(),
            "source": surface,
        })
        total += len(surface)
        if len(records) >= 4:
            break
    return records


def _criteria(state: Any) -> list[str]:
    values = getattr(state, "akzeptanzkriterien", None)
    if not isinstance(values, list):
        return []
    return [str(item).strip()[:1000] for item in values if str(item).strip()][:20]


def _json_reply(reply: Any) -> dict[str, Any] | None:
    if not getattr(reply, "ok", False):
        return None
    content = getattr(reply, "content", "")
    if not isinstance(content, str):
        return None
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        parsed = json.loads(content[start:end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def build_spec_test_checkpoint(
    state: Any, phase_state: Any, *, goal: str,
) -> dict[str, Any] | None:
    """Generate, independently validate, hash, and persist spec tests."""
    run_id = getattr(state, "run_id", None)
    api_key = getattr(state, "api_key", None)
    criteria = _criteria(state)
    sources = _source_evidence(state)
    if (
        not isinstance(run_id, str) or not run_id
        or not isinstance(api_key, str) or not api_key.strip()
        or not criteria or not sources
    ):
        return None
    from werkstatt.agent import ask_llm

    source_evidence = [
        {key: value for key, value in record.items() if key != "source"}
        | {"source": record["source"]}
        for record in sources
    ]
    payload = {
        "goal": goal,
        "acceptance_criteria": criteria,
        "current_public_api_surfaces": source_evidence,
        "required_test_ids": [f"AC{i + 1}" for i in range(len(criteria))],
    }
    encoded_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if len(_SPEC_SYSTEM) + len(encoded_payload) > 18_000:
        return None
    audit(
        "loop_phase",
        {
            "phase": "spec_builder_context_budget",
            "status": "included",
            "system_chars": len(_SPEC_SYSTEM),
            "user_chars": len(encoded_payload),
            "actual_chars": len(_SPEC_SYSTEM) + len(encoded_payload),
            "required_context_complete": True,
            "source_file_count": len(sources),
            "criterion_count": len(criteria),
        },
        state.project_dir,
        state.project_name,
        run_id=run_id,
    )
    manifest = {
        "budget_event": "spec_builder_context_budget",
        "required_context_complete": True,
        "user_sha256": hashlib.sha256(encoded_payload.encode()).hexdigest(),
        "system_sha256": hashlib.sha256(_SPEC_SYSTEM.encode()).hexdigest(),
        "source": "goal_criteria_and_hash_validated_public_api_signatures",
    }
    reply = ask_llm(
        api_key, _SPEC_SYSTEM, encoded_payload, model="deepseek-chat",
        temperature=0.0, timeout=60, max_tokens=6000, state=state,
        aufgabe="spec-builder", rolle="spec-builder", heartbeat=False,
        context_manifest=manifest,
    )
    generated = _json_reply(reply)
    raw_tests = generated.get("tests") if isinstance(generated, dict) else None
    if (
        not isinstance(raw_tests, list)
        or not 1 <= len(raw_tests) <= MAX_SPEC_FILES
        or any(
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not isinstance(item.get("source"), str)
            for item in raw_tests
        )
    ):
        return None
    allowed_modules = {
        ".".join(
            PurePosixPath(record["path"]).with_suffix("").parts[:-1]
            if PurePosixPath(record["path"]).name == "__init__.py"
            else PurePosixPath(record["path"]).with_suffix("").parts
        )
        for record in sources
        if record["path"].endswith(".py")
        and all(
            segment.isidentifier()
            for segment in PurePosixPath(record["path"]).with_suffix("").parts
            if segment != "__init__"
        )
    }
    normalized: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_test_names: set[str] = set()
    for item in raw_tests:
        test_id = item["id"]
        source = item["source"]
        valid, _reason, test_name = _validate_test_source(
            source, allowed_modules=allowed_modules,
        )
        if (
            not re.fullmatch(r"AC[1-9][0-9]*", test_id)
            or test_id in seen_ids
            or not valid or test_name is None
            or test_name in seen_test_names
        ):
            return None
        seen_ids.add(test_id)
        seen_test_names.add(test_name)
        normalized.append({
            "id": test_id, "source": source, "test_name": test_name,
        })
    if seen_ids != {f"AC{i + 1}" for i in range(len(criteria))}:
        return None

    validator_payload = json.dumps({
        "goal": goal,
        "acceptance_criteria": criteria,
        "generated_tests": normalized,
    }, ensure_ascii=False, sort_keys=True)
    validator_manifest = {
        "budget_event": "spec_validator_context_budget",
        "required_context_complete": True,
        "user_sha256": hashlib.sha256(validator_payload.encode()).hexdigest(),
        "system_sha256": hashlib.sha256(_VALIDATOR_SYSTEM.encode()).hexdigest(),
        "source": "original_goal_criteria_and_spec_test_candidate",
    }
    audit(
        "loop_phase",
        {
            "phase": "spec_validator_context_budget",
            "status": "included",
            "system_chars": len(_VALIDATOR_SYSTEM),
            "user_chars": len(validator_payload),
            "actual_chars": len(_VALIDATOR_SYSTEM) + len(validator_payload),
            "required_context_complete": True,
            "test_file_count": len(normalized),
        },
        state.project_dir,
        state.project_name,
        run_id=run_id,
    )
    validation_reply = ask_llm(
        api_key, _VALIDATOR_SYSTEM, validator_payload,
        model="deepseek-chat", temperature=0.0, timeout=45,
        max_tokens=1200, state=state, aufgabe="spec-validator",
        rolle="spec-validator", heartbeat=False,
        context_manifest=validator_manifest,
    )
    validation = _json_reply(validation_reply)
    if (
        validation is None
        or validation.get("complete") is not True
        or validation.get("uncovered") != []
        or validation.get("invalid_tests") != []
    ):
        return None

    safe_run = re.sub(r"[^A-Za-z0-9_.-]", "_", run_id)[:120]
    root = Path(state.project_dir).resolve(strict=True)
    output_dir = root / ".werkstatt" / "spec-tests" / safe_run
    if output_dir.is_symlink():
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        output_dir.resolve().relative_to(root / ".werkstatt" / "spec-tests")
    except (OSError, ValueError):
        return None
    files: list[dict[str, str]] = []
    total_chars = 0
    for index, item in enumerate(normalized, 1):
        source = item["source"]
        total_chars += len(source)
        if total_chars > MAX_SPEC_TOTAL_CHARS:
            return None
        relative = Path(".werkstatt") / "spec-tests" / safe_run / f"test_spec_{index}.py"
        target = root / relative
        if target.exists() or target.is_symlink():
            return None
        target.write_text(source, encoding="utf-8", newline="\n")
        files.append({
            "path": relative.as_posix(),
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "case_id": item["id"],
            "test_name": item["test_name"],
        })
    spec_checkpoint = {
        "schema_version": 1,
        "run_id": run_id,
        "goal_sha256": hashlib.sha256(goal.encode("utf-8")).hexdigest(),
        "criteria_sha256": hashlib.sha256(
            json.dumps(criteria, ensure_ascii=False, sort_keys=True).encode(),
        ).hexdigest(),
        "spec_sha256": hashlib.sha256(
            json.dumps(normalized, ensure_ascii=False, sort_keys=True).encode(),
        ).hexdigest(),
        "files": files,
        "test_count": len(normalized),
        "status": "frozen",
    }
    if not spec_test_manifest_is_current(root, spec_checkpoint, run_id=run_id, goal=goal):
        return None
    phase_state.data["spec_test_checkpoint"] = spec_checkpoint
    phase_state.save()
    state.tests = list(state.tests or []) + [(
        f"Spec-First: {len(files)} eingefrorene Verhaltenstests; "
        f"SHA-256 {spec_checkpoint['spec_sha256']}."
    )]
    audit(
        "loop_phase",
        {
            "phase": "spec_builder",
            "status": "frozen",
            "test_count": len(files),
            "spec_sha256": spec_checkpoint["spec_sha256"],
            "file_hashes": [item["sha256"] for item in files],
            "independent_validation": True,
        },
        state.project_dir,
        state.project_name,
        run_id=run_id,
    )
    return spec_checkpoint


def spec_test_manifest_is_current(
    project_dir: str | Path,
    manifest: object,
    *,
    run_id: str | None = None,
    goal: str | None = None,
) -> bool:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return False
    if run_id is not None and manifest.get("run_id") != run_id:
        return False
    if goal is not None and manifest.get("goal_sha256") != hashlib.sha256(
        goal.encode("utf-8"),
    ).hexdigest():
        return False
    files = manifest.get("files")
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_SPEC_FILES:
        return False
    try:
        root = Path(project_dir).resolve(strict=True)
        total = 0
        seen: set[str] = set()
        case_ids: dict[str, str] = {}
        for item in files:
            if not isinstance(item, dict):
                return False
            relative_text = item.get("path")
            expected = item.get("sha256")
            if (
                not isinstance(relative_text, str)
                or relative_text in seen
                or not re.fullmatch(r"[0-9a-f]{64}", str(expected or ""))
            ):
                return False
            relative = Path(relative_text)
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or relative.parts[:2] != (".werkstatt", "spec-tests")
                or relative.suffix != ".py"
            ):
                return False
            raw_path = root / relative
            if raw_path.is_symlink():
                return False
            path = raw_path.resolve(strict=True)
            path.relative_to(root / ".werkstatt" / "spec-tests")
            if not path.is_file() or path.is_symlink():
                return False
            raw = path.read_bytes()
            if len(raw) > MAX_SPEC_FILE_CHARS or hashlib.sha256(raw).hexdigest() != expected:
                return False
            total += len(raw)
            if total > MAX_SPEC_TOTAL_CHARS:
                return False
            seen.add(relative_text)
            case_id = item.get("case_id")
            test_name = item.get("test_name")
            if (
                not isinstance(case_id, str)
                or not re.fullmatch(r"AC[1-9][0-9]*", case_id)
                or not isinstance(test_name, str)
                or not test_name.startswith("test_")
            ):
                return False
            case_ids[Path(relative_text).name] = case_id
        return (
            manifest.get("test_count") == len(files)
            and set(case_ids.values())
            == {f"AC{i + 1}" for i in range(len(files))}
        )
    except (OSError, RuntimeError, ValueError, TypeError):
        return False


def run_spec_tests(
    project_dir: str | Path,
    manifest: object,
    *,
    python_executable: str,
    run_id: str,
    goal: str,
    must_fail: bool,
) -> dict[str, Any]:
    """Run the frozen suite and expose only bounded test IDs/error classes."""
    root = Path(project_dir).resolve()
    if not spec_test_manifest_is_current(
        root, manifest, run_id=run_id, goal=goal,
    ):
        return {"ok": False, "error": "test_integrity_mismatch", "cases": []}
    files = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(files, list):
        return {"ok": False, "error": "test_manifest_invalid", "cases": []}
    paths = [str(root / item["path"]) for item in files]
    case_by_name = {
        item["test_name"]: item["case_id"]
        for item in files if isinstance(item, dict)
    }
    try:
        from werkstatt.subprocess_env import subprocess_env

        child_env = subprocess_env()
        if os.name == "nt":
            for key in ("SystemRoot", "WINDIR", "TEMP", "TMP"):
                value = os.environ.get(key)
                if value:
                    child_env[key] = value
        with tempfile.TemporaryDirectory(prefix="werkstatt-spec-") as tmp:
            report = Path(tmp) / "results.xml"
            command = [
                python_executable, "-m", "pytest", "--rootdir", str(root),
                "--tb=no", "-q", f"--junitxml={report}", *paths,
            ]
            result = subprocess.run(
                command, cwd=root, capture_output=True, text=True,
                timeout=120, check=False, env=child_env,
            )
            suite = ET.parse(report).getroot() if report.exists() else None
    except (OSError, subprocess.SubprocessError, ET.ParseError) as exc:
        return {
            "ok": False,
            "error": f"spec_test_runner_{type(exc).__name__}",
            "cases": [],
        }
    cases: list[dict[str, str]] = []
    collection_error = suite is None
    testcases = suite.findall(".//testcase") if suite is not None else []
    for testcase in testcases:
        failure = testcase.find("failure")
        error_node = testcase.find("error")
        if failure is None and error_node is None:
            continue
        failure_node: ET.Element[str]
        if failure is not None:
            failure_node = failure
        else:
            assert error_node is not None
            failure_node = error_node
        test_name = str(testcase.get("name") or "")
        error_class: str | None = failure_node.get("type")
        if not error_class and failure is not None:
            message = str(failure.get("message") or "").strip()
            if message.startswith(("assert ", "AssertionError")):
                error_class = "AssertionError"
            else:
                first = re.match(r"([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)):", message)
                error_class = first.group(1) if first else "TestFailure"
        cases.append({
            "test_id": case_by_name.get(test_name, "unknown"),
            "error_class": str(error_class or "TestError")[:80],
        })
    if suite is not None:
        collection_error = bool(
            suite.get("errors", "0") != "0"
            or suite.find(".//error") is not None
        )
    expected_ids = {
        item["case_id"] for item in files if isinstance(item, dict)
    }
    actual_ids = {item["test_id"] for item in cases}
    red = (
        bool(cases) and not collection_error
        and actual_ids == expected_ids
        and len(cases) == len(expected_ids)
        and all(item["error_class"] == "AssertionError" for item in cases)
    )
    if must_fail:
        ok = red
        result_error = "baseline_assertions_failed_as_expected" if red else (
            "baseline_suite_passed" if result.returncode == 0
            else "baseline_failure_not_behavior_assertion"
        )
    else:
        ok = result.returncode == 0
        result_error = "" if ok else "spec_acceptance_tests_failed"
    if not spec_test_manifest_is_current(
        root, manifest, run_id=run_id, goal=goal,
    ):
        return {"ok": False, "error": "test_integrity_changed_during_run", "cases": []}
    return {"ok": ok, "error": result_error, "cases": cases}
