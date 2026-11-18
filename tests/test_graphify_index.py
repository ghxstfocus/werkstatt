from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from werkstatt import graphify_index
from werkstatt.graphify_index import graphify_candidates


def _write_index(
    root: Path, source: Path, *, rel: str = "werkstatt/phase_state.py"
) -> None:
    output = root / "graphify-out"
    output.mkdir(exist_ok=True)
    digest = hashlib.md5(usedforsecurity=False)
    digest.update(source.read_bytes())
    (output / "manifest.json").write_text(
        json.dumps(
            {
                rel: {"ast_hash": digest.hexdigest(), "mtime": source.stat().st_mtime},
            }
        ),
        encoding="utf-8",
    )
    nodes = [{
        "id": "n1",
        "label": "phase state checkpoint",
        "source_file": rel,
        "file_type": "code",
    }]
    links = []
    related = root / "tests/test_checkpoint_decision.py"
    if related.is_file():
        nodes.append({
            "id": "n2",
            "label": "checkpoint decision",
            "source_file": "tests/test_checkpoint_decision.py",
            "file_type": "code",
        })
        links.append({
            "source": "n1",
            "target": "n2",
            "relation": "calls",
            "confidence": "EXTRACTED",
        })
    (output / "graph.json").write_text(
        json.dumps({
            "graph": {"schema_version": "1", "graphify_version": "test"},
            "nodes": nodes,
            "links": links,
        }),
        encoding="utf-8",
    )


def test_graphify_candidates_use_current_manifest_hash_and_relationship(tmp_path: Path):
    source = tmp_path / "werkstatt" / "phase_state.py"
    source.parent.mkdir()
    source.write_text("def checkpoint_state(): pass\n", encoding="utf-8")
    related = tmp_path / "tests" / "test_checkpoint_decision.py"
    related.parent.mkdir()
    related.write_text("def test_checkpoint_decision(): pass\n", encoding="utf-8")
    _write_index(tmp_path, source)
    # The related file must also be stamped because Graphify candidates are
    # individually checked against the source manifest.
    manifest_path = tmp_path / "graphify-out" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    md5 = hashlib.md5(usedforsecurity=False)
    md5.update(related.read_bytes())
    manifest["tests/test_checkpoint_decision.py"] = {"ast_hash": md5.hexdigest()}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = graphify_candidates(
        tmp_path,
        "checkpoint decision",
        limit=4,
        seed_paths=["werkstatt/phase_state.py", "../outside.py"],
        seed_sha256={
            "werkstatt/phase_state.py": hashlib.sha256(
                source.read_bytes(),
            ).hexdigest(),
        },
    )

    assert result["status"] == "ok"
    assert result["index_sha256"]
    assert [item["file"] for item in result["candidates"]][:2] == [
        "werkstatt/phase_state.py",
        "tests/test_checkpoint_decision.py",
    ]
    by_path = {item["file"]: item for item in result["candidates"]}
    phase_state_candidate = by_path["werkstatt/phase_state.py"]
    assert phase_state_candidate["source_sha256"] == hashlib.sha256(
        source.read_bytes(),
    ).hexdigest()
    assert phase_state_candidate["symbols"][0]["symbol"] == (
        "phase state checkpoint"
    )
    assert phase_state_candidate["relationships"][0]["relation"] == "calls"
    assert phase_state_candidate["relationships"][0]["to"]["file"] == (
        "tests/test_checkpoint_decision.py"
    )


def test_graphify_fallback_prioritizes_hash_validated_explorer_seed(
    tmp_path: Path, monkeypatch,
):
    source = tmp_path / "werkstatt" / "phase_state.py"
    source.parent.mkdir()
    source.write_text("def target_checkpoint(): return True\n", encoding="utf-8")
    _write_index(tmp_path, source)
    monkeypatch.setattr(graphify_index.shutil, "which", lambda _name: None)

    result = graphify_candidates(
        tmp_path,
        "unrelated query vocabulary",
        limit=3,
        seed_paths=["werkstatt/phase_state.py"],
        seed_sha256={
            "werkstatt/phase_state.py": hashlib.sha256(
                source.read_bytes(),
            ).hexdigest(),
        },
    )

    assert result["retrieval_method"] == "werkstatt_fallback_seeded"
    assert result["seed_paths"] == ["werkstatt/phase_state.py"]
    assert result["candidates"][0]["file"] == "werkstatt/phase_state.py"
    assert result["candidates"][0]["source_sha256"] == hashlib.sha256(
        source.read_bytes(),
    ).hexdigest()
    assert "Explorer source seed" in result["candidates"][0]["why"]


