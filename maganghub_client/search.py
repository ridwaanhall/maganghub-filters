"""Search utilities for MagangHub saved pages.

Provides `VacancySearch` which loads per-page JSON files and performs a
case-insensitive "deep" search across several fields including
`perusahaan.nama_kabupaten`, `perusahaan.nama_provinsi`, `posisi`, and
`program_studi` titles (which are stored as JSON-encoded strings).

The search is simple and deterministic: split the query into tokens and
require every token to be present somewhere in the searchable text of a
vacancy (AND semantic). Multi-word fields like "Manajemen Pemasaran" will
match if both words appear in the vacancy's program_studi/title fields.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


def _parse_program_studi(value: Any) -> List[str]:
    """Return list of program_studi titles from API field which may be
    a JSON-encoded string or already a list.
    """
    if not value:
        return []
    if isinstance(value, list):
        # items may be dicts with 'title'
        out = []
        for it in value:
            if isinstance(it, dict):
                title = it.get("title")
                if title:
                    out.append(str(title))
            elif isinstance(it, str):
                out.append(it)
        return out
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return _parse_program_studi(parsed)
        except Exception:
            # not JSON; treat as single-title string
            return [value]
    return []


class VacancySearch:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise ValueError(f"data_dir does not exist: {self.data_dir}")

    def iter_page_files(self) -> Iterable[Path]:
        # yield numeric .json files sorted by numeric stem
        files = []
        for p in self.data_dir.glob("*.json"):
            if p.name == "all.json":
                continue
            try:
                int(p.stem)
                files.append(p)
            except Exception:
                continue
        for p in sorted(files, key=lambda x: int(x.stem)):
            yield p

    def iter_items(self) -> Iterable[Dict[str, Any]]:
        for p in self.iter_page_files():
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    j = json.load(fh)
            except Exception as exc:
                logger.warning("Skipping file %s due to load error: %s", p, exc)
                continue
            if isinstance(j, dict) and isinstance(j.get("data"), list):
                for item in j.get("data"):
                    yield item
            elif isinstance(j, list):
                for item in j:
                    yield item

    def _make_search_text(self, item: Dict[str, Any]) -> str:
        parts: List[str] = []
        # posisi and deskripsi
        if item.get("posisi"):
            parts.append(str(item.get("posisi")))
        if item.get("deskripsi_posisi"):
            parts.append(str(item.get("deskripsi_posisi")))

        # perusahaan fields (nama_kabupaten, nama_provinsi, nama_perusahaan, alamat)
        cp = item.get("perusahaan") or {}
        for k in ("nama_kabupaten", "nama_provinsi", "nama_perusahaan", "alamat"):
            if cp.get(k):
                parts.append(str(cp.get(k)))

        # also include a cleaned form of nama_kabupaten without prefixes like 'KAB.' or 'KOTA'
        raw_kab = (cp.get("nama_kabupaten") or "")
        if raw_kab:
            clean = raw_kab.replace("KAB.", "").replace("KAB", "").replace("KOTA.", "").replace("KOTA", "")
            clean = clean.replace(".", "").strip()
            if clean:
                parts.append(clean)

        # program_studi (JSON-encoded string)
        ps_titles = _parse_program_studi(item.get("program_studi"))
        parts.extend(ps_titles)

        # jenjang list
        jen = item.get("jenjang")
        if jen:
            if isinstance(jen, str):
                try:
                    parsed = json.loads(jen)
                    if isinstance(parsed, list):
                        for it in parsed:
                            parts.append(str(it))
                except Exception:
                    parts.append(jen)
            elif isinstance(jen, list):
                for it in jen:
                    parts.append(str(it))

        # join and lowercase for simple substring search
        return "\n".join(parts).lower()

    def search_deep(self, query: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search items using a whitespace tokenized AND query.

        Returns matching raw items (not converted to Vacancy dataclass).
        """
        if not query:
            return []
        tokens = [t.strip().lower() for t in query.split() if t.strip()]
        out: List[Dict[str, Any]] = []
        for item in self.iter_items():
            text = self._make_search_text(item)
            matched = True
            for tok in tokens:
                if tok not in text:
                    matched = False
                    break
            if matched:
                out.append(item)
                if limit is not None and len(out) >= limit:
                    break
        return out


__all__ = ["VacancySearch", "_parse_program_studi"]
