"""Deterministic Builder dispatch for unambiguous, source-bound edits."""
from __future__ import annotations

import ast
import re
from pathlib import Path


def build_direct_edit_plan(
    task: str, target: str, project_dir,
) -> tuple[dict | None, str]:
    """Build a one-edit task only from a unique, current source replacement.

    Supported inputs are explicit literal replacements and one or more
    Python simple-name assignments to Python literals in the same file.
    Anything requiring semantic interpretation escalates to the other roles.
    """
    match = re.search(
        r"(?:ersetze|replace)\s+`([^`\r\n]{1,200})`"
        r"\s+(?:durch|with)\s+`([^`\r\n]{1,200})`",
        task,
        flags=re.IGNORECASE,
    )
    path = Path(target)
    if path.is_absolute() or ".." in path.parts or path.parts[0] == "tests":
        return None, "zieldateipfad_unsicher"
    try:
        root = Path(project_dir).resolve()
        file_path = (root / path).resolve(strict=True)
        file_path.relative_to(root)
        if not file_path.is_file():
            return None, "zieldatei_fehlt"
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, ValueError, TypeError):
        return None, "zieldatei_nicht_lesbar"

    reason = "exakte_einzeldatei_ersetzung_aktuell_belegt"
    if match is not None:
        target_binding = (
            r"(?:\bin\s+(?:der\s+Datei\s+)?|\bwithin\s+)"
            + r"\x60?" + re.escape(target) + r"\x60?(?![\w/-])"
        )
        if re.search(
            target_binding, task[match.end():], flags=re.IGNORECASE,
        ) is None:
            return None, "zieldatei_nicht_an_ersetzung_gebunden"
        old_text, new_text = match.groups()
    else:
        setting_pattern = re.compile(
            r"(?:setze|set|aendere|ändere|change)\s+"
            r"(?P<name>[A-Za-z_]\w*)\s+(?:in\s+(?:der\s+Datei\s+)?)?"
            + re.escape(target)
            + r"\s+(?:auf|to)\s+(?P<value>`[^`\r\n]{1,100}`|"
            r"'[^'\r\n]{1,100}'|\"[^\"\r\n]{1,100}\"|"
            r"[-+]?\d+(?:\.\d+)?|true|false|null|True|False|None)"
            r"(?=\s|[.,;]|$)",
            flags=re.IGNORECASE,
        )
        settings = list(setting_pattern.finditer(task))
        if len(settings) > 1:
            remainder = task
            for setting_match in reversed(settings):
                remainder = (
                    remainder[:setting_match.start()]
                    + remainder[setting_match.end():]
                )
            if re.fullmatch(
                r"[\s,;.]*(?:(?:und|and)[\s,;.]*)*",
                remainder,
                flags=re.IGNORECASE,
            ) is None:
                return None, "literal_batch_enthaelt_weitere_auftragsteile"
            if path.suffix.casefold() != ".py":
                return None, "direkte_literalzuweisung_nur_fuer_python"
            try:
                syntax = ast.parse(content)
            except SyntaxError:
                return None, "zieldatei_nicht_syntaktisch_parsebar"
            changes: list[dict] = []
            for setting_match in settings:
                name = setting_match.group("name")
                raw_value = setting_match.group("value").strip("`")
                if raw_value.casefold() == "true":
                    batch_value: object = True
                elif raw_value.casefold() == "false":
                    batch_value = False
                elif raw_value.casefold() == "null":
                    batch_value = None
                else:
                    try:
                        batch_value = ast.literal_eval(raw_value)
                    except (SyntaxError, ValueError):
                        return None, "neuer_literalwert_nicht_parsebar"
                if not isinstance(
                    batch_value, (str, int, float, bool, type(None)),
                ):
                    return None, "neuer_literalwert_ungueltig"
                assignments = [
                    node for node in ast.walk(syntax)
                    if isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == name
                ]
                if len(assignments) != 1:
                    return None, "zielvariable_nicht_eindeutig"
                assignment = assignments[0]
                if not isinstance(assignment.value, ast.Constant):
                    return None, "zielwert_ist_keine_einfache_literalzuweisung"
                line = assignment.lineno
                original_line = content.splitlines()[line - 1]
                line_match = re.fullmatch(
                    rf"(?P<prefix>\s*{re.escape(name)}\s*=\s*)"
                    r"(?P<old>[^#\r\n]+?)"
                    r"(?P<suffix>\s*(?:#.*)?)",
                    original_line,
                )
                if line_match is None:
                    return None, "zielzuweisung_nicht_einzeilig_eindeutig"
                replacement = (
                    line_match.group("prefix") + repr(batch_value)
                    + line_match.group("suffix")
                )
                if (
                    not original_line.strip()
                    or original_line == replacement
                    or content.count(original_line) != 1
                ):
                    return None, "zielzuweisung_nicht_eindeutig_oder_unveraendert"
                changes.append({
                    "datei": path.as_posix(),
                    "zeile": line,
                    "alt": original_line,
                    "neu": replacement,
                    "grund": (
                        "Explizite Nutzeranweisung; eindeutige AST-bestaetigte "
                        "Literalzuweisung im aktuellen Dateiinhalt"
                    ),
                })
            if len({item["zeile"] for item in changes}) != len(changes):
                return None, "zielzuweisung_doppelt_angefordert"
            return {
                "ziel": task,
                "auftrag_prosa": task,
                "api_auszug": {},
                "risiken": [],
                "atomarer_plan": True,
                "betroffene_stellen": changes,
            }, "eindeutige_ast_literalzuweisungen"
        setting: re.Match[str] | None = settings[0] if settings else None
        if setting is None:
            return None, "kein_expliziter_literalersetzungsausdruck"
        if path.suffix.casefold() != ".py":
            return None, "direkte_literalzuweisung_nur_fuer_python"
        name = setting.group("name")
        raw_value = setting.group("value").strip("`")
        if raw_value.casefold() == "true":
            new_value: object = True
        elif raw_value.casefold() == "false":
            new_value = False
        elif raw_value.casefold() == "null":
            new_value = None
        else:
            try:
                new_value = ast.literal_eval(raw_value)
            except (SyntaxError, ValueError):
                return None, "neuer_literalwert_nicht_parsebar"
        if not isinstance(new_value, (str, int, float, bool, type(None))):
            return None, "neuer_literalwert_ungueltig"
        try:
            syntax = ast.parse(content)
        except SyntaxError:
            return None, "zieldatei_nicht_syntaktisch_parsebar"
        assignments = [
            node for node in ast.walk(syntax)
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ]
        if len(assignments) != 1:
            return None, "zielvariable_nicht_eindeutig"
        assignment = assignments[0]
        if not isinstance(assignment.value, ast.Constant):
            return None, "zielwert_ist_keine_einfache_literalzuweisung"
        line = assignment.lineno
        original_line = content.splitlines()[line - 1]
        line_match = re.fullmatch(
            rf"(?P<prefix>\s*{re.escape(name)}\s*=\s*)"
            r"(?P<old>[^#\r\n]+?)"
            r"(?P<suffix>\s*(?:#.*)?)",
            original_line,
        )
        if line_match is None:
            return None, "zielzuweisung_nicht_einzeilig_eindeutig"
        old_text = original_line
        new_text = (
            line_match.group("prefix") + repr(new_value)
            + line_match.group("suffix")
        )
        reason = "eindeutige_ast_literalzuweisung"

    if not old_text.strip() or not new_text.strip() or old_text == new_text:
        return None, "ersetzung_leer_oder_unveraendert"
    if content.count(old_text) != 1:
        return None, "alter_text_nicht_eindeutig"
    start = content.index(old_text)
    line = content.count("\n", 0, start) + 1
    return {
        "ziel": task,
        "auftrag_prosa": task,
        "api_auszug": {},
        "risiken": [],
        "atomarer_plan": True,
        "betroffene_stellen": [{
            "datei": path.as_posix(),
            "zeile": line,
            "alt": old_text,
            "neu": new_text,
            "grund": "Explizite Nutzeranweisung; eindeutiger Treffer im aktuellen Dateiinhalt",
        }],
    }, reason