def test_graphify_fallback_keeps_current_source_seed_when_manifest_is_stale(
    tmp_path: Path, monkeypatch,
):
    source = tmp_path / "werkstatt" / "phase_state.py"
    source.parent.mkdir()
    source.write_text("def target_checkpoint(): return True\n", encoding="utf-8")
    _write_index(tmp_path, source)
    manifest_path = tmp_path / "graphify-out" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["werkstatt/phase_state.py"]["ast_hash"] = "0" * 32
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(graphify_index.shutil, "which", lambda _name: None)

    current_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    result = graphify_candidates(
        tmp_path,
        "unrelated query vocabulary",
        limit=3,
        seed_paths=["werkstatt/phase_state.py"],
        seed_sha256={"werkstatt/phase_state.py": current_sha256},
    )

    candidate = result["candidates"][0]
    assert result["status"] == "partial_stale"
    assert result["graph_stale_seed_count"] == 1
    assert candidate["file"] == "werkstatt/phase_state.py"
    assert candidate["source_sha256"] == current_sha256
    assert candidate["source_provenance"] == (
        "explorer_source_seed_graphify_unindexed_or_stale"
    )
    assert candidate["relationships"] == []
    assert candidate["symbols"] == []
    assert result["seed_paths"] == []
    assert result["source_seed_paths"] == ["werkstatt/phase_state.py"]


def test_graphify_index_uses_generic_project_relative_source_paths(
    tmp_path: Path,
):
    project = tmp_path / "sample_app"
    source = project / "src" / "api.py"
    source.parent.mkdir(parents=True)
    source.write_text("def checkpoint_state(): return True\n", encoding="utf-8")
    _write_index(project, source, rel="src/api.py")

    result = graphify_candidates(project, "checkpoint state", limit=3)

    assert result["status"] == "ok"
    assert result["candidates"]
    assert result["candidates"][0]["file"] == "src/api.py"
    assert result["candidates"][0]["source_sha256"] == hashlib.sha256(
        source.read_bytes(),
    ).hexdigest()


def test_graphify_candidates_never_return_its_own_cache_files(
    tmp_path: Path, monkeypatch,
):
    source = tmp_path / "src" / "api.py"
    source.parent.mkdir()
    source.write_text("def checkpoint_state(): return True\n", encoding="utf-8")
    _write_index(tmp_path, source, rel="src/api.py")
    graph_path = tmp_path / "graphify-out" / "graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["nodes"].append({
        "id": "cache",
        "label": "checkpoint state graph index",
        "source_file": "graphify-out/graph.json",
        "file_type": "code",
    })
    graph["links"].append({
        "source": "n1", "target": "cache", "relation": "indexes",
        "confidence": "EXTRACTED",
    })
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    monkeypatch.setattr(graphify_index, "_graphify_executable", lambda: None)

    result = graphify_candidates(tmp_path, "checkpoint state", limit=5)

    assert result["candidates"]
    assert all("graphify-out" not in item["file"] for item in result["candidates"])


