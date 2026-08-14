"""CLI Procure Guard backend."""
from __future__ import annotations

import argparse

from app.services.ingest import ingest_sops


def main() -> None:
    parser = argparse.ArgumentParser(description="Procure Guard AI backend CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Ingest dokumen SOP vendor")
    ingest.add_argument("--dir", required=True, help="Direktori berisi PDF/MD SOP vendor")
    args = parser.parse_args()

    if args.command == "ingest":
        count = ingest_sops(args.dir)
        print(f"OK: {count} chunk dokumen di-ingest")


if __name__ == "__main__":
    main()