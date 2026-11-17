"""Bounded, read-only adapter for a project's Graphify index.

Graphify is used only to suggest source paths and relationships. Werkstatt
always re-reads source files through its normal evidence path before relying
on them. Missing, malformed, or stale indexes degrade to the existing search.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

MAX_GRAPH_BYTES = 24 * 1024 * 1024
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_NODES = 150_000
MAX_LINKS = 500_000
MAX_CANDIDATES = 12
MAX_AST_SYMBOLS_PER_FILE = 5
MAX_RELATIONSHIPS_PER_FILE = 8
GRAPHIFY_REFRESH_TIMEOUT_S = 60
GRAPHIFY_QUERY_TIMEOUT_S = 20
GRAPHIFY_QUERY_BUDGET = 1200
GRAPHIFY_QUERY_MAX_CHARS = GRAPHIFY_QUERY_BUDGET * 4
_STOPWORDS = frozenset(
    {
        "aber",
        "auch",
        "auf",
        "aus",
        "bei",
        "bin",
        "bis",
        "das",
        "dem",
        "den",
        "der",
        "des",
        "die",
        "ein",
        "eine",
        "einer",
        "eines",
        "er",
        "es",
        "fuer",
        "hat",
        "ich",
        "im",
        "in",
        "ist",
        "mit",
        "nach",
        "nicht",
        "oder",
        "sind",
        "von",
        "was",
        "wie",
        "wird",
        "und",
        "zum",
        "zur",
        "the",
        "and",
        "for",
        "from",
        "how",
        "into",
        "is",
        "of",
        "that",
        "this",
        "what",
        "when",
        "where",
        "which",
        "who",
        "with",
    }
)


def _tokens(value: str) -> set[str]:
    return {
        token.casefold()
        for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]{1,}", value)
        if len(token) > 2 and token.casefold() not in _STOPWORDS
    }


def _graphify_dir(root: Path) -> Path:
    """Prefer Werkstatt's ignored local cache; read Graphify's default too."""
    private = root / ".werkstatt" / "graphify-out"
    standard = root / "graphify-out"
    output = private if private.exists() or not standard.exists() else standard
    try:
        output.resolve().relative_to(root.resolve())
    except (OSError, ValueError) as exc:
        raise ValueError("Graphify output directory escapes project") from exc
    return output


def _safe_relative(root: Path, raw: object) -> str | None:
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        return None
    normalized = raw.replace("\\", "/")
    candidate = Path(normalized)
    try:
        resolved = (
            (root / candidate).resolve()
            if not candidate.is_absolute()
            else candidate.resolve()
        )
        relative = resolved.relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return None
    if relative.startswith("../") or relative == "." or not resolved.is_file():
        return None
    return relative


@lru_cache(maxsize=8)
def _load_manifest_snapshot(
    path_text: str,
    mtime_ns: int,
    expected_size: int,
) -> dict[str, Any]:
    path = Path(path_text)
    raw_manifest = path.read_bytes()
    if len(raw_manifest) > MAX_MANIFEST_BYTES or len(raw_manifest) != expected_size:
        raise ValueError("Graphify manifest changed or exceeds size cap")
    manifest = json.loads(raw_manifest)
    if not isinstance(manifest, dict):
        raise TypeError("Graphify manifest root is not an object")
    del mtime_ns
    return manifest


def _manifest_fresh(root: Path, manifest_path: Path, rel: str) -> bool:
    try:
        stat = manifest_path.stat()
        if stat.st_size > MAX_MANIFEST_BYTES:
            return False
        manifest = _load_manifest_snapshot(
            str(manifest_path.resolve()),
            stat.st_mtime_ns,
            stat.st_size,
        )
        source = root / rel
        entry = manifest.get(rel)
        if not isinstance(entry, dict):
            # Graphify manifests from older releases used absolute paths.
            entry = manifest.get(str(source.resolve()))
        if not isinstance(entry, dict):
            return False
        expected = (
            entry.get("ast_hash") or entry.get("semantic_hash") or entry.get("hash")
        )
        if not isinstance(expected, str) or not re.fullmatch(
            r"[0-9a-fA-F]{32}", expected
        ):
            return False
        digest = hashlib.md5(usedforsecurity=False)
        with source.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest().casefold() == expected.casefold()
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
        return False


@lru_cache(maxsize=4)
def _load_graph_snapshot(
    path_text: str,
    mtime_ns: int,
    expected_size: int,
) -> tuple[dict[str, Any], str]:
    """Cache parsed Graphify snapshots across repeated Chat/role queries."""
    path = Path(path_text)
    raw_graph = path.read_bytes()
    if len(raw_graph) > MAX_GRAPH_BYTES or len(raw_graph) != expected_size:
        raise ValueError("Graphify index changed or exceeds size cap")
    graph = json.loads(raw_graph)
    if not isinstance(graph, dict):
        raise TypeError("Graphify index root is not an object")
    # mtime_ns is intentionally part of the cache key; it binds this parse to
    # the stat observed immediately before the read.
    del mtime_ns
    return graph, hashlib.sha256(raw_graph).hexdigest()


@lru_cache(maxsize=128)
def _rank_graph_paths(
    root_text: str,
    graph_path_text: str,
    mtime_ns: int,
    expected_size: int,
    query_tokens: tuple[str, ...],
) -> tuple[str, str | None, tuple[dict[str, Any], ...]]:
    """Cache bounded ranking work; file content freshness is checked later."""
    root = Path(root_text)
    graph, graph_sha256 = _load_graph_snapshot(
        graph_path_text,
        mtime_ns,
        expected_size,
    )
    nodes = graph.get("nodes")
    links = graph.get("links", graph.get("edges", []))
    if (
        not isinstance(nodes, list)
        or not isinstance(links, list)
        or len(nodes) > MAX_NODES
        or len(links) > MAX_LINKS
    ):
        raise ValueError("Graphify index schema invalid or exceeds bounds")
    node_by_id: dict[str, dict[str, Any]] = {}
    source_paths: dict[str, str] = {}
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str):
            continue
        node_by_id[node["id"]] = node
        rel = _safe_relative(root, node.get("source_file"))
        if rel:
            source_paths[node["id"]] = rel
    file_tokens: dict[str, set[str]] = {}
    for node_id, node in node_by_id.items():
        rel = source_paths.get(node_id)
        if not rel:
            continue
        searchable = " ".join(
            (rel, str(node.get("label", "")), str(node.get("name", "")))
        )
        file_tokens.setdefault(rel, set()).update(_tokens(searchable))
    document_frequency: dict[str, int] = {}
    for tokens in file_tokens.values():
        for token in tokens:
            document_frequency[token] = document_frequency.get(token, 0) + 1
    corpus_size = max(1, len(file_tokens))
    base_scores: dict[str, float] = {}
    matched_tokens: dict[str, list[str]] = {}
    token_set = set(query_tokens)
    for rel, tokens in file_tokens.items():
        matches = token_set & tokens
        if matches:
            matched_tokens[rel] = sorted(matches)
            base_scores[rel] = sum(
                math.log1p(
                    (corpus_size - document_frequency[token] + 0.5)
                    / (document_frequency[token] + 0.5)
                )
                for token in matches
            )
    scores = dict(base_scores)
    related_paths: dict[str, set[str]] = {}
    for edge in links:
        if not isinstance(edge, dict):
            continue
        left, right = edge.get("source"), edge.get("target")
        if left not in node_by_id or right not in node_by_id:
            continue
        confidence = str(edge.get("confidence", "")).upper()
        bonus = 0.25 if confidence == "EXTRACTED" else 0.05
        for endpoint, neighbor in ((left, right), (right, left)):
            rel = source_paths.get(endpoint)
            neighbor_rel = source_paths.get(neighbor)
            neighbor_score = base_scores.get(neighbor_rel or "")
            if not rel or neighbor_score is None:
                continue
            if neighbor_rel is not None:
                related_paths.setdefault(rel, set()).add(neighbor_rel)
            scores[rel] = max(scores.get(rel, 0.0), neighbor_score + bonus)
    ranked = tuple(
        {
            "file": rel,
            "score": round(score, 3),
            "matched_terms": matched_tokens.get(rel, []),
            "related_to": sorted(related_paths.get(rel, set()))[:3],
            "why": "Graphify symbol/relationship match",
        }
        for rel, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    )
    meta = graph.get("graph")
    graphify_version = meta.get("graphify_version") if isinstance(meta, dict) else None
    return graph_sha256, graphify_version, ranked


def _candidate_ast_subgraph(
    root: Path,
    manifest_path: Path,
    graph_path: Path,
    graph_mtime_ns: int,
    graph_size: int,
    candidate_path: str,
    query_tokens: tuple[str, ...],
    ignored_paths: set[str] | None = None,
) -> dict[str, Any]:
    """Return a small, source-validated AST neighborhood for one path."""
    raw_graph, _graph_sha256 = _load_graph_snapshot(
        str(graph_path.resolve()), graph_mtime_ns, graph_size,
    )
    if not isinstance(raw_graph, dict):
        return {"symbols": [], "relationships": [], "stale_relationship_count": 0}
    raw_nodes = raw_graph.get("nodes")
    raw_links = raw_graph.get("links", raw_graph.get("edges", []))
    if not isinstance(raw_nodes, list) or not isinstance(raw_links, list):
        return {"symbols": [], "relationships": [], "stale_relationship_count": 0}

    node_by_id: dict[str, dict[str, Any]] = {}
    path_by_id: dict[str, str] = {}
    symbol_scores: list[tuple[int, str, dict[str, Any]]] = []
    query = set(query_tokens)
    for node in raw_nodes[:MAX_NODES]:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str):
            continue
        node_id = node["id"]
        node_by_id[node_id] = node
        relative = _safe_relative(root, node.get("source_file"))
        if relative is None:
            continue
        path_by_id[node_id] = relative
        if relative != candidate_path:
            continue
        searchable = " ".join(str(node.get(key) or "") for key in (
            "label", "name", "norm_label", "community_name", "id",
        ))
        matches = sorted(query & _tokens(searchable))
        symbol_scores.append((len(matches), node_id, {
            "symbol": str(node.get("label") or node.get("name") or node_id)[:160],
            "origin": str(node.get("_origin") or "unknown")[:32],
            "location": str(node.get("source_location") or "")[:80],
            "community": str(node.get("community_name") or "")[:120],
            "matched_terms": matches[:8],
        }))
    symbol_scores.sort(key=lambda item: (-item[0], item[1]))
    selected_symbols = symbol_scores[:MAX_AST_SYMBOLS_PER_FILE]
    selected_ids = {node_id for _score, node_id, _record in selected_symbols}

    relationships: list[dict[str, Any]] = []
    stale_relationship_count = 0
    ignored_relationship_count = 0
    for edge in raw_links[:MAX_LINKS]:
        if not isinstance(edge, dict):
            continue
        left, right = edge.get("source"), edge.get("target")
        if not isinstance(left, str) or not isinstance(right, str):
            continue
        if left not in selected_ids and right not in selected_ids:
            continue
        left_path, right_path = path_by_id.get(left), path_by_id.get(right)
        if left_path is None or right_path is None:
            continue
        if ignored_paths and (left_path in ignored_paths or right_path in ignored_paths):
            ignored_relationship_count += 1
            continue
        other_path = right_path if left_path == candidate_path else left_path
        if not _manifest_fresh(root, manifest_path, other_path):
            stale_relationship_count += 1
            continue
        left_node, right_node = node_by_id.get(left), node_by_id.get(right)
        if left_node is None or right_node is None:
            continue
        relationships.append({
            "from": {
                "symbol": str(left_node.get("label") or left)[:120],
                "file": left_path,
                "location": str(left_node.get("source_location") or "")[:80],
            },
            "relation": str(edge.get("relation") or "related")[:48],
            "to": {
                "symbol": str(right_node.get("label") or right)[:120],
                "file": right_path,
                "location": str(right_node.get("source_location") or "")[:80],
            },
            "confidence": str(edge.get("confidence") or "unknown")[:24],
            "origin": str(edge.get("_origin") or "unknown")[:32],
        })
        if len(relationships) >= MAX_RELATIONSHIPS_PER_FILE:
            break
    return {
        "symbols": [record for _score, _node_id, record in selected_symbols],
        "relationships": relationships,
        "stale_relationship_count": stale_relationship_count,
        "ignored_relationship_count": ignored_relationship_count,
    }


def _parse_graphify_query_output(output: str, *, limit: int) -> list[dict[str, Any]]:
    """Extract Graphify's file-first scoped-subgraph results without trusting paths."""
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in output.splitlines():
        if not line.startswith("NODE ") or " [src=" not in line:
            continue
        # Graphify emits `NODE label [src=path loc=... community=...]`.
        # Split from the right so spaces in repo-relative paths are preserved.
        _label, _marker, details = line.rpartition(" [src=")
        source, separator, remainder = details.partition(" loc=")
        if not separator:
            continue
        location, separator, _community = remainder.partition(" community=")
        if not separator or not source or source in seen:
            continue
        seen.add(source)
        candidates.append({
            "file": source,
            "score": round(1.0 / (len(candidates) + 1), 3),
            "matched_terms": [],
            "related_to": [],
            "why": "Graphify native scoped-subgraph query",
            "graphify_location": location[:80],
        })
        if len(candidates) >= max(1, min(limit, MAX_CANDIDATES)):
            break
    return candidates