def test_graphify_indexes_and_hashes_are_isolated_between_projects(
    tmp_path: Path, monkeypatch,
):
    monkeypatch.setattr(graphify_index.shutil, "which", lambda _name: None)
    projects = {
        "alpha": "def alpha_checkpoint(): return 'alpha'\n",
        "beta": "def beta_checkpoint(): return 'beta'\n",
    }
    results = {}
    for name, content in projects.items():
        project = tmp_path / name
        source = project / "src" / "api.ts"
        source.parent.mkdir(parents=True)
        source.write_text(content, encoding="utf-8")
        _write_index(project, source, rel="src/api.ts")
        graph_path = project / "graphify-out" / "graph.json"
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        graph["nodes"][0]["label"] = f"{name} checkpoint api"
        graph_path.write_text(json.dumps(graph), encoding="utf-8")
        results[name] = graphify_candidates(
            project, f"{name} checkpoint api", limit=2,
        )

    for name, content in projects.items():
        result = results[name]
        assert result["status"] == "ok"
        assert result["candidates"][0]["file"] == "src/api.ts"
        assert result["candidates"][0]["symbols"][0]["symbol"] == (
            f"{name} checkpoint api"
        )
        source = tmp_path / name / "src" / "api.ts"
        assert result["candidates"][0]["source_sha256"] == hashlib.sha256(
            source.read_bytes(),
        ).hexdigest()

    changed = tmp_path / "alpha" / "src" / "api.ts"
    changed.write_text("def changed_checkpoint(): return 'changed'\n", encoding="utf-8")
    alpha = graphify_candidates(tmp_path / "alpha", "alpha checkpoint api")
    beta = graphify_candidates(tmp_path / "beta", "beta checkpoint api")
    assert alpha["status"] == "stale"
    assert alpha["candidates"] == []
    assert beta["status"] == "ok"
    beta_source = tmp_path / "beta" / "src" / "api.ts"
    assert beta["candidates"][0]["source_sha256"] == hashlib.sha256(
        beta_source.read_bytes(),
    ).hexdigest()


