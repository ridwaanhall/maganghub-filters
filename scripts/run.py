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
    p.add_argument("--deep", required=False, default=None, help="Deep query string (space-separated tokens) to search for; optional when using structured filters")
    p.add_argument("--limit", type=int, default=None, help="Maximum number of results to return")
    p.add_argument("--mode", choices=["and", "or"], default="or", help="Search mode: 'and' (all tokens) or 'or' (any token). Default: or")
    # Structured filters
    p.add_argument("--nama_kabupaten", default=None, help="Filter by one or more kabupaten names (space-separated, treated as OR)")
    p.add_argument("--program_studi", default=None, help="Filter by program studi titles (space-separated, treated as OR)")
    p.add_argument("--posisi", default=None, help="Filter by posisi/role text (space-separated, treated as OR)")
    p.add_argument("--deskripsi_posisi", default=None, help="Filter by words in deskripsi_posisi (space-separated, treated as OR)")
    p.add_argument("--gov", choices=["0", "1", "2"], default="2", help="Filter by government posting: 1 = government posting (government_agency or sub_government_agency present), 0 = neither present, 2 = both (default)")
    p.add_argument("--out", default=None, help="Optional output JSON file to write results")
    p.add_argument("--accept", choices=["desc", "asc"], default=None, help="Sort results by acceptance percentage: 'desc' or 'asc'")

    args = p.parse_args(argv)

    # allow special value 'all' to mean all subdirectories inside the repo `data/` folder
    dir_arg = args.dir
    if dir_arg != "all":
        data_dir = Path(dir_arg)
        if not data_dir.exists():
            logger.error("Data directory does not exist: %s", data_dir)
            return 2
    else:
        # base data directory
        data_dir = Path("data")
        if not data_dir.exists() or not any(data_dir.iterdir()):
            logger.error("Data directory does not exist or is empty: %s", data_dir)
            return 2

    # helper: iterate items from target (single dir or all subdirs)
    def iter_items_from_target():
        if dir_arg == "all":
            # iterate through subdirectories of data in sorted order
            subs = sorted([d for d in data_dir.iterdir() if d.is_dir()], key=lambda p: p.name)
            for sub in subs:
                for it in VacancySearch(sub).iter_items():
                    yield it
        else:
            for it in VacancySearch(data_dir).iter_items():
                yield it

    # helper: search across one dir or all subdirs (respect limit)
    def search_deep_multi(query, limit=None, mode="and"):
        out = []
        if dir_arg == "all":
            subs = sorted([d for d in data_dir.iterdir() if d.is_dir()], key=lambda p: p.name)
            for sub in subs:
                remaining = None if limit is None else max(0, limit - len(out))
                res = VacancySearch(sub).search_deep(query, limit=remaining, mode=mode)
                out.extend(res)
                if limit is not None and len(out) >= limit:
                    break
            return out
        return VacancySearch(data_dir).search_deep(query, limit=limit, mode=mode)

    # If structured filters provided, run a field-specific search. Within each
    # field tokens are treated as OR (match any). The overall combination is
    # AND across fields (item must satisfy all provided filters).
    # treat --gov default ("2") as not an active structured filter; it's only active when user passes 0 or 1
    structured = any([args.nama_kabupaten, args.program_studi, args.posisi, args.deskripsi_posisi]) or (str(args.gov) != "2")

    # Require at least one filter: either --deep or at least one structured flag
    if not structured and not args.deep:
        p.error("either --deep or at least one structured filter (--nama_kabupaten/--program_studi/--posisi) must be provided")

    results = []
    if structured:
        # import helper to parse program_studi values
        from maganghub_client.search import _parse_program_studi

        # prepare token lists (lowercased)
        nk_tokens = [t.lower() for t in (args.nama_kabupaten or "").split() if t.strip()]
        ps_tokens = [t.lower() for t in (args.program_studi or "").split() if t.strip()]
        pos_tokens = [t.lower() for t in (args.posisi or "").split() if t.strip()]
        desc_tokens = [t.lower() for t in (args.deskripsi_posisi or "").split() if t.strip()]

        def matches_kab(item) -> bool:
            if not nk_tokens:
                return True
            cp = item.get("perusahaan") or {}
            raw_kab = (cp.get("nama_kabupaten") or "")
            clean_kab = raw_kab.replace("KAB.", "").replace("KAB", "").replace("KOTA.", "").replace("KOTA", "").replace(".", "").strip().lower()
            prov = (cp.get("nama_provinsi") or "").lower()
            # match any token against cleaned kabupaten or province
            for tok in nk_tokens:
                if tok in clean_kab or tok in prov:
                    return True
            return False

        def matches_program(item) -> bool:
            if not ps_tokens:
                return True
            titles = [t.lower() for t in _parse_program_studi(item.get("program_studi"))]
            for tok in ps_tokens:
                for title in titles:
                    if tok in title:
                        return True
            return False

        def matches_posisi(item) -> bool:
            if not pos_tokens:
                return True
            text_parts = []
            if item.get("posisi"):
                text_parts.append(str(item.get("posisi")))
            text = "\n".join(text_parts).lower()
            for tok in pos_tokens:
                if tok in text:
                    return True
            return False

        def matches_deskripsi(item) -> bool:
            if not desc_tokens:
                return True
            parts = []
            # position description
            if item.get("deskripsi_posisi"):
                parts.append(str(item.get("deskripsi_posisi")))
            # also consider the posisi/title (sometimes keywords appear there)
            if item.get("posisi"):
                parts.append(str(item.get("posisi")))
            # company description may contain keywords related to required tech
            cp = item.get("perusahaan") or {}
            if cp.get("deskripsi_perusahaan"):
                parts.append(str(cp.get("deskripsi_perusahaan")))
            # additional fields like syarat_khusus
            if item.get("syarat_khusus"):
                parts.append(str(item.get("syarat_khusus")))

            text = "\n".join(parts).lower()
            for tok in desc_tokens:
                if tok in text:
                    return True
            return False

        def matches_gov(item) -> bool:
            # args.gov values: "1" => only government postings; "0" => only non-government; "2" => both (default)
            gv = str(args.gov or "2").strip()
            ga = item.get("government_agency") or {}
            sga = item.get("sub_government_agency") or {}
            ga_name = (ga.get("government_agency_name") or "")
            sga_name = (sga.get("sub_government_agency_name") or "")
            has_any = bool(str(ga_name).strip()) or bool(str(sga_name).strip())
            if gv == "1":
                return has_any
            if gv == "0":
                return not has_any
            # gv == "2" or unknown -> accept both
            return True

        for item in iter_items_from_target():
            if matches_kab(item) and matches_program(item) and matches_posisi(item) and matches_deskripsi(item) and matches_gov(item):
                results.append(item)
                if args.limit is not None and len(results) >= args.limit:
                    break
    else:
        results = search_deep_multi(args.deep, limit=args.limit, mode=args.mode)

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
            # item.get("id_posisi") or "-",
            posisi or "-",
            nama_perusahaan or "-",
            nama_kab or "-",
            jumlah_kuota if jumlah_kuota is not None else "-",
            jumlah_terdaftar if jumlah_terdaftar is not None else "-",
            accept_pct_text,
        ])

        # enrich item for optional saving
        item_copy = dict(item)
        item_copy["_applicants_per_slot"] = applicants_per_slot
        item_copy["_acceptance_prob"] = acceptance_prob
        enriched_results.append(item_copy)

    # Optionally sort by acceptance percentage if requested
    if args.accept and enriched_results:
        if args.accept == "desc":
            # None -> treat as -1 so they go to the end
            sort_key = lambda it: (it.get("_acceptance_prob") if it.get("_acceptance_prob") is not None else -1)
            reverse = True
        else:
            # asc: None -> put at end
            sort_key = lambda it: (it.get("_acceptance_prob") if it.get("_acceptance_prob") is not None else float("inf"))
            reverse = False

        paired = list(zip(rows, enriched_results))
        paired.sort(key=lambda pair: sort_key(pair[1]), reverse=reverse)
        rows, enriched_results = zip(*paired) if paired else ([], [])
        rows = list(rows)
        enriched_results = list(enriched_results)

    # Try to pretty-print a table using tabulate if available
    try:
        from tabulate import tabulate

        headers = ["posisi", "perusahaan", "kabupaten", "kuota", "terdaftar", "accept%"]
        print(tabulate(rows, headers=headers, tablefmt="github"))
    except Exception:
        # Fallback to manual formatting
        col_headers = ["posisi", "perusahaan", "kabupaten", "kuota", "terdaftar", "accept%"]
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