def _query_graphify_cli(
    root: Path, graph_path: Path, query: str, *, limit: int,
    graph_mtime_ns: int, graph_size: int, graph_sha256: str,
    seed_paths: tuple[str, ...] = (),
) -> tuple[str, list[dict[str, Any]], str]:
    """Use Graphify's own query/traversal implementation when the CLI is present."""
    executable = shutil.which("graphify")
    if not executable:
        return "cli_unavailable", [], ""
    return _query_graphify_cli_cached(
        executable, str(root), str(graph_path), graph_mtime_ns, graph_size,
        graph_sha256,
        query[:2000], max(1, min(limit, MAX_CANDIDATES)),
        seed_paths[:3],
    )


@lru_cache(maxsize=64)
def _query_graphify_cli_cached(
    executable: str,
    root_text: str,
    graph_path_text: str,
    graph_mtime_ns: int,
    graph_size: int,
    graph_sha256: str,
    query: str,
    limit: int,
    seed_paths: tuple[str, ...],
) -> tuple[str, list[dict[str, Any]], str]:
    root, graph_path = Path(root_text), Path(graph_path_text)
    del graph_mtime_ns, graph_size, graph_sha256  # These bind the cache entry to this exact graph.
    env = os.environ.copy()
    # Queries are local reads; suppress the optional Graphify query history.
    env["GRAPHIFY_QUERY_LOG_DISABLE"] = "1"
    try:
        argv = [
                executable, "query", query[:2000], "--graph", str(graph_path),
                "--budget", str(GRAPHIFY_QUERY_BUDGET),
            ]
        for seed in seed_paths:
            argv.extend(("--seed", seed))
        completed = subprocess.run(
            argv,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=GRAPHIFY_QUERY_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return "query_timeout", [], ""
    except OSError:
        return "query_spawn_error", [], ""
    if completed.returncode not in (0, 3, 4):
        return "query_failed", [], ""
    output = (completed.stdout or "")[:GRAPHIFY_QUERY_MAX_CHARS]
    candidates = _parse_graphify_query_output(output, limit=limit)
    if candidates:
        return "native_query", candidates, output
    return "native_no_match", [], output


def _git_ignored_paths(root: Path, paths: list[str]) -> set[str]:
    """Do not return ignored scratch/build files from an older graph snapshot."""
    if not paths or not (root / ".git").exists():
        return set()
    try:
        completed = subprocess.run(
            ["git", "check-ignore", "-z", "--stdin"],
            cwd=root,
            input="\0".join(paths) + "\0",
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    if completed.returncode not in (0, 1):
        return set()
    return {path for path in (completed.stdout or "").split("\0") if path}


def _native_subgraph_paths(output: str) -> list[str]:
    paths: list[str] = []
    for line in output.splitlines():
        if not line.startswith("NODE ") or " [src=" not in line:
            continue
        _label, _marker, details = line.rpartition(" [src=")
        source, separator, _remainder = details.partition(" loc=")
        if separator and source:
            paths.append(source)
    return paths


def _filter_native_subgraph(output: str, ignored_paths: set[str]) -> str:
    if not output or not ignored_paths:
        return output
    ignored_labels: set[str] = set()
    for line in output.splitlines():
        if not line.startswith("NODE ") or " [src=" not in line:
            continue
        label, _marker, details = line.rpartition(" [src=")
        source, separator, _remainder = details.partition(" loc=")
        if separator and source in ignored_paths:
            ignored_labels.add(label.removeprefix("NODE "))
    filtered: list[str] = []
    for line in output.splitlines():
        if line.startswith("NODE ") and " [src=" in line:
            _label, _marker, details = line.rpartition(" [src=")
            source, separator, _remainder = details.partition(" loc=")
            if separator and source in ignored_paths:
                continue
        elif line.startswith("EDGE "):
            left, separator, rest = line.partition(" --")
            _relation, arrow, right = rest.partition("-->")
            if separator and arrow:
                from_label = left.removeprefix("EDGE ")
                to_label = right.split(" at=", 1)[0].strip()
                at_source = (
                    right.rsplit(" at=", 1)[-1].rsplit(":", 1)[0]
                    if " at=" in right else ""
                )
                if (
                    from_label in ignored_labels
                    or to_label in ignored_labels
                    or at_source in ignored_paths
                ):
                    continue
        filtered.append(line)
    return "\n".join(filtered)[:GRAPHIFY_QUERY_MAX_CHARS]


def graphify_candidates(
    project_dir: str | Path,
    query: str,
    *,
    limit: int = 8,
    seed_paths: list[str] | tuple[str, ...] = (),
    seed_sha256: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return current Graphify-derived source candidates with provenance."""
    root = Path(project_dir).resolve()
    result: dict[str, Any] = {
        "provider": "graphify",
        "status": "unavailable",
        "candidates": [],
        "stale_source_count": 0,
        "index_sha256": None,
        "native_subgraph": "",
    }
    try:
        output = _graphify_dir(root)
    except ValueError:
        result["status"] = "invalid_index_path"
        return result
    graph_path = output / "graph.json"
    manifest_path = output / "manifest.json"
    try:
        graph_path.resolve().relative_to(root)
        manifest_path.resolve().relative_to(root)
        graph_stat = graph_path.stat()
        if graph_stat.st_size > MAX_GRAPH_BYTES:
            result["status"] = "index_too_large"
            return result
        query_tokens = tuple(sorted(_tokens(query))[:32])
        # Seeds come only from callers that already read the source. Revalidate
        # each one against the current Graphify manifest before native traversal.
        validated_seeds: list[str] = []
        for raw_seed in seed_paths:
            relative = _safe_relative(root, raw_seed)
            expected_seed_sha256 = (
                seed_sha256.get(relative)
                if relative is not None and isinstance(seed_sha256, dict)
                else None
            )
            if (
                relative is not None
                and relative not in validated_seeds
                and isinstance(expected_seed_sha256, str)
                and re.fullmatch(r"[0-9a-f]{64}", expected_seed_sha256)
                and _manifest_fresh(root, manifest_path, relative)
            ):
                try:
                    current_sha256 = hashlib.sha256(
                        (root / relative).read_bytes(),
                    ).hexdigest()
                except OSError:
                    current_sha256 = ""
                if current_sha256 == expected_seed_sha256:
                    validated_seeds.append(relative)
            if len(validated_seeds) >= 3:
                break
        graph, graph_sha256 = _load_graph_snapshot(
            str(graph_path.resolve()), graph_stat.st_mtime_ns, graph_stat.st_size,
        )
        meta = graph.get("graph")
        graphify_version = meta.get("graphify_version") if isinstance(meta, dict) else None
        query_status, native_ranked, native_subgraph = _query_graphify_cli(
            # Parse a bounded replacement pool before stale/ignored entries
            # are removed; otherwise one stale result can starve the final
            # requested candidate list even when current nodes follow it.
            root, graph_path.resolve(), query, limit=MAX_CANDIDATES,
            graph_mtime_ns=graph_stat.st_mtime_ns,
            graph_size=graph_stat.st_size,
            graph_sha256=graph_sha256,
            seed_paths=tuple(validated_seeds),
        )
        result["native_subgraph"] = native_subgraph
        retrieval_method = "graphify_cli_query"
        if native_ranked:
            ranked = tuple(native_ranked)
        else:
            # Compatibility fallback for installations where Graphify's CLI is
            # unavailable or cannot answer. This is Werkstatt ranking, not native
            # Graphify retrieval, and is labeled as such in the evidence.
            _fallback_sha, _fallback_version, ranked = _rank_graph_paths(
                str(root), str(graph_path.resolve()), graph_stat.st_mtime_ns,
                graph_stat.st_size, query_tokens,
            )
            retrieval_method = "werkstatt_fallback"
        candidate_pool = list(ranked[: MAX_CANDIDATES * 4])
        ignored_paths = _git_ignored_paths(
            root,
            [str(item["file"]) for item in candidate_pool]
            + _native_subgraph_paths(native_subgraph),
        )
        # The fallback index can contain many paths; retain only the inspected
        # bounded prefix so ignored entries beyond this batch cannot leak through.
        ranked = tuple(candidate_pool)
        native_subgraph = _filter_native_subgraph(native_subgraph, ignored_paths)
        result["native_subgraph"] = native_subgraph
        native_lines = native_subgraph.splitlines()
        native_node_count = sum(line.startswith("NODE ") for line in native_lines)
        native_relationship_count = sum(
            line.startswith("EDGE ") for line in native_lines
        )
        ranked = tuple(
            item for item in ranked if str(item["file"]) not in ignored_paths
        )
        result["index_sha256"] = graph_sha256
        selected: list[dict[str, Any]] = []
        stale = 0
        for candidate in ranked:
            rel = str(candidate["file"])
            if not _manifest_fresh(root, manifest_path, rel):
                stale += 1
                continue
            try:
                source_path = (root / rel).resolve(strict=True)
                source_path.relative_to(root)
                source_digest = hashlib.sha256()
                source_bytes = 0
                with source_path.open("rb") as source_handle:
                    for chunk in iter(
                        lambda: source_handle.read(65536), b"",
                    ):
                        source_digest.update(chunk)
                        source_bytes += len(chunk)
            except (OSError, RuntimeError, ValueError):
                stale += 1
                continue
            current_candidate = dict(candidate)
            current_candidate["source_sha256"] = source_digest.hexdigest()
            current_candidate["source_bytes"] = source_bytes
            selected.append(current_candidate)
            if len(selected) >= max(1, min(limit, MAX_CANDIDATES)):
                break
        query_tokens = tuple(sorted(_tokens(query))[:32])
        graph, _graph_sha256 = _load_graph_snapshot(
            str(graph_path.resolve()), graph_stat.st_mtime_ns,
            graph_stat.st_size,
        )
        stale_relationship_count = 0
        ignored_relationship_count = 0
        for candidate in selected:
            details = _candidate_ast_subgraph(
                root,
                manifest_path,
                graph_path,
                graph_stat.st_mtime_ns,
                graph_stat.st_size,
                str(candidate["file"]),
                query_tokens,
                ignored_paths,
            )
            candidate.update(details)
            stale_relationship_count += int(
                details.get("stale_relationship_count", 0),
            )
            ignored_relationship_count += int(
                details.get("ignored_relationship_count", 0),
            )
        result.update(
            {
                "status": (
                    "partial_stale"
                    if selected and (stale or stale_relationship_count)
                    else "ok" if selected
                    else "stale" if stale
                    else "no_match"
                ),
                "candidates": selected,
                "stale_source_count": stale,
                "stale_relationship_count": stale_relationship_count,
                "graphify_version": graphify_version,
                "built_at_commit": graph.get("built_at_commit"),
                "candidate_limit": max(1, min(limit, MAX_CANDIDATES)),
                "retrieval_method": retrieval_method,
                "native_query_status": query_status,
                "native_node_count": native_node_count,
                "native_relationship_count": native_relationship_count,
                "seed_paths": validated_seeds,
                "ignored_source_count": len(ignored_paths),
                "ignored_relationship_count": ignored_relationship_count,
            }
        )
        return result
    except (OSError, ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        return result


def refresh_graphify_index(project_dir: str | Path) -> dict[str, Any]:
    """Build or incrementally refresh the local code graph without an LLM call."""
    root = Path(project_dir).resolve()
    executable = shutil.which("graphify")
    if not executable:
        return {"status": "cli_unavailable"}
    try:
        output = _graphify_dir(root)
    except ValueError:
        return {"status": "invalid_index_path"}
    graph_path = output / "graph.json"
    command = (
        [executable, "update", "."]
        if graph_path.is_file()
        else [executable, "extract", ".", "--code-only"]
    )
    env = os.environ.copy()
    env["GRAPHIFY_QUERY_LOG_DISABLE"] = "1"
    env["GRAPHIFY_OUT"] = output.relative_to(root).as_posix()
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=GRAPHIFY_REFRESH_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "timeout_s": GRAPHIFY_REFRESH_TIMEOUT_S}
    except OSError as exc:
        return {"status": "spawn_error", "error_type": type(exc).__name__}
    return {
        "status": "refreshed" if completed.returncode == 0 else "refresh_failed",
        "returncode": completed.returncode,
        "stdout_chars": len(completed.stdout or ""),
        "stderr_chars": len(completed.stderr or ""),
    }