def test_graphify_candidates_use_native_query_order_when_cli_is_available(
    tmp_path: Path, monkeypatch,
):
    source = tmp_path / "werkstatt" / "phase_state.py"
    source.parent.mkdir()
    source.write_text("def checkpoint_state(): pass\n", encoding="utf-8")
    related = tmp_path / "tests" / "test_checkpoint_decision.py"
    related.parent.mkdir()
    related.write_text("def test_checkpoint_decision(): pass\n", encoding="utf-8")
    _write_index(tmp_path, source)
    manifest_path = tmp_path / "graphify-out" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    related_md5 = hashlib.md5(usedforsecurity=False)
    related_md5.update(related.read_bytes())
    manifest["tests/test_checkpoint_decision.py"] = {
        "ast_hash": related_md5.hexdigest(),
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    observed: dict[str, object] = {}
    monkeypatch.setattr(graphify_index.shutil, "which", lambda _name: "graphify")

    def fake_run(argv, **kwargs):
        observed["argv"] = argv
        observed["env"] = kwargs["env"]
        return subprocess.CompletedProcess(
            argv,
            0,
            "Graph: graphify-out/graph.json (2 nodes)\n"
            "NODE checkpoint decision [src=tests/test_checkpoint_decision.py "
            "loc=L1 community=tests]\n"
            "NODE phase state [src=werkstatt/phase_state.py "
            "loc=L1 community=runtime]\n",
            "",
        )

    monkeypatch.setattr(graphify_index.subprocess, "run", fake_run)
    result = graphify_candidates(
        tmp_path,
        "checkpoint decision",
        limit=4,
        seed_paths=["werkstatt/phase_state.py", "../outside.py"],
        seed_sha256={
            "werkstatt/phase_state.py": hashlib.sha256(
                source.read_bytes(),
            ).hexdigest(),
        },
    )

    assert result["retrieval_method"] == "graphify_cli_query"
    assert result["native_query_status"] == "native_query"
    assert "NODE checkpoint decision" in result["native_subgraph"]
    assert result["native_node_count"] == 2
    assert [item["file"] for item in result["candidates"]] == [
        "tests/test_checkpoint_decision.py",
        "werkstatt/phase_state.py",
    ]
    assert observed["argv"][1:3] == ["query", "checkpoint decision"]
    assert "--graph" in observed["argv"]
    assert "--budget" in observed["argv"]
    assert "--depth" not in observed["argv"]
    assert observed["argv"][observed["argv"].index("--seed") + 1] == (
        "werkstatt/phase_state.py"
    )
    assert "../outside.py" not in observed["argv"]
    assert result["seed_paths"] == ["werkstatt/phase_state.py"]
    assert observed["env"]["GRAPHIFY_QUERY_LOG_DISABLE"] == "1"


def test_graphify_rejects_seed_when_explorer_source_hash_changed(
    tmp_path: Path, monkeypatch,
):
    source = tmp_path / "werkstatt" / "phase_state.py"
    source.parent.mkdir()
    source.write_text("def checkpoint_state(): pass\n", encoding="utf-8")
    _write_index(tmp_path, source)
    observed: dict[str, object] = {}
    monkeypatch.setattr(graphify_index.shutil, "which", lambda _name: "graphify")

    def fake_run(argv, **kwargs):
        observed["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(graphify_index.subprocess, "run", fake_run)
    result = graphify_candidates(
        tmp_path,
        "checkpoint decision",
        seed_paths=["werkstatt/phase_state.py"],
        seed_sha256={"werkstatt/phase_state.py": "0" * 64},
    )

    assert "--seed" not in observed["argv"]
    assert result["seed_paths"] == []


def test_native_query_replaces_stale_early_nodes_from_bounded_candidate_pool(
    tmp_path: Path, monkeypatch,
):
    first = tmp_path / "src" / "first.py"
    second = tmp_path / "src" / "second.py"
    first.parent.mkdir()
    first.write_text("def first(): return 1\n", encoding="utf-8")
    second.write_text("def second(): return 2\n", encoding="utf-8")
    _write_index(tmp_path, first, rel="src/first.py")
    manifest_path = tmp_path / "graphify-out" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    second_md5 = hashlib.md5(usedforsecurity=False)
    second_md5.update(second.read_bytes())
    manifest["src/second.py"] = {"ast_hash": second_md5.hexdigest()}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(graphify_index.shutil, "which", lambda _name: "graphify")

    def fake_run(argv, **kwargs):
        output = (
            "NODE stale one [src=gone/one.py loc=L1 community=old]\n"
            "NODE stale two [src=gone/two.py loc=L1 community=old]\n"
            "NODE first [src=src/first.py loc=L1 community=src]\n"
            "NODE second [src=src/second.py loc=L1 community=src]"
        )
        return subprocess.CompletedProcess(argv, 0, output, "")

    monkeypatch.setattr(graphify_index.subprocess, "run", fake_run)
    result = graphify_candidates(tmp_path, "source dependency", limit=2)

    assert [item["file"] for item in result["candidates"]] == [
        "src/first.py", "src/second.py",
    ]
    assert result["stale_source_count"] == 2


def test_graphify_query_parser_keeps_paths_with_spaces_and_bounds_results():
    parsed = graphify_index._parse_graphify_query_output(
        "NODE x [src=src/my module.py loc=L10 community=core]\n"
        "NODE duplicate [src=src/my module.py loc=L20 community=core]\n"
        "NODE y [src=src/other.py loc=L4 community=core]\n",
        limit=1,
    )

    assert [item["file"] for item in parsed] == ["src/my module.py"]
    assert parsed[0]["graphify_location"] == "L10"


def test_native_subgraph_filter_removes_ignored_nodes_and_edges():
    output = (
        "Graph: graph.json (3 nodes)\n"
        "NODE current [src=src/current.py loc=L1 community=core]\n"
        "NODE scratch [src=work/scratch.py loc=L1 community=tmp]\n"
        "NODE target [src=src/target.py loc=L2 community=core]\n"
        "EDGE current --calls [EXTRACTED]--> scratch at=src/current.py:L2\n"
        "EDGE current --calls [EXTRACTED]--> target at=src/current.py:L3\n"
        "EDGE scratch --imports [EXTRACTED]--> target at=work/scratch.py:L1\n"
    )

    filtered = graphify_index._filter_native_subgraph(
        output, {"work/scratch.py"},
    )

    assert "work/scratch.py" not in filtered
    assert "NODE current" in filtered
    assert "NODE target" in filtered
    assert "EDGE current --calls [EXTRACTED]--> target" in filtered
    assert "EDGE current --calls [EXTRACTED]--> scratch" not in filtered


def test_graphify_ignores_git_ignored_stale_snapshot_paths(
    tmp_path: Path, monkeypatch,
):
    (tmp_path / ".git").mkdir()
    observed: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        observed["argv"] = argv
        observed["input"] = kwargs["input"]
        return subprocess.CompletedProcess(argv, 0, "work/scratch.py\0", "")

    monkeypatch.setattr(graphify_index.subprocess, "run", fake_run)

    ignored = graphify_index._git_ignored_paths(
        tmp_path, ["src/current.py", "work/scratch.py"],
    )

    assert ignored == {"work/scratch.py"}
    assert observed["argv"] == ["git", "check-ignore", "-z", "--stdin"]
    assert observed["input"] == "src/current.py\0work/scratch.py\0"


def test_graphify_native_query_cache_is_bound_to_graph_hash(
    tmp_path: Path, monkeypatch,
):
    graphify_index._query_graphify_cli_cached.cache_clear()
    calls = 0
    monkeypatch.setattr(graphify_index.shutil, "which", lambda _name: "graphify")

    def fake_run(argv, **kwargs):
        nonlocal calls
        calls += 1
        output = "NODE target [src=target.py loc=L1 community=core]\n"
        return subprocess.CompletedProcess(argv, 0, output, "")

    monkeypatch.setattr(graphify_index.subprocess, "run", fake_run)
    args = {
        "limit": 4, "graph_mtime_ns": 1, "graph_size": 22,
        "graph_sha256": "a" * 64,
    }
    first = graphify_index._query_graphify_cli(
        tmp_path, tmp_path / "graph.json", "target", **args,
    )
    second = graphify_index._query_graphify_cli(
        tmp_path, tmp_path / "graph.json", "target", **args,
    )
    changed = graphify_index._query_graphify_cli(
        tmp_path, tmp_path / "graph.json", "target",
        **{**args, "graph_sha256": "b" * 64},
    )

    assert calls == 2
    assert first == second == changed


def test_graphify_rejects_stale_files_and_out_of_project_paths(tmp_path: Path):
    source = tmp_path / "module.py"
    source.write_text("def checkpoint_state(): pass\n", encoding="utf-8")
    output = tmp_path / "graphify-out"
    output.mkdir()
    (output / "manifest.json").write_text("{}", encoding="utf-8")
    (output / "graph.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "stale",
                        "label": "checkpoint state",
                        "source_file": "module.py",
                    },
                    {
                        "id": "outside",
                        "label": "checkpoint state",
                        "source_file": "../outside.py",
                    },
                ],
                "links": [],
            }
        ),
        encoding="utf-8",
    )

    result = graphify_candidates(tmp_path, "checkpoint state")

    assert result["status"] == "stale"
    assert result["candidates"] == []
    assert result["stale_source_count"] == 1


