from pathlib import Path
from typing import List
import json

from django.shortcuts import render

from maganghub_client.search import VacancySearch


"""Path to the repository `data/` directory. Use parents[2] because this
module lives at <repo>/web/core/views.py and the repo root is two levels up.
"""
DATA_ROOT = Path(__file__).resolve().parents[2] / "data"


def filter_view(request):
	"""Render a simple filter page that reuses VacancySearch.

    Query parameters (all filters):
    - prov: one or more province folder names (e.g. prov_33). multi-select
    - kabupaten: one or more kabupaten names. multi-select
    - government_agency: substring filter for government agency name
    - program_studi: substring filter for program studi title
	"""

	# selected provinces (multi-select). If none provided, use all available prov_ dirs.
	prov_list = request.GET.getlist("prov")
	if not prov_list:
		# default to prov_33 if present, otherwise empty and we'll discover available provinces
		prov_list = ["prov_33"]

	# extra filters
	kabupaten_list = request.GET.getlist("kabupaten")
	program_studi_q = request.GET.get("program_studi", "").strip()
	government_agency_present = request.GET.get("government_agency_present", "both")

	# iterate items across selected provinces
	results: List[dict] = []
	error = None
	all_items = []
	vs_instances = []
	for prov in prov_list:
		data_dir = DATA_ROOT / prov
		try:
			vs = VacancySearch(data_dir)
			vs_instances.append(vs)
			all_items.extend(list(vs.iter_items()))
		except Exception:
			# skip missing/invalid province directories
			continue

	results = all_items

	# apply post-filters (kabupaten, program_studi, government_agency)
	def _match_prog(item):
		# if no program_studi filter provided, accept all
		if not program_studi_q:
			return True
		# split the user input into tokens and match if ANY token appears in the
		# program_studi titles (OR semantic as requested)
		tokens = [t.strip().lower() for t in program_studi_q.split() if t.strip()]
		if not tokens:
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
		return any(tok in lowered for tok in tokens)

	def _match_kab(item):
		if not kabupaten_list:
			return True
		cp = item.get("perusahaan") or {}
		nk = (cp.get("nama_kabupaten") or "")
		if not nk:
			return False
		# match if any selected kabupaten is a substring of the item's nama_kabupaten or exact match
		for k in kabupaten_list:
			if k and (k.lower() in nk.lower()):
				return True
		return False

	def _match_gov(item):
		# three-state filter: both => accept all; true => must have govt agency name; false => must NOT have one
		if government_agency_present == "both":
			return True
		ga = (item.get("government_agency") or {}).get("government_agency_name")
		sga = (item.get("sub_government_agency") or {}).get("sub_government_agency_name")
		has_gov = bool((ga and str(ga).strip()) or (sga and str(sga).strip()))
		if government_agency_present == "true":
			return has_gov
		if government_agency_present == "false":
			return not has_gov
		return True

	if results:
		filtered = [it for it in results if _match_kab(it) and _match_prog(it) and _match_gov(it)]
	else:
		filtered = []

	results = filtered

	# list available provinces under data
	# discover available provinces for the province multi-select
	prov_choices = []
	try:
		for p in (DATA_ROOT).iterdir():
			if p.is_dir() and p.name.startswith("prov_"):
				prov_choices.append(p.name)
	except Exception:
		prov_choices = []

	# build mapping of province -> kabupaten list (for client-side dynamic filtering)
	prov_to_kabs = {}
	try:
		for prov_name in prov_choices:
			kset = set()
			try:
				vs_tmp = VacancySearch(DATA_ROOT / prov_name)
				for it in vs_tmp.iter_items():
					cp = it.get("perusahaan") or {}
					nk = cp.get("nama_kabupaten")
					if nk:
						kset.add(nk)
			except Exception:
				pass
			prov_to_kabs[prov_name] = sorted(kset)
	except Exception:
		prov_to_kabs = {}

	# collect kabupaten and government agency choices from the dataset
	kab_choices = set()
	gov_choices = set()
	try:
		for vs in vs_instances:
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

	# (no per-agency multi-select anymore)

	# prepare display-friendly results (parse program_studi, jenjang)
	display_results = []
	if results:
		try:
			from maganghub_client.search import _parse_program_studi
		except Exception:
			_parse_program_studi = None


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
		"prov_choices": sorted(prov_choices),
		"selected_provs": prov_list,
		"selected_kabs": kabupaten_list,
	"program_studi_q": program_studi_q,
	"government_agency_present": government_agency_present,
		"results": results,
		"error": error,
		"kab_choices": kab_choices,
		"gov_choices": gov_choices,
		"prov_to_kabs_json": json.dumps(prov_to_kabs),
	}
	return render(request, "core/filter.html", context)
