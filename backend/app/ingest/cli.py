"""CLI: python -m app.ingest.cli --company amul --source website|report|all [--dry-run]

Examples:
  # Dry-run one company (prints payload stats, no DB writes)
  python -m app.ingest.cli --company heritage-foods --source all --dry-run

  # Ingest all companies (website + reports)
  python -m app.ingest.cli --source all

  # Only annual reports for two companies
  python -m app.ingest.cli --company amul --company nestle-india --source report
"""
from __future__ import annotations

import argparse
import sys

from app.ingest.config import COMPANIES, all_slugs, get_company
from app.ingest.pipeline import run_all, summarize


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="app.ingest.cli", description="Ingest company websites + annual reports into DB.")
    p.add_argument(
        "--company", action="append", dest="companies", metavar="SLUG",
        help="Company slug (repeatable). Default: all 15. Slugs: " + ", ".join(all_slugs()),
    )
    p.add_argument(
        "--source", choices=["website", "report", "reports", "all"], default="all",
        help="Which source(s) to run (default: all)",
    )
    p.add_argument("--dry-run", action="store_true",
                   help="Extract but roll back DB writes (prints stats only)")
    p.add_argument("--list", action="store_true", help="List company slugs and exit")
    p.add_argument("-q", "--quiet", action="store_true", help="Only print summary")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list:
        for c in COMPANIES:
            print(f"{c.slug:20s} {c.name:30s} {c.website}")
        return 0

    if args.companies:
        unknown = [s for s in args.companies if get_company(s) is None]
        if unknown:
            print(f"Unknown company slug(s): {', '.join(unknown)}", file=sys.stderr)
            print("Use --list to see valid slugs.", file=sys.stderr)
            return 2

    if args.source == "all":
        sources: tuple[str, ...] = ("website", "report")
    elif args.source == "reports":
        sources = ("report",)
    else:
        sources = (args.source,)

    slugs = args.companies  # None → all
    print(f"Running ingest: sources={sources} companies={slugs or 'ALL'} dry_run={args.dry_run}")
    stats = run_all(slugs=slugs, sources=sources, dry_run=args.dry_run)

    if not args.quiet:
        for s in stats:
            print(f"\n== {s.company} ==")
            print(f"  brands+{s.brands_created} products+{s.products_created} "
                  f"skus+{s.skus_created}/~{s.skus_updated} regions+{s.regions_created}"
                  f"(links+{s.region_links}) distributors+{s.distributors_created} "
                  f"prices+{s.price_records} changes+{s.change_events} "
                  f"review+{s.review_items} sources+{s.sources}")
            for e in s.errors:
                print(f"  ERROR: {e}", file=sys.stderr)

    total = summarize(stats)
    print("\n== SUMMARY ==")
    for k, v in total.items():
        print(f"  {k}: {v}")
    if args.dry_run:
        print("  (dry-run: DB writes rolled back)")
    return 1 if total["errors"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
