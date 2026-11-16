"""Expose concise pytest failures as GitHub Actions annotations.

The pytest hook emits each failure directly during a GitHub Actions run. The
JUnit reader is available for local diagnosis. Only short test identifiers,
repository-relative paths, and redacted failure messages are published; the
full traceback remains in the Actions log.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import PurePosixPath

from redaction import redact_text

_MAX_ANNOTATIONS = 30
_MAX_ANNOTATION_CHARS = 1_500
_GITHUB_ANNOTATION_COUNT = 0
_GITHUB_LIMIT_WARNING_EMITTED = False


def _property(value: str) -> str:
    return (
        value.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def _message(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def format_annotation(
    path_value: str, name_value: str, line_value: int | None,
    detail_value: str,
) -> str:
    """Format one redacted, repository-scoped GitHub error command."""
    path = PurePosixPath(path_value.replace("\\", "/"))
    if (
        not path_value
        or path.is_absolute()
        or ".." in path.parts
        or not re.fullmatch(r"[A-Za-z0-9_./-]{1,300}", path.as_posix())
    ):
        path = PurePosixPath("tests")
    name, _ = redact_text(name_value, max_len=300)
    detail, _ = redact_text(detail_value, max_len=_MAX_ANNOTATION_CHARS)
    line_property = (
        f",line={line_value}" if isinstance(line_value, int) and line_value > 0
        else ""
    )
    summary = _message(f"{name}: {detail or 'failure'}")
    return (
        f"::error file={_property(path.as_posix())}{line_property},"
        f"title={_property('pytest failure')}::{summary}"
    )


def emit_test_failure(
    path: str, name: str, line: int | None, detail: str,
) -> None:
    """Write one formatted test failure annotation to stdout."""
    print(format_annotation(path, name, line, detail))


def format_report(report: object) -> str | None:
    """Format one pytest report without writing into pytest's capture."""
    if not getattr(report, "failed", False):
        return None
    location = getattr(report, "location", None)
    if not isinstance(location, tuple) or len(location) < 2:
        path, line = "tests", None
    else:
        path = str(location[0])
        try:
            line = int(location[1]) + 1
        except (TypeError, ValueError):
            line = None
    failure = getattr(report, "longrepr", None)
    crash = getattr(failure, "reprcrash", None)
    detail = str(getattr(crash, "message", "pytest failure"))
    return format_annotation(
        path, str(getattr(report, "nodeid", "pytest test")), line, detail,
    )


def pytest_runtest_logreport(report: object) -> None:
    """Annotate bounded failures directly from pytest on GitHub Actions.

    This compatibility helper is useful to standalone pytest plugins. The
    repository conftest buffers annotations and emits them from
    ``pytest_terminal_summary`` so pytest's output capture cannot swallow the
    GitHub workflow commands.
    """
    global _GITHUB_ANNOTATION_COUNT, _GITHUB_LIMIT_WARNING_EMITTED
    if os.environ.get("GITHUB_ACTIONS") != "true" or not getattr(report, "failed", False):
        return
    if _GITHUB_ANNOTATION_COUNT >= _MAX_ANNOTATIONS:
        if not _GITHUB_LIMIT_WARNING_EMITTED:
            print(
                f"::warning::More than {_MAX_ANNOTATIONS} pytest failures; "
                "additional failures remain in the Actions log."
            )
            _GITHUB_LIMIT_WARNING_EMITTED = True
        return
    annotation = format_report(report)
    if annotation is not None:
        print(annotation)
    _GITHUB_ANNOTATION_COUNT += 1


def emit_annotations(xml_path: str) -> int:
    """Print bounded GitHub workflow commands; return annotation count."""
    root = ET.parse(xml_path).getroot()
    emitted = 0
    for testcase in root.iter("testcase"):
        failure = testcase.find("failure")
        if failure is None:
            failure = testcase.find("error")
        if failure is None:
            continue
        test_name = str(testcase.get("name") or testcase.get("classname") or "pytest test")
        raw_detail = str(failure.get("message") or "")
        if not raw_detail:
            raw_detail = " ".join((failure.text or "").split())
        line = testcase.get("line")
        line_number = int(line) if line and line.isdigit() else None
        emit_test_failure(
            str(testcase.get("file") or ""), test_name, line_number,
            raw_detail,
        )
        emitted += 1
        if emitted >= _MAX_ANNOTATIONS:
            print(
                f"::warning::More than {_MAX_ANNOTATIONS} pytest failures; "
                "additional failures remain in the Actions log.",
            )
            break
    return emitted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("junit_xml")
    args = parser.parse_args()
    try:
        emitted = emit_annotations(args.junit_xml)
    except (OSError, ET.ParseError) as exc:
        print(f"pytest annotation report unavailable: {type(exc).__name__}", file=sys.stderr)
        return 0
    if emitted == 0:
        print("::warning::pytest failed but its JUnit report has no failure entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
