from pathlib import Path
from typing import List

from django.shortcuts import render

from maganghub_client.search import VacancySearch


"""Path to the repository `data/` directory. Use parents[2] because this
module lives at <repo>/web/core/views.py and the repo root is two levels up.
"""
DATA_ROOT = Path(__file__).resolve().parents[2] / "data"


def filter_view(request):
	"""Render a simple filter page that reuses VacancySearch.

	Query parameters:
	- q: search query (tokens separated by whitespace)
	- prov: province folder name (e.g. prov_33 or prov_34). default: prov_33 if exists
	- mode: 'and' or 'or' (default 'and')
	- limit: integer limit for results (optional)
	"""
	q = request.GET.get("q", "").strip()
	prov = request.GET.get("prov") or "prov_33"
	mode = request.GET.get("mode") or "and"
	limit = request.GET.get("limit")
	try:
		limit_val = int(limit) if limit else None
	except Exception:
		limit_val = None

	# determine data dir
	data_dir = DATA_ROOT / prov
	results: List[dict] = []
	error = None

	# extra filters
	kabupaten = request.GET.get("kabupaten", "").strip()
	program_studi_q = request.GET.get("program_studi", "").strip()
	government_agency_q = request.GET.get("government_agency", "").strip()

	try:
		vs = VacancySearch(data_dir)
	except Exception as exc:
		vs = None
		error = str(exc)

	if vs and q:
		try:
			results = vs.search_deep(q, limit=limit_val, mode=mode)
		except Exception as exc:
			error = str(exc)
	elif vs and not q:
		# no free-text query - iterate all items
		results = list(vs.iter_items())

	# apply post-filters (kabupaten, program_studi, government_agency)
	def _match_prog(item):
		if not program_studi_q:
			return True
		titles = []
		ps = item.get("program_studi")
		# reuse parse logic from VacancySearch module
		try:
			from maganghub_client.search import _parse_program_studi

			titles = _parse_program_studi(ps)
		except Exception:
			titles = [ps] if ps else []
		lowered = "\n".join([str(t).lower() for t in titles])
		return program_studi_q.lower() in lowered

	def _match_kab(item):
		if not kabupaten:
			return True
		cp = item.get("perusahaan") or {}
		nk = (cp.get("nama_kabupaten") or "").lower()
		# allow substring match
		return kabupaten.lower() in nk

	def _match_gov(item):
		if not government_agency_q:
			return True
		ga = (item.get("government_agency") or {}).get("government_agency_name") or ""
		sga = (item.get("sub_government_agency") or {}).get("sub_government_agency_name") or ""
		return (government_agency_q.lower() in str(ga).lower()) or (government_agency_q.lower() in str(sga).lower())

	if results:
		filtered = [it for it in results if _match_kab(it) and _match_prog(it) and _match_gov(it)]
	else:
		filtered = []

	results = filtered

	# list available provinces under data
	prov_choices = []
	try:
		for p in (DATA_ROOT).iterdir():
			if p.is_dir() and p.name.startswith("prov_"):
				prov_choices.append(p.name)
	except Exception:
		prov_choices = []

	# collect kabupaten and government agency choices from the dataset
	kab_choices = set()
	gov_choices = set()
	try:
		if vs:
			for it in vs.iter_items():
				cp = it.get("perusahaan") or {}
				nk = cp.get("nama_kabupaten")
				if nk:
					kab_choices.add(nk)
				ga = (it.get("government_agency") or {}).get("government_agency_name")
				if ga:
					gov_choices.add(ga)
				sga = (it.get("sub_government_agency") or {}).get("sub_government_agency_name")
				if sga:
					gov_choices.add(sga)
	except Exception:
		pass

	kab_choices = sorted(kab_choices)
	gov_choices = sorted(gov_choices)

	# prepare display-friendly results (parse program_studi, jenjang)
	display_results = []
	if results:
		try:
			from maganghub_client.search import _parse_program_studi
		except Exception:
			_parse_program_studi = None

		import json

		for it in results:
			cp = it.get("perusahaan") or {}
			ps_raw = it.get("program_studi")
			if _parse_program_studi:
				try:
					ps_list = _parse_program_studi(ps_raw)
				except Exception:
					ps_list = []
			else:
				# try to decode JSON or fallback to string
				try:
					parsed = json.loads(ps_raw) if isinstance(ps_raw, str) else ps_raw
					if isinstance(parsed, list):
						ps_list = [p.get("title") if isinstance(p, dict) else str(p) for p in parsed]
					else:
						ps_list = [str(parsed)]
				except Exception:
					ps_list = [str(ps_raw)] if ps_raw else []

			jenjang_raw = it.get("jenjang")
			jenjang_display = jenjang_raw
			try:
				if isinstance(jenjang_raw, str):
					jen = json.loads(jenjang_raw)
					jenjang_display = ", ".join(str(x) for x in jen) if isinstance(jen, list) else str(jen)
			except Exception:
				jenjang_display = jenjang_raw

			display_results.append({
				"posisi": it.get("posisi"),
				"perusahaan": cp.get("nama_perusahaan"),
				"nama_kabupaten": cp.get("nama_kabupaten"),
				"nama_provinsi": cp.get("nama_provinsi"),
				"program_studi": ", ".join(ps_list),
				"jenjang": jenjang_display,
				"id_perusahaan": (cp.get("id_perusahaan") or it.get("program", {}).get("id_perusahaan")),
				"id_posisi": it.get("id_posisi"),
				"deskripsi_posisi": it.get("deskripsi_posisi"),
			})

	# use display_results in template
	results = display_results

	context = {
		"query": q,
		"prov": prov,
		"mode": mode,
		"limit": limit or "",
		"results": results,
		"error": error,
		"prov_choices": sorted(prov_choices),
		"kab_choices": kab_choices,
		"gov_choices": gov_choices,
	}
	return render(request, "core/filter.html", context)
