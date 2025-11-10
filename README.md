MagangHub Vacancies — scraper and search tools
=============================================

A small, professional command-line toolkit to scrape the MagangHub public
vacancies API and search the saved results locally.

This repository contains:
- `maganghub_client/` — light client, models, scraper and search utilities.
- `scripts/scrape_and_save.py` — paginate the API and save each page as `<page>.json`.
- `scripts/build_all_json.py` — optional: merge per-page files into a single `all.json`.
- `scripts/run.py` — field-aware search CLI that prints a readable table and can save results.
- `data/` — where scraped JSON pages are saved (not committed).

Quick concepts
--------------
1. Scrape from the API and save pages to disk.
2. (Optional) Merge saved pages into `all.json`.
3. Run `scripts/run.py` to filter and inspect results locally.

Prerequisites
-------------
- Python 3.8+
- A virtual environment (recommended).

Install
-------
From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

If you prefer not to install `tabulate`, the search CLI will fall back to a simple text table.

1) Scrape (save pages)
----------------------
Use the scraper to fetch pages and save them under a directory such as `data/prov_33` (folder is created automatically). Each page is saved as `1.json`, `2.json`, ... until the API returns an empty `data` list.

Example (province code 33):

```powershell
python .\scripts\scrape_and_save.py --save-dir data\prov_33 --kode_provinsi 33
```

Options
- `--save-dir` (required) — directory to write pages (created if missing)
- `--start-page` — default 1
- `--limit` — items per page (default 100)
- `--max-pages` — optional cap
- `--delay` — seconds between requests (politeness)

Notes
- Saved files are the raw JSON responses from the API. Keep the `data/` folder private — it may contain many files.

2) (Optional) Merge pages into a single file
--------------------------------------------
If you prefer a single file, run the merger which reads numeric `*.json` files and writes `all.json`:

```powershell
python .\scripts\build_all_json.py --dir data\prov_33
```

Output structure (simple):
```json
{ "data": [ ...all items... ], "meta": { "pages": [ {"file":"1.json","count":10}, ...], "total_items": N }}
```

3) Search saved pages (recommended)
-----------------------------------
The main interactive CLI is `scripts/run.py`. It supports two modes:
- Free-text `--deep` search across many fields (posisi, deskripsi_posisi, perusahaan, program_studi, jenjang).
- Structured filters that let you specify fields explicitly (recommended for advanced queries).

Examples

Structured search (no `--deep` required):

```powershell
python .\scripts\run.py --dir data\prov_33 --nama_kabupaten "boyolali surakarta sukoharjo" --program_studi "hukum ekonomi islam" --posisi "" --deskripsi_posisi "" --accept desc
```

- `--nama_kabupaten` — space-separated tokens (OR within field). Matches cleaned `nama_kabupaten` (prefixes like `KAB.` / `KOTA` are removed) or province. Example: `boyolali`.
- `--program_studi` — tokens matched against parsed `program_studi` titles.
- `--posisi` — tokens matched against `posisi` text.
- `--deskripsi_posisi` — tokens matched against `deskripsi_posisi`.
- `--accept` — `desc` or `asc` to sort results by estimated acceptance percentage.
- `--dir all` — special value: search across every subfolder under `data/` (e.g. `data/prov_33`, `data/prov_34`, ...).
- `--out` — save matched items (with computed fields) to a JSON file.

Free-text search (simple):

```powershell
python .\scripts\run.py --dir data\prov_33 --deep "sleman yogyakarta marketing Manajemen Pemasaran"
```

- `--mode` controls token logic for `--deep` (`and` or `or`, default `or`).

What the table shows
--------------------
The table displays these columns:
- `id_posisi` — the vacancy unique id
- `posisi` — position title
- `perusahaan` — company name
- `kabupaten` — district/city
- `kuota` — jumlah_kuota (slots)
- `terdaftar` — jumlah_terdaftar (registered applicants)
- `accept%` — estimated acceptance probability as a percentage, computed as:

  acceptance_prob = min(1.0, jumlah_kuota / (jumlah_terdaftar + 1))

This is a simple, naive estimate assuming uniform random selection. It is only an approximate indicator.

Saved JSON
----------
If you use `--out results.json`, each saved item will include two helper fields:
- `_applicants_per_slot` — (jumlah_terdaftar + 1) / jumlah_kuota (raw competitiveness)
- `_acceptance_prob` — acceptance probability as a fraction (0..1)

Troubleshooting
---------------
- If you get `ModuleNotFoundError: No module named 'maganghub_client'` when running a script directly, run from the repo root and the scripts already add the project root to `sys.path` so `python scripts\run.py ...` should work. If you still see errors, ensure your working directory is the project root and your virtualenv is activated.

- If `tabulate` is not installed, the CLI falls back to a readable ASCII table.

Development notes
-----------------
- `maganghub_client/` contains a small client, dataclasses and parsing helpers. The code attempts to be defensive: it preserves raw JSON under `raw` for fields we don't explicitly map.
- The scraper uses `requests.Session` with retry/backoff for robustness.

Next improvements (optional)
- Add fuzzy matching (typo tolerance) for program or posisi using `rapidfuzz`.
- Add exact-phrase search and quoted-space parsing for `--deep`.
- Export CSV/Excel with selected columns.

License & attribution
---------------------
Use this code responsibly. The API belongs to Kementerian Ketenagakerjaan (Kemnaker). This tool only consumes their public API and stores local copies of responses for offline searching and analysis.

Contact / Support
-----------------
If you want changes to the CLI flags, sorting, or output format, tell me which behavior you prefer and I will update the scripts accordingly.
