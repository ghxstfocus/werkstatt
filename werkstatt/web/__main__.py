"""Web-Server-Start: python -m werkstatt.web [--port 8000] [--host 0.0.0.0]."""
from __future__ import annotations

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Werkstatt Web-Dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    print(f"Werkstatt-Dashboard: http://{args.host}:{args.port}/")
    print(f"Audit-History:       http://{args.host}:{args.port}/api/projects/werkstatt/audit")
    uvicorn.run(
        "werkstatt.web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