def test_graphify_missing_index_returns_explicit_fallback(tmp_path: Path):
    result = graphify_candidates(tmp_path, "anything")
    assert result["status"] == "unavailable"
    assert result["candidates"] == []


def test_graphify_rejects_manifest_hash_mismatch(tmp_path: Path):
    source = tmp_path / "module.py"
    source.write_text("def old_checkpoint(): pass\n", encoding="utf-8")
    _write_index(tmp_path, source, rel="module.py")
    source.write_text("def changed_checkpoint(): pass\n", encoding="utf-8")

    result = graphify_candidates(tmp_path, "checkpoint")

    assert result["status"] == "stale"
    assert result["candidates"] == []
    assert result["stale_source_count"] == 1


def test_graphify_marks_partial_staleness_even_with_current_candidates(
    tmp_path: Path,
) -> None:
    current = tmp_path / "current.py"
    stale = tmp_path / "stale.py"
    current.write_text("def checkpoint_current(): pass\n", encoding="utf-8")
    stale.write_text("def checkpoint_old(): pass\n", encoding="utf-8")
    output = tmp_path / "graphify-out"
    output.mkdir()
    current_md5 = hashlib.md5(usedforsecurity=False)
    current_md5.update(current.read_bytes())
    (output / "manifest.json").write_text(
        json.dumps({
            "current.py": {"ast_hash": current_md5.hexdigest()},
            "stale.py": {"ast_hash": "0" * 32},
        }),
        encoding="utf-8",
    )
    (output / "graph.json").write_text(
        json.dumps({
            "nodes": [
                {"id": "current", "label": "checkpoint current",
                 "source_file": "current.py"},
                {"id": "stale", "label": "checkpoint old",
                 "source_file": "stale.py"},
            ],
            "links": [],
        }),
        encoding="utf-8",
    )

    result = graphify_candidates(tmp_path, "checkpoint", limit=2)

    assert result["status"] == "partial_stale"
    assert result["stale_source_count"] == 1
    assert [item["file"] for item in result["candidates"]] == ["current.py"]


