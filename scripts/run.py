"""Simple CLI runner for deep searching saved MagangHub pages.

Example:
    python scripts/run.py --dir data/prov_34 --deep "sleman yogyakarta marketing Manajemen Pemasaran"
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Ensure repo root is importable when running this script directly
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from maganghub_client.search import VacancySearch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Deep search saved MagangHub vacancy pages")
    p.add_argument("--dir", default="data", help="Directory containing per-page JSON files")
    p.add_argument("--deep", required=True, help="Deep query string (space-separated tokens) to search for")
    p.add_argument("--limit", type=int, default=None, help="Maximum number of results to return")
    p.add_argument("--out", default=None, help="Optional output JSON file to write results")

    args = p.parse_args(argv)

    data_dir = Path(args.dir)
    if not data_dir.exists():
        logger.error("Data directory does not exist: %s", data_dir)
        return 2

    search = VacancySearch(data_dir)
    results = search.search_deep(args.deep, limit=args.limit)

    # Compute probability and prepare table rows
    rows = []
    enriched_results = []
    for i, item in enumerate(results, start=1):
        posisi = item.get("posisi")
        perusahaan = item.get("perusahaan", {})
        nama_perusahaan = perusahaan.get("nama_perusahaan") if isinstance(perusahaan, dict) else None
        nama_kab = perusahaan.get("nama_kabupaten") if isinstance(perusahaan, dict) else None

        # parse jumlah_kuota and jumlah_terdaftar safely
        def _safe_int(v):
            try:
                return int(v)
            except Exception:
                return None

        jumlah_kuota = _safe_int(item.get("jumlah_kuota"))
        jumlah_terdaftar = _safe_int(item.get("jumlah_terdaftar"))

        applicants_per_slot = None
        acceptance_prob = None
        if jumlah_kuota and jumlah_kuota != 0:
            jt = jumlah_terdaftar if jumlah_terdaftar is not None else 0
            try:
                applicants_per_slot = (jt + 1) / jumlah_kuota
            except Exception:
                applicants_per_slot = None
            try:
                # estimated acceptance probability under simple random selection
                acceptance_prob = jumlah_kuota / (jt + 1) if (jt + 1) > 0 else 1.0
                # cap to 1.0
                if acceptance_prob > 1.0:
                    acceptance_prob = 1.0
            except Exception:
                acceptance_prob = None

        app_text = f"{applicants_per_slot:.2f}" if isinstance(applicants_per_slot, float) else "-"
        accept_pct_text = f"{(acceptance_prob * 100):.2f}%" if isinstance(acceptance_prob, float) else "-"

        rows.append([
            i,
            posisi or "-",
            nama_perusahaan or "-",
            nama_kab or "-",
            jumlah_kuota if jumlah_kuota is not None else "-",
            jumlah_terdaftar if jumlah_terdaftar is not None else "-",
            app_text,
            accept_pct_text,
        ])

        # enrich item for optional saving
        item_copy = dict(item)
        item_copy["_applicants_per_slot"] = applicants_per_slot
        item_copy["_acceptance_prob"] = acceptance_prob
        enriched_results.append(item_copy)

    # Try to pretty-print a table using tabulate if available
    try:
        from tabulate import tabulate

        headers = ["#", "posisi", "perusahaan", "kabupaten", "kuota", "terdaftar", "app/slot", "accept%"]
        print(tabulate(rows, headers=headers, tablefmt="github"))
    except Exception:
        # Fallback to manual formatting
        col_headers = ["#", "posisi", "perusahaan", "kabupaten", "kuota", "terdaftar", "app/slot", "accept%"]
        col_widths = [max(len(str(cell)) for cell in col) for col in zip(*([[h for h in col_headers]] + rows))]
        fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
        headers = col_headers
        print(fmt.format(*headers))
        print("-" * (sum(col_widths) + 2 * (len(col_widths) - 1)))
        for r in rows:
            print(fmt.format(*[str(c) for c in r]))

    print(f"\nTotal matches: {len(results)}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(enriched_results, fh, ensure_ascii=False, indent=2)
        logger.info("Saved results to %s", out_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
