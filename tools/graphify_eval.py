"""Compare Graphify navigation with the existing repository retrieval baseline."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from werkstatt.explorer import _rank_source_files  # noqa: E402
from werkstatt.graphify_index import graphify_candidates  # noqa: E402


def _rank_metrics(
    paths: list[str], relevant: set[str], *, k: int,
) -> dict[str, float]:
    selected = paths[:max(1, k)]
    hits = [path for path in selected if path in relevant]
    first_rank = next(
        (rank for rank, path in enumerate(selected, 1) if path in relevant),
        None,
    )
    return {
        "precision_at_k": len(hits) / max(1, k),
        "recall_at_k": len(hits) / len(relevant) if relevant else 1.0,
        "mrr": 1 / first_rank if first_rank else 0.0,
    }


def evaluate(
    project_dir: Path,
    dataset_path: Path,
    *,
    limit: int = 5,
) -> dict[str, Any]:
    """Measure Graphify and Explorer on the same curated query/gold sets."""
    cases: list[dict[str, Any]] = []
    with dataset_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            query = row.get("query", "")
            relevant = set(filter(
                None, row.get("expected_relevant_files", "").split(";"),
            ))
            if not query.strip() or not relevant:
                raise ValueError("Retrieval-Eval enthaelt eine leere Query/Goldmenge")

            graph = graphify_candidates(project_dir, query, limit=limit)
            graph_candidates = graph.get("candidates", [])
            graph_paths = [
                str(item["file"])
                for item in graph_candidates
                if isinstance(item, dict) and isinstance(item.get("file"), str)
            ]
            baseline, baseline_manifest = _rank_source_files(
                project_dir, query, limit=limit,
            )
            baseline_paths = [
                str(item["file"])
                for item in baseline
                if isinstance(item, dict) and isinstance(item.get("file"), str)
            ]
            seed_source_hashes: dict[str, str] = {}
            for relative in baseline_paths[:3]:
                try:
                    source = (project_dir / relative).resolve(strict=True)
                    source.relative_to(project_dir.resolve(strict=True))
                    seed_source_hashes[relative] = hashlib.sha256(
                        source.read_bytes(),
                    ).hexdigest()
                except (OSError, RuntimeError, ValueError):
                    continue
            seeded_graph = graphify_candidates(
                project_dir,
                query,
                limit=limit,
                seed_paths=baseline_paths[:3],
                seed_sha256=seed_source_hashes,
            )
            seeded_paths = [
                str(item["file"])
                for item in seeded_graph.get("candidates", [])
                if isinstance(item, dict) and isinstance(item.get("file"), str)
            ]
            seeded_source_hashes = {
                str(item["file"]): item.get("source_sha256")
                for item in seeded_graph.get("candidates", [])
                if isinstance(item, dict) and isinstance(item.get("file"), str)
            }
            current_source_hashes: dict[str, str | None] = {}
            for relative in graph_paths:
                try:
                    source = (project_dir / relative).resolve(strict=True)
                    source.relative_to(project_dir.resolve(strict=True))
                    current_source_hashes[relative] = hashlib.sha256(
                        source.read_bytes(),
                    ).hexdigest()
                except (OSError, RuntimeError, ValueError):
                    current_source_hashes[relative] = None
            cases.append({
                "query": query,
                "expected_relevant_files": sorted(relevant),
                "graphify": {
                "status": graph.get("status"),
                    "retrieval_method": graph.get("retrieval_method"),
                    "native_query_status": graph.get("native_query_status"),
                    "native_node_count": graph.get("native_node_count", 0),
                    "native_relationship_count": graph.get(
                        "native_relationship_count", 0,
                    ),
                    "ignored_source_count": graph.get("ignored_source_count", 0),
                    "index_sha256": graph.get("index_sha256"),
                    "graphify_version": graph.get("graphify_version"),
                    "stale_source_count": graph.get("stale_source_count"),
                    "selected": graph_paths,
                    "candidate_evidence": [
                        {
                            "file": item.get("file"),
                            "score": item.get("score"),
                            "matched_terms": item.get("matched_terms", []),
                            "related_to": item.get("related_to", []),
                        }
                        for item in graph_candidates
                        if isinstance(item, dict)
                    ],
                    "source_sha256": current_source_hashes,
                    "metrics": _rank_metrics(graph_paths, relevant, k=limit),
                },
                "graphify_seeded": {
                    "retrieval_method": seeded_graph.get("retrieval_method"),
                    "native_query_status": seeded_graph.get("native_query_status"),
                    "seed_paths": seeded_graph.get("seed_paths", []),
                    "selected": seeded_paths,
                    "source_sha256": seeded_source_hashes,
                    "metrics": _rank_metrics(seeded_paths, relevant, k=limit),
                },
                "explorer": {
                    "index_scan_succeeded": baseline_manifest.get(
                        "index_scan_succeeded",
                    ),
                    "selected": baseline_paths,
                    "metrics": _rank_metrics(baseline_paths, relevant, k=limit),
                },
            })

    if not cases:
        raise ValueError("Retrieval-Eval enthaelt keine Faelle")
    metric_names = ("precision_at_k", "recall_at_k", "mrr")
    means: dict[str, dict[str, float]] = {}
    for retriever in ("graphify", "graphify_seeded", "explorer"):
        means[retriever] = {
            metric: round(sum(
                float(case[retriever]["metrics"][metric]) for case in cases
            ) / len(cases), 4)
            for metric in metric_names
        }
    return {
        "dataset": str(dataset_path),
        "project": str(project_dir),
        "candidate_limit": max(1, min(limit, 12)),
        "case_count": len(cases),
        "macro_metrics": means,
        "delta_graphify_minus_explorer": {
            metric: round(
                means["graphify"][metric] - means["explorer"][metric], 4,
            )
            for metric in metric_names
        },
        "all_selected_graphify_sources_current": all(
            case["graphify"]["status"] in {"ok", "partial_stale"}
            and case["graphify"]["index_sha256"]
            and all(case["graphify"]["source_sha256"].values())
            and case["graphify_seeded"]["retrieval_method"]
            and all(case["graphify_seeded"]["source_sha256"].values())
            for case in cases
        ),
        "queries_with_stale_index_candidates": sum(
            case["graphify"]["status"] in {"partial_stale", "stale"}
            for case in cases
        ),
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument(
        "--dataset", type=Path,
        help="CSV mit query und expected_relevant_files; Standardfixture wird genutzt.",
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument(
        "--require-baseline", action="store_true",
        help="Mit Fehlercode enden, wenn ein Macro-Metrikwert unter Explorer liegt.",
    )
    args = parser.parse_args(argv)
    root = args.project.resolve()
    dataset = args.dataset or (
        root / "tests" / "fixtures" / "explorer_retrieval_eval.csv"
    )
    if not 1 <= args.limit <= 12:
        parser.error("--limit muss zwischen 1 und 12 liegen")
    try:
        report = evaluate(root, dataset.resolve(), limit=args.limit)
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    if not report["all_selected_graphify_sources_current"]:
        return 2
    if args.require_baseline and any(
        delta < 0
        for delta in report["delta_graphify_minus_explorer"].values()
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