def test_graphify_accepts_document_semantic_manifest_hash(tmp_path: Path):
    source = tmp_path / "docs" / "architecture.md"
    source.parent.mkdir()
    source.write_text("# Checkpoint architecture\n", encoding="utf-8")
    _write_index(tmp_path, source, rel="docs/architecture.md")
    manifest_path = tmp_path / "graphify-out" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["docs/architecture.md"]["semantic_hash"] = manifest[
        "docs/architecture.md"
    ].pop("ast_hash")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = graphify_candidates(tmp_path, "checkpoint architecture")

    assert result["status"] == "ok"
    assert result["candidates"][0]["file"] == "docs/architecture.md"


def test_graphify_refresh_uses_private_cache_and_code_only(
    tmp_path: Path,
    monkeypatch,
):
    observed: dict[str, object] = {}
    monkeypatch.setattr(graphify_index.shutil, "which", lambda _name: "graphify")

    def fake_run(argv, *, cwd, env, capture_output, text, check, timeout):
        observed.update(
            {
                "argv": argv,
                "cwd": cwd,
                "env": env,
                "timeout": timeout,
            }
        )
        return subprocess.CompletedProcess(argv, 0, "updated", "")

    monkeypatch.setattr(graphify_index.subprocess, "run", fake_run)
    result = graphify_index.refresh_graphify_index(tmp_path)

    assert result["status"] == "refreshed"
    assert observed["argv"] == ["graphify", "extract", ".", "--code-only"]
    assert observed["env"]["GRAPHIFY_OUT"] == ".werkstatt/graphify-out"
    assert observed["env"]["GRAPHIFY_QUERY_LOG_DISABLE"] == "1"
    assert observed["timeout"] == 60


def test_graphify_refresh_uses_update_when_index_exists(
    tmp_path: Path,
    monkeypatch,
):
    graph_path = tmp_path / "graphify-out" / "graph.json"
    graph_path.parent.mkdir()
    graph_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(graphify_index.shutil, "which", lambda _name: "graphify")
    observed: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        observed["argv"] = argv
        observed["env"] = kwargs["env"]
        return subprocess.CompletedProcess(argv, 0, "updated", "")

    monkeypatch.setattr(graphify_index.subprocess, "run", fake_run)

    result = graphify_index.refresh_graphify_index(tmp_path)

    assert result["status"] == "refreshed"
    assert observed["argv"] == ["graphify", "update", "."]
    assert observed["env"]["GRAPHIFY_OUT"] == "graphify-out"


def test_graphify_refresh_finds_cli_beside_venv_python_when_path_is_missing(
    tmp_path: Path, monkeypatch,
):
    scripts = tmp_path / "venv" / (
        "Scripts" if graphify_index.os.name == "nt" else "bin"
    )
    scripts.mkdir(parents=True)
    python = scripts / (
        "python.exe" if graphify_index.os.name == "nt" else "python"
    )
    python.write_text("", encoding="utf-8")
    executable = scripts / (
        "graphify.exe" if graphify_index.os.name == "nt" else "graphify"
    )
    executable.write_text("", encoding="utf-8")
    monkeypatch.setattr(graphify_index.shutil, "which", lambda _name: None)
    monkeypatch.setattr(graphify_index.sys, "executable", str(python))
    observed: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        observed["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, "updated", "")

    monkeypatch.setattr(graphify_index.subprocess, "run", fake_run)
    result = graphify_index.refresh_graphify_index(tmp_path)

    assert result["status"] == "refreshed"
    assert observed["argv"][0] == str(executable)


def test_graphify_parsed_index_is_cached_and_invalidated_on_change(tmp_path: Path):
    graphify_index._load_graph_snapshot.cache_clear()
    graphify_index._rank_graph_paths.cache_clear()
    output = tmp_path / "graphify-out"
    output.mkdir()
    graph_path = output / "graph.json"
    graph_path.write_text(json.dumps({"nodes": [], "links": []}), encoding="utf-8")

    first = graphify_candidates(tmp_path, "checkpoint")
    second = graphify_candidates(tmp_path, "checkpoint")
    assert first["index_sha256"] == second["index_sha256"]
    assert graphify_index._rank_graph_paths.cache_info().hits == 1

    graph_path.write_text(
        json.dumps({"nodes": [], "links": [], "changed": True}), encoding="utf-8"
    )
    changed = graphify_candidates(tmp_path, "checkpoint")
    assert changed["index_sha256"] != first["index_sha256"]
