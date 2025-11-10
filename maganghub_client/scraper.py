"""Scraper for MagangHub vacancies API.

Provides VacanciesScraper which paginates through the `vacancies-aktif` endpoint
and saves each page as JSON into a target directory (filename = `<page>.json`).

Design goals:
- Small, testable OOP class with clear public methods
- Robust requests.Session with retries and backoff
- Safe file writing and logging
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


class VacanciesScraper:
    DEFAULT_BASE = "https://maganghub.kemnaker.go.id/be/v1/api/"

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 15,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = (base_url or self.DEFAULT_BASE).rstrip("/") + "/"
        self.timeout = timeout
        self.session = session or self._build_session(max_retries, backoff_factor)

    def _build_session(self, max_retries: int, backoff_factor: float) -> requests.Session:
        s = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("HEAD", "GET", "OPTIONS"),
        )
        adapter = HTTPAdapter(max_retries=retries)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        return s

    def _build_url(self, path: str) -> str:
        return self.base_url + path.lstrip("/")

    def fetch_page(
        self, *, page: int = 1, limit: int = 100, kode_provinsi: Optional[int] = None, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Fetch a single page from `list/vacancies-aktif`.

        Returns the parsed JSON as a dict.
        Raises requests.RequestException on network/HTTP errors.
        """
        path = "list/vacancies-aktif"
        url = self._build_url(path)
        q = {
            "order_by": "jumlah_kuota",
            "order_direction": "DESC",
            "page": page,
            "limit": limit,
        }
        if kode_provinsi is not None:
            q["kode_provinsi"] = kode_provinsi
        if params:
            q.update(params)

        logger.debug("Fetching page %s url=%s params=%s", page, url, q)
        resp = self.session.get(url, params=q, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def save_page_json(self, data: Dict[str, Any], save_dir: str, page: int) -> str:
        """Save a page dict to `save_dir/<page>.json` and return the path."""
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, f"{page}.json")
        # add a scraped timestamp (UTC ISO 8601) to the saved payload
        ts = datetime.now(timezone.utc).isoformat()
        if isinstance(data, dict):
            to_write = dict(data)
            to_write["_scraped_at"] = ts
        else:
            # preserve non-dict payloads by wrapping them
            to_write = {"data": data, "_scraped_at": ts}

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(to_write, fh, ensure_ascii=False, indent=2)
        logger.info("Saved page %s at %s -> %s", page, ts, path)
        return path

    def scrape_all(
        self,
        save_dir: str,
        start_page: int = 1,
        limit: int = 100,
        kode_provinsi: Optional[int] = None,
        max_pages: Optional[int] = None,
        delay: float = 0.0,
    ) -> int:
        """Scrape pages beginning at `start_page`, saving each page as `<page>.json`.

        Stops when the API returns an empty `data` list or when `max_pages` is reached.
        Returns the number of pages saved.
        """
        page = start_page
        saved = 0
        while True:
            if max_pages is not None and saved >= max_pages:
                logger.debug("Reached max_pages=%s, stopping", max_pages)
                break

            try:
                result = self.fetch_page(page=page, limit=limit, kode_provinsi=kode_provinsi)
            except Exception as exc:
                logger.error("Failed to fetch page %s: %s", page, exc)
                raise

            # Defensive checks: prefer `data` key
            items = []
            if isinstance(result, dict):
                items = result.get("data") if isinstance(result.get("data"), list) else []
            elif isinstance(result, list):
                items = result

            # Save the raw page regardless (to keep parity with your requirement)
            self.save_page_json(result, save_dir, page)
            saved += 1

            # Stop if there's no data on this page
            if not items:
                logger.info("No data found on page %s, stopping.", page)
                break

            # prepare next
            page += 1
            if delay and page:
                time.sleep(delay)

        return saved


__all__ = ["VacanciesScraper"]
