#!/usr/bin/env python3
"""
Oculon Public API Client - Version 2 (Public Component)
======================================================
Provides a type-safe, lightweight Python interface to the Oculon v2 backend.
Adheres to the decoupled architecture:
- Consumes public v2 endpoints from the private backend runtime.
- Never ships or embeds proprietary algorithm source code.
- Supports both local offline caching and remote HTTPS dispatch.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional, Union


class OculonClientV2:
    """Public client for interacting with Oculon v2 Hotspot & Risk Density APIs."""

    def __init__(self, base_url: str = "https://abhyudaymishr-oculon.hf.space"):
        self.base_url = base_url.rstrip("/")

    def query_hotspots(
        self,
        dataset: str = "missing_persons",
        month: Optional[str] = None,
        query: Optional[str] = None,
        top_k: Union[int, str] = "all",
        district: Optional[str] = None,
        include_continuous_density: bool = True
    ) -> Dict[str, Any]:
        """
        Query forecasted hotspots with continuous Lebesgue density and per-capita risk.
        """
        params = {
            "dataset": dataset,
            "top_k": str(top_k),
            "include_density": "true" if include_continuous_density else "false"
        }
        if month:
            params["month"] = month
        if query:
            params["query"] = query
        if district:
            params["district"] = district

        qs = urllib.parse.urlencode(params)
        url = f"{self.base_url}/api/v2/hotspots?{qs}"
        req = urllib.request.Request(url, headers={"User-Agent": "OculonClientV2/2.0.0"})

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception:
            # Fallback to v1 endpoint if v2 is temporarily offline during deployment
            url_v1 = f"{self.base_url}/api/hotspots?{qs}"
            req_v1 = urllib.request.Request(url_v1, headers={"User-Agent": "OculonClientV2-Fallback/2.0.0"})
            with urllib.request.urlopen(req_v1, timeout=10) as resp_v1:
                return json.loads(resp_v1.read().decode("utf-8"))

    def get_risk_density_field(self, dataset: str = "missing_persons", month: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve the continuous Lebesgue risk density field f(s) = p(u) / a_u
        derived from exact boundary clipping and population exposure offsets.
        """
        params = {"dataset": dataset}
        if month:
            params["month"] = month
        qs = urllib.parse.urlencode(params)
        url = f"{self.base_url}/api/v2/risk-density?{qs}"
        req = urllib.request.Request(url, headers={"User-Agent": "OculonClientV2/2.0.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_evaluation_metrics(self) -> Dict[str, Any]:
        """
        Retrieve both discrete baseline benchmarks and continuous Lebesgue differential metrics.
        """
        url = f"{self.base_url}/api/v2/metrics"
        req = urllib.request.Request(url, headers={"User-Agent": "OculonClientV2/2.0.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_release_manifest(self) -> Dict[str, Any]:
        """
        Retrieve public release manifest detailing decoupled component versions.
        """
        url = f"{self.base_url}/api/v2/manifest"
        req = urllib.request.Request(url, headers={"User-Agent": "OculonClientV2/2.0.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
