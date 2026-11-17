"""Small repository retrieval evaluation with explicit gold source sets."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from werkstatt.explorer import _rank_source_files


def test_repository_retrieval_recall_and_first_relevant_rank() -> None:
    root = Path(__file__).resolve().parents[1]
    dataset_path = root / "tests" / "fixtures" / "explorer_retrieval_eval.csv"
    with dataset_path.open(encoding="utf-8", newline="") as dataset_file:
        cases = [
            (
                row["query"],
                set(row["expected_relevant_files"].split(";")),
            )
            for row in csv.DictReader(dataset_file)
        ]
    precisions: list[float] = []
    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    case_diagnostics: list[dict[str, object]] = []

    for query, expected_relevant in cases:
        selected, manifest = _rank_source_files(root, query, limit=5)
        selected_files = [item["file"] for item in selected]
        assert manifest["index_scan_succeeded"] is True
        assert manifest["omissions_are_not_negative_evidence"] is True
        assert len(selected_files) <= 5
        hits = expected_relevant.intersection(selected_files)
        precisions.append(len(hits) / len(selected_files) if selected_files else 0.0)
        recalls.append(len(hits) / len(expected_relevant))
        case_diagnostics.append({
            "query": query,
            "expected": sorted(expected_relevant),
            "selected": selected_files,
            "hits": sorted(hits),
            "indexed_file_count": manifest.get("indexed_file_count"),
            "content_scanned_file_count": manifest.get(
                "content_scanned_file_count"
            ),
            "index_truncated": manifest.get("index_truncated"),
            "inventory_source": manifest.get("inventory_source"),
            "read_failures": manifest.get("read_failures"),
            "discriminative_token_count": manifest.get(
                "discriminative_token_count"
            ),
        })
        first_rank = next(
            (index for index, path in enumerate(selected_files, 1)
             if path in expected_relevant),
            None,
        )
        reciprocal_ranks.append(1 / first_rank if first_rank else 0.0)

    assert min(precisions) == 1.0, case_diagnostics
    # A query may have more gold-relevant sources than the context top-k.
    # Require the maximum recall that this bounded result can provide.
    capacity_recall = [
        min(1.0, 5 / len(expected_relevant))
        for _, expected_relevant in cases
    ]
    assert all(
        recall == attainable
        for recall, attainable in zip(recalls, capacity_recall, strict=True)
    ), case_diagnostics
    assert min(reciprocal_ranks) == 1.0, case_diagnostics


def test_role_information_queries_retrieve_required_sources_with_live_hashes() -> None:
    """Critical role handoffs retain their required source files and provenance."""
    root = Path(__file__).resolve().parents[1]
    dataset_path = (
        root / "tests" / "fixtures" / "explorer_role_retrieval_eval.csv"
    )
    with dataset_path.open(encoding="utf-8", newline="") as dataset_file:
        cases = [
            (
                row["query"],
                set(row["required_files"].split(";")),
                set(filter(None, row.get("forbidden_files", "").split(";"))),
            )
            for row in csv.DictReader(dataset_file)
        ]

    for query, required_files, forbidden_files in cases:
        selected, manifest = _rank_source_files(root, query, limit=5)
        selected_by_path = {item["file"]: item for item in selected}
        assert required_files <= selected_by_path.keys(), {
            "query": query,
            "required": sorted(required_files),
            "selected": list(selected_by_path),
            "manifest": manifest,
        }
        assert not forbidden_files.intersection(selected_by_path), {
            "query": query,
            "known_irrelevant_sources_selected": sorted(
                forbidden_files.intersection(selected_by_path),
            ),
            "selected": list(selected_by_path),
            "manifest": manifest,
        }
        assert manifest["index_scan_succeeded"] is True
        assert manifest["omissions_are_not_negative_evidence"] is True
        for relative_path in required_files:
            source_path = root / relative_path
            source_bytes = source_path.read_bytes()
            assert selected_by_path[relative_path]["source_sha256"] == hashlib.sha256(
                source_bytes
            ).hexdigest()
            assert selected_by_path[relative_path]["source_bytes"] == len(
                source_bytes
            )
            if relative_path == "werkstatt/phase_state.py":
                assert "phase_state" in selected_by_path[relative_path][
                    "matched_explicit_symbols"
                ]
