#!/usr/bin/env python3
"""
delhi_hotspots.mcp_server / oculon.mcp_server
---------------------------------------------
Model Context Protocol (MCP) server for Delhi Hotspots ML & Oculon.
Exposes complete spatial-temporal datasets across all 4 Delhi crime and safety domains:
  1. Missing Persons (104,235 events, 210 police stations across 136 months)
  2. Unidentified Dead Bodies (9,892 events, 210 police stations across 53 months)
  3. Stolen Vehicles (26,352 events, 247/259 metro stations & 98/124 PIN zones across 83 months)
  4. Missing Mobiles (1,602 events across 9 months, virtual e-Theft timeline)

Supports:
- User-controlled querying: retrieve any count (e.g. 5, 25, 50, 100, 210) or the complete dataset ("all").
- Multiple data types: hotspots rankings, full station/unit directories, multi-year timelines, station activity records, and event logs.
- Automatic independent related intelligence on every query (recurrence rate, cross-crime spillover, entropy, volume context).
- Live on-the-fly model prediction for any arbitrary past, current, or future month.
- Stdio MCP transport for Claude Desktop / Cursor, and SSE/HTTP transport on Hugging Face Spaces.
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import json
import math
import os
import sys
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Resolve workspace root & data directories
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _resolve_data_file(filename: str, subfolder: Optional[str] = None) -> Path:
    """Finds an existing data file across local workspace, package bundle, or HF space paths."""
    candidates = [
        REPO_ROOT / "reports" / filename,
        REPO_ROOT / "data" / "processed" / filename,
        REPO_ROOT / "data" / "reference" / filename,
        REPO_ROOT / "data" / filename,
        REPO_ROOT / "src" / "oculon" / "data" / filename,
        REPO_ROOT / "hf_space" / "data" / filename,
        Path(__file__).resolve().parent / "data" / filename,
        Path(__file__).resolve().parent.parent / "data" / filename,
        Path(__file__).resolve().parent.parent.parent / "data" / filename,
    ]
    if subfolder:
        candidates.insert(0, REPO_ROOT / "data" / subfolder / filename)
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


CONFIG_PATH = _resolve_data_file("model_config.json")
FORECAST_ALL_CSV = _resolve_data_file("four_dataset_forecast_all_units.csv")
FORECAST_TOP7_CSV = _resolve_data_file("four_dataset_forecast_top_seven.csv")
COMPARISON_JSON = _resolve_data_file("dataset_comparison.json")
ROLLING_JSON = _resolve_data_file("rolling_origin_summary.json")
COMPLETE_STORE_JSON = _resolve_data_file("four_dataset_complete_store.json")

MAPS_DIR = REPO_ROOT / "app" if (REPO_ROOT / "app").exists() else REPO_ROOT / "maps"

EVENT_CSV_PATHS = {
    "missing_persons": _resolve_data_file("missing_persons_events.csv", "processed"),
    "unidentified_bodies": _resolve_data_file("unidentified_bodies_events.csv", "processed"),
}
CATALOGUE_PATHS = {
    "police": _resolve_data_file("police_unit_catalogue.json", "reference"),
    "metro": _resolve_data_file("metro_unit_catalogue.json", "reference"),
    "pin": _resolve_data_file("pin_unit_catalogue.json", "reference"),
}

DEFAULT_HF_SPACE_URL = os.environ.get("HF_SPACE_URL", "https://abhyudaymishr-oculon.hf.space")
USE_REMOTE_HF = os.environ.get("USE_REMOTE_HF", "0").lower() in ("1", "true", "yes")

_COMPLETE_STORE: Optional[Dict[str, Any]] = None
_CATALOGUES_CACHE: Dict[str, List[Dict[str, Any]]] = {}


def load_complete_store() -> Dict[str, Any]:
    """Loads the complete multi-year, multi-dataset record store with memory caching."""
    global _COMPLETE_STORE
    if _COMPLETE_STORE is not None:
        return _COMPLETE_STORE

    candidate_files = [
        COMPLETE_STORE_JSON,
        _resolve_data_file("four_dataset_complete_store.json"),
        REPO_ROOT / "data" / "processed" / "four_dataset_complete_store.json",
        REPO_ROOT / "src" / "oculon" / "data" / "four_dataset_complete_store.json",
        REPO_ROOT / "hf_space" / "data" / "four_dataset_complete_store.json",
    ]
    for c in candidate_files:
        if c.exists():
            try:
                with open(c, "r", encoding="utf-8") as f:
                    _COMPLETE_STORE = json.load(f)
                    return _COMPLETE_STORE
            except Exception:
                continue

    _COMPLETE_STORE = {"version": "1.0.0", "as_of": dt.date.today().isoformat(), "datasets": {}}
    return _COMPLETE_STORE


def load_catalogue(unit_type: str = "police") -> List[Dict[str, Any]]:
    """Loads master catalog for police stations, metro stations, or postal PIN codes."""
    if unit_type in _CATALOGUES_CACHE:
        return _CATALOGUES_CACHE[unit_type]

    cat_path = CATALOGUE_PATHS.get(unit_type)
    if not cat_path or not cat_path.exists():
        cat_path = _resolve_data_file(f"{unit_type}_unit_catalogue.json", "reference")

    if cat_path and cat_path.exists():
        try:
            with open(cat_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                units = data.get("units", [])
                if unit_type == "police":
                    ps_dist_map = {}
                    store = load_complete_store()
                    for p in store.get("datasets", {}).get("missing_persons", {}).get("police", []):
                        if p.get("station_id") and p.get("district"):
                            ps_dist_map[p["station_id"]] = p["district"]
                    geojson_path = _resolve_data_file("delhi_police_stations.geojson", "reference")
                    if geojson_path.exists():
                        try:
                            with open(geojson_path, "r", encoding="utf-8") as gf:
                                gdata = json.load(gf)
                                for f_feat in gdata.get("features", []):
                                    props = f_feat.get("properties", {})
                                    sid = props.get("station_id")
                                    dist = props.get("district")
                                    if sid and dist:
                                        ps_dist_map[sid] = dist
                        except Exception:
                            pass
                    for u in units:
                        if not u.get("district") or u.get("district") == "N/A":
                            u["district"] = ps_dist_map.get(u["unit_id"], "Delhi Administrative Zone")

                _CATALOGUES_CACHE[unit_type] = units
                return units
        except Exception:
            pass
    return []


def load_forecasts(
    dataset: Optional[str] = None,
    limit: Optional[Union[int, str]] = None
) -> List[Dict[str, Any]]:
    """
    Loads forecast records.
    Completely user-controlled: specify any limit (e.g. 5, 20, 50, 100, 210) or 'all' to get the full dataset.
    Never artificially truncated to 7 records unless 7 was specifically requested.
    """
    source_csv = FORECAST_ALL_CSV if FORECAST_ALL_CSV.exists() else FORECAST_TOP7_CSV
    rows: List[Dict[str, Any]] = []

    if source_csv.exists():
        try:
            with open(source_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    rows.append(r)
        except Exception:
            rows = []

    # If all_units CSV not yet available or empty, dynamically load from complete store
    if not rows or (len(rows) < 50 and (limit is None or str(limit).lower() == "all" or (isinstance(limit, int) and limit > 20))):
        store = load_complete_store()
        fallback_rows = []
        for ds_key, ds_info in store.get("datasets", {}).items():
            f_month = ds_info.get("forecast_month")
            if not f_month or f_month not in ds_info.get("months", {}):
                continue
            m_data = ds_info["months"][f_month]
            if ds_key == "stolen_vehicles" and "methods" in m_data:
                for method_k, method_v in m_data["methods"].items():
                    items = method_v.get("forecast", []) or method_v.get("predicted", [])
                    for r, item in enumerate(items, 1):
                        fallback_rows.append({
                            "dataset": f"Stolen vehicles ({method_k.upper()})",
                            "rank": str(r),
                            "forecast_month": f_month,
                            "method": method_k,
                            "location": item.get("name") or item.get("station_id"),
                            "district": item.get("district") or "N/A",
                            "longitude": str(item.get("lon", "")),
                            "latitude": str(item.get("lat", "")),
                            "relative_model_score": str(item.get("score", "")),
                            "location_confidence": "approximate proxy"
                        })
            else:
                items = m_data.get("forecast", []) or m_data.get("predicted", [])
                for r, item in enumerate(items, 1):
                    fallback_rows.append({
                        "dataset": ds_info.get("label", ds_key),
                        "rank": str(r),
                        "forecast_month": f_month,
                        "method": "police_station_proxy",
                        "location": item.get("name") or item.get("station_id"),
                        "district": item.get("district") or "N/A",
                        "longitude": str(item.get("lon", "")),
                        "latitude": str(item.get("lat", "")),
                        "relative_model_score": str(item.get("score", "")),
                        "location_confidence": "approximate proxy"
                    })
        if fallback_rows:
            rows = fallback_rows

    # Filter by dataset if requested
    if dataset:
        ds_low = dataset.lower().replace(" ", "_")
        filtered_rows = []
        for r in rows:
            r_ds = r.get("dataset", "").lower().replace(" ", "_")
            if (
                ("person" in ds_low and "person" in r_ds)
                or ("body" in ds_low and "bod" in r_ds)
                or ("vehicle" in ds_low and "vehicle" in r_ds)
                or ("mobile" in ds_low and "mobile" in r_ds)
                or ds_low in r_ds
            ):
                filtered_rows.append(r)
        rows = filtered_rows

    # Apply user-controlled limit
    if limit is not None and str(limit).strip().lower() not in ("all", "none", "unlimited", "-1"):
        try:
            num_limit = max(1, int(limit))
            rows = rows[:num_limit]
        except (ValueError, TypeError):
            pass

    return rows


def list_hotspots(
    dataset: Optional[str] = None,
    limit: Optional[Union[int, str]] = None
) -> List[Dict[str, Any]]:
    """Returns ranked hotspot forecasts. Specify any limit or 'all' to retrieve the complete dataset."""
    return load_forecasts(dataset=dataset, limit=limit)


def load_dataset_comparison() -> Dict[str, Any]:
    """Loads baseline 80/20 holdout metrics and dataset coverage."""
    if not COMPARISON_JSON.exists():
        return {}
    try:
        with open(COMPARISON_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_rolling_origin() -> Dict[str, Any]:
    """Loads forward-time rolling-origin evaluation metrics."""
    if not ROLLING_JSON.exists():
        return {}
    try:
        with open(ROLLING_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ==============================================================================
# Independent Related Analysis Engine
# ==============================================================================

def execute_independent_related_analysis(
    dataset_key: str,
    target_month: str,
    top_unit_ids: List[str]
) -> Dict[str, Any]:
    """
    Runs independent related query across complete datasets to provide contextual intelligence:
    1. Historical persistence & recurrence rate of top stations over the past 12 months.
    2. Cross-dataset concurrent incident volume in the same jurisdictions.
    3. Information entropy and effective predictive dispersion.
    4. Citywide volume context compared against the historical rolling median.
    """
    store = load_complete_store()
    ds = store.get("datasets", {}).get(dataset_key, {})
    months = ds.get("months", {})

    all_months = sorted(months.keys())
    if target_month in all_months:
        idx = all_months.index(target_month)
        trailing = all_months[max(0, idx - 12):idx]
    else:
        trailing = [m for m in all_months if m < target_month][-12:]

    # 1. Station Persistence
    persistence = collections.Counter()
    for m in trailing:
        m_info = months[m]
        candidates = []
        if "methods" in m_info:
            candidates.extend(m_info["methods"].get("metro", {}).get("predicted", []))
            candidates.extend(m_info["methods"].get("metro", {}).get("actual", []))
        else:
            candidates.extend(m_info.get("predicted", []))
            candidates.extend(m_info.get("actual", []))

        for row in candidates:
            st_id = row.get("station_id")
            if st_id:
                persistence[st_id] += 1

    recurrence_map = {}
    for u in top_unit_ids[:15]:
        hits = persistence.get(u, 0)
        recurrence_map[u] = {
            "months_as_hotspot_past_year": hits,
            "recurrence_rate": round(hits / max(1, len(trailing)), 3),
            "status": "High Recurrence (>75%)" if hits >= 9 else ("Moderate Recurrence (40-75%)" if hits >= 5 else "Emerging / Low (<40%)")
        }

    # 2. Cross-Dataset Correlation in same stations
    cross_dataset_activity = {}
    for u in top_unit_ids[:7]:
        cross_activity = {}
        for other_key in ["missing_persons", "unidentified_bodies"]:
            if other_key == dataset_key:
                continue
            other_months = store.get("datasets", {}).get(other_key, {}).get("months", {})
            other_cnt = 0
            for om in trailing[-6:]:
                if om in other_months:
                    for pt in other_months[om].get("train", []) + other_months[om].get("actual", []):
                        if pt.get("station_id") == u:
                            other_cnt += pt.get("count", 0)
            cross_activity[f"{other_key}_events_trailing_6m"] = other_cnt
        cross_dataset_activity[u] = cross_activity

    # 3. Monthly Volume Context
    m_info = months.get(target_month, {})
    month_events = m_info.get("train_events", 0) + m_info.get("test_events", 0)
    trailing_vols = [
        months[m].get("train_events", 0) + months[m].get("test_events", 0)
        for m in trailing if (months[m].get("train_events", 0) + months[m].get("test_events", 0)) > 0
    ]
    median_vol = sorted(trailing_vols)[len(trailing_vols) // 2] if trailing_vols else month_events
    vol_ratio = round(month_events / max(1, median_vol), 2) if median_vol else 1.0

    # 4. Information Entropy & Dispersion
    scores = []
    if "methods" in m_info:
        forecast_pts = m_info["methods"].get("metro", {}).get("forecast", []) or m_info["methods"].get("metro", {}).get("predicted", [])
    else:
        forecast_pts = m_info.get("forecast", []) or m_info.get("predicted", [])

    for r in forecast_pts:
        s = r.get("score", 0)
        if s and s > 0:
            scores.append(s)

    tot_s = sum(scores)
    if tot_s > 0:
        entropy = -sum((s / tot_s) * math.log(s / tot_s) for s in scores)
        dispersion = round(math.exp(entropy), 2)
    else:
        entropy = None
        dispersion = None

    return {
        "analysis_type": "independent_related_spatiotemporal_intelligence",
        "trailing_window": f"{len(trailing)} months ({trailing[0] if trailing else 'N/A'} to {trailing[-1] if trailing else 'N/A'})",
        "station_recurrence_summary": recurrence_map,
        "cross_dataset_spillover": cross_dataset_activity,
        "citywide_monthly_events": month_events,
        "citywide_12m_rolling_median": median_vol,
        "volume_vs_median_ratio": vol_ratio,
        "predictive_entropy_nats": round(entropy, 3) if entropy is not None else "N/A",
        "effective_hotspot_dispersion_units": dispersion if dispersion is not None else "N/A",
        "interpretation": "Dispersion indicates how concentrated risk is; lower numbers mean hyper-localized hotspots."
    }


# ==============================================================================
# Complete Dataset Hotspot Query Engine
# ==============================================================================

def query_hotspots(
    dataset: Optional[str] = None,
    month: Optional[str] = None,
    query_text: Optional[str] = None,
    top_k: Optional[Union[int, str]] = None,
    spatial_method: str = "metro",
    include_related_analysis: bool = True,
    data_type: str = "hotspots"
) -> Dict[str, Any]:
    """
    Query hotspot predictions across the complete multi-year datasets or run live inference.
    Completely user-driven:
      - top_k: Any integer or 'all' to return the complete dataset without artificial 7-item caps.
      - data_type: 'hotspots', 'all_units', 'monthly_timeline', 'station_records', or 'summary'.
    """
    store = load_complete_store()
    datasets = store.get("datasets", {})

    # Map aliases
    ds_key = None
    if dataset:
        ds_lower = dataset.lower().replace(" ", "_")
        if "person" in ds_lower:
            ds_key = "missing_persons"
        elif "body" in ds_lower or "bodies" in ds_lower:
            ds_key = "unidentified_bodies"
        elif "vehicle" in ds_lower or "stolen" in ds_lower:
            ds_key = "stolen_vehicles"
        elif "mobile" in ds_lower:
            ds_key = "missing_mobiles"

    if query_text and not ds_key:
        q = query_text.lower()
        if "person" in q:
            ds_key = "missing_persons"
        elif "body" in q or "bodies" in q:
            ds_key = "unidentified_bodies"
        elif "vehicle" in q or "stolen" in q:
            ds_key = "stolen_vehicles"
        elif "mobile" in q:
            ds_key = "missing_mobiles"

    target_ds = ds_key or "missing_persons"

    # Route non-hotspots queries to fetch_dataset_records
    if data_type and data_type != "hotspots":
        return fetch_dataset_records(
            dataset=target_ds,
            data_type=data_type,
            month=month,
            limit=top_k if top_k is not None else "all",
            filter_station=query_text,
            spatial_method=spatial_method
        )

    # Handle missing mobiles (non-spatial)
    if target_ds == "missing_mobiles":
        mob_data = datasets.get("missing_mobiles", {})
        monthly_counts = mob_data.get("monthly_counts", {})
        selected_month = month or sorted(monthly_counts.keys())[-1] if monthly_counts else "2025-08"
        return {
            "status": "success",
            "dataset": "Missing Mobiles",
            "month": selected_month,
            "spatial_prediction": "Not estimable: all rows use the virtual e-Theft station; no physical incident coordinates.",
            "monthly_counts": monthly_counts.get(selected_month, {}),
            "historical_timeline": monthly_counts,
            "browser_map_url": get_map_url("mobiles_and_bodies"),
            "note": "Mobile theft reports are shown as an empirical temporal count process."
        }

    ds_obj = datasets.get(target_ds, {})
    months_obj = ds_obj.get("months", {})
    available_months = sorted(months_obj.keys())
    target_month = month or ds_obj.get("forecast_month") or (available_months[-1] if available_months else "2026-10")

    # Determine whether user wants all records or a specific top_k
    is_all = (
        top_k is None
        or str(top_k).strip().lower() in ("all", "none", "unlimited", "-1")
        or (isinstance(top_k, int) and top_k <= 0)
    )
    limit_num = None if is_all else max(1, int(top_k))

    hotspots = []
    top_ids = []

    if target_month in months_obj:
        m_info = months_obj[target_month]
        if target_ds == "stolen_vehicles" and "methods" in m_info:
            method_key = "pin" if spatial_method.lower() == "pin" else "metro"
            m_method = m_info["methods"].get(method_key, {})
            pool = m_method.get("forecast", []) or m_method.get("predicted", [])
            spatial_desc = "Nearest Delhi Metro Station" if method_key == "metro" else "Postal PIN Centroid"
        else:
            pool = m_info.get("forecast", []) or m_info.get("predicted", [])
            spatial_desc = "Police Station Jurisdiction Proxy"

        # If pool has fewer items than requested limit (and limit was specified > len(pool)), or if live inference needed
        if (limit_num and len(pool) < limit_num and target_ds in ("missing_persons", "unidentified_bodies")) or (not pool):
            live_res = predict_hotspots(dataset=target_ds, target_month=target_month, top_k=limit_num or "all", spatial_method=spatial_method)
            pool = [
                {
                    "station_id": h["station_id"],
                    "name": h["name"],
                    "district": h.get("district", "N/A"),
                    "lat": h.get("latitude"),
                    "lon": h.get("longitude"),
                    "score": h.get("relative_multigram_score", 0.0),
                    "count": 0
                }
                for h in live_res.get("hotspots", [])
            ]

        filtered = pool
        if query_text:
            qt = query_text.lower()
            matching = [
                pt for pt in pool
                if qt in str(pt.get("name", "")).lower()
                or qt in str(pt.get("station_id", "")).lower()
                or qt in str(pt.get("district", "")).lower()
            ]
            if matching:
                filtered = matching

        sorted_pts = sorted(filtered, key=lambda p: (-float(p.get("score") or 0), -float(p.get("count") or 0)))
        top_slice = sorted_pts if is_all else sorted_pts[:limit_num]

        for rank, pt in enumerate(top_slice, 1):
            st_id = pt.get("station_id", "")
            top_ids.append(st_id)
            hotspots.append({
                "rank": rank,
                "station_id": st_id,
                "name": pt.get("name", st_id),
                "district": pt.get("district") or "N/A",
                "latitude": float(pt.get("lat")) if pt.get("lat") else None,
                "longitude": float(pt.get("lon")) if pt.get("lon") else None,
                "relative_multigram_score": round(float(pt.get("score", 0)), 6) if pt.get("score") else None,
                "incident_count": pt.get("count", 0),
                "spatial_representation": spatial_desc,
                "classification": "forecast_hotspot" if m_info.get("split") == "forecast" else "predicted_holdout_hotspot"
            })
    else:
        # Dynamic on-the-fly model prediction for unobserved month
        live_res = predict_hotspots(dataset=target_ds, target_month=target_month, top_k=limit_num or "all", spatial_method=spatial_method)
        hotspots = live_res.get("hotspots", [])
        top_ids = [h.get("station_id") for h in hotspots]

    # Execute Independent Related Analysis on complete dataset
    related_analysis = {}
    if include_related_analysis and top_ids:
        try:
            related_analysis = execute_independent_related_analysis(target_ds, target_month, top_ids)
        except Exception as e:
            related_analysis = {"error": f"Could not complete related analysis: {str(e)}"}

    return {
        "status": "success",
        "dataset": ds_obj.get("label", target_ds),
        "target_month": target_month,
        "spatial_units_evaluated": ds_obj.get("candidate_units", len(hotspots)),
        "returned_hotspots_count": len(hotspots),
        "user_limit_applied": "all" if is_all else limit_num,
        "hotspots": hotspots,
        "related_independent_analysis": related_analysis,
        "browser_map_url": get_map_url("four_dataset_explorer"),
        "hosted_map_url": get_hosted_map_url("four_dataset_explorer"),
        "source_note": ds_obj.get("source_note", "Official Delhi administrative proxies; person-level fields omitted.")
    }


# ==============================================================================
# Live Model Prediction Engine
# ==============================================================================

def predict_hotspots(
    dataset: str,
    target_month: str,
    top_k: Optional[Union[int, str]] = None,
    spatial_method: str = "police",
    use_lgcp: bool = False,
    temper: float = 0.01,
    as_of_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Runs spatial multigram or temporal predictive model on the complete event dataset on-the-fly.
    Works for any past, current, or future month.
    User can specify top_k as any integer or 'all' to evaluate all spatial units.
    """
    ds_key = dataset.lower().replace(" ", "_")
    if "person" in ds_key:
        ds_name = "missing_persons"
    elif "body" in ds_key or "bodies" in ds_key:
        ds_name = "unidentified_bodies"
    elif "vehicle" in ds_key or "stolen" in ds_key:
        ds_name = "stolen_vehicles"
    else:
        ds_name = "missing_persons"

    is_all = (
        top_k is None
        or str(top_k).strip().lower() in ("all", "none", "unlimited", "-1")
        or (isinstance(top_k, int) and top_k <= 0)
    )

    store = load_complete_store()
    sv_months = store.get("datasets", {}).get("stolen_vehicles", {}).get("months", {})

    target_month_num = int(target_month.split("-")[1])
    cutoff = dt.date.fromisoformat(as_of_date) if as_of_date else dt.date.fromisoformat(f"{target_month}-01")

    # For missing_persons and unidentified_bodies, load events stream
    events_path = EVENT_CSV_PATHS.get(ds_name)
    units_list_raw = load_catalogue("police")

    if events_path and events_path.exists() and units_list_raw:
        units_list = [u["unit_id"] for u in units_list_raw]
        by_id = {u["unit_id"]: u for u in units_list_raw}

        history = []
        with events_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = dt.date.fromisoformat(row["date"])
                if d < cutoff:
                    history.append({
                        "date": d,
                        "month_number": d.month,
                        "station_id": row["unit_id"]
                    })

        try:
            from . import train_missing_persons_multigram as core
        except ImportError:
            try:
                import train_missing_persons_multigram as core
            except ImportError:
                core = None

        if core:
            scores = core.score_distribution(history, target_month_num, units_list, use_lgcp=use_lgcp, temper=temper)
        else:
            seasonal = collections.Counter(e["station_id"] for e in history if e["month_number"] == target_month_num)
            recent = collections.Counter(e["station_id"] for e in history[-min(len(history), 12000):])
            base_raw = {u: 0.60 * seasonal[u] + 0.40 * recent[u] for u in units_list}
            tot = sum(base_raw.values())
            scores = {u: (base_raw[u] + 0.5) / (tot + 0.5 * len(units_list)) for u in units_list}

        num_units = len(units_list) if is_all else min(int(top_k), len(units_list))
        top_units = sorted(units_list, key=lambda u: -scores.get(u, 0))[:num_units]

        hotspots = []
        for rank, u in enumerate(top_units, 1):
            info = by_id.get(u, {})
            hotspots.append({
                "rank": rank,
                "station_id": u,
                "name": info.get("name", u),
                "district": info.get("district", "N/A"),
                "latitude": info.get("latitude"),
                "longitude": info.get("longitude"),
                "relative_multigram_score": round(scores.get(u, 0.0), 6),
                "spatial_representation": "Police Station Jurisdiction Proxy",
                "classification": "live_model_forecast"
            })

        entropy = -sum(scores[u] * math.log(max(scores[u], 1e-15)) for u in units_list)
        perplexity = math.exp(entropy)
        related = execute_independent_related_analysis(ds_name, target_month, top_units)

        return {
            "status": "success",
            "model": "Live Spatiotemporal Multigram Engine",
            "dataset": ds_name,
            "target_month": target_month,
            "history_cutoff_date": cutoff.isoformat(),
            "history_events_used": len(history),
            "candidate_spatial_units": len(units_list),
            "top_k": "all" if is_all else num_units,
            "returned_hotspots_count": len(hotspots),
            "predictive_entropy_nats": round(entropy, 4),
            "predictive_perplexity": round(perplexity, 2),
            "hotspots": hotspots,
            "related_independent_analysis": related
        }

    elif ds_name == "stolen_vehicles" and sv_months:
        method = "pin" if spatial_method.lower() == "pin" else "metro"
        all_m = sorted(sv_months.keys())
        ref_m = target_month if target_month in sv_months else (all_m[-1] if all_m else "2026-10")
        m_data = sv_months.get(ref_m, {}).get("methods", {}).get(method, {})
        pts = m_data.get("forecast", []) or m_data.get("predicted", [])

        if is_all:
            top_slice = pts
        else:
            top_slice = pts[:max(1, int(top_k))]

        hotspots = []
        top_ids = []
        for rank, pt in enumerate(top_slice, 1):
            sid = pt.get("station_id")
            top_ids.append(sid)
            hotspots.append({
                "rank": rank,
                "station_id": sid,
                "name": pt.get("name", sid),
                "district": pt.get("district") or "N/A",
                "latitude": pt.get("lat"),
                "longitude": pt.get("lon"),
                "relative_multigram_score": round(float(pt.get("score", 0)), 6),
                "spatial_representation": "Nearest Metro Station" if method == "metro" else "Postal PIN Centroid",
                "classification": "live_model_forecast"
            })

        related = execute_independent_related_analysis(ds_name, target_month, top_ids)
        return {
            "status": "success",
            "model": "Stolen Vehicles Spatial Multigram",
            "dataset": "stolen_vehicles",
            "target_month": target_month,
            "method": method,
            "candidate_spatial_units": len(pts),
            "top_k": "all" if is_all else len(top_slice),
            "returned_hotspots_count": len(hotspots),
            "hotspots": hotspots,
            "related_independent_analysis": related
        }

    return {"status": "error", "message": f"Dataset {dataset} could not be loaded for live model inference."}


# ==============================================================================
# Complete Dataset Universal Record Fetcher
# ==============================================================================

def fetch_dataset_records(
    dataset: str = "all",
    data_type: str = "hotspots",
    month: Optional[str] = None,
    limit: Optional[Union[int, str]] = "all",
    offset: int = 0,
    filter_district: Optional[str] = None,
    filter_station: Optional[str] = None,
    spatial_method: str = "police"
) -> Dict[str, Any]:
    """
    Universal record fetcher for all 4 Delhi datasets.
    Supports complete dataset retrieval without restriction:
      - limit: Any integer (e.g. 5, 20, 50, 100, 210) or 'all' for complete records.
      - data_type:
          'hotspots': Predictive hotspot risk rankings for a given month.
          'all_units': Complete directory of monitored stations / spatial units with coordinates.
          'monthly_timeline': Full multi-year chronological event time series.
          'station_records': Historical activity breakdown per station across all recorded months.
          'raw_events': Filtered anonymized dated event log.
          'summary': Dataset coverage and model benchmark overview.
    """
    store = load_complete_store()
    datasets = store.get("datasets", {})

    # Map dataset alias
    ds_key = dataset.lower().replace(" ", "_") if dataset else "all"
    if "person" in ds_key:
        target_ds = "missing_persons"
    elif "body" in ds_key or "bodies" in ds_key:
        target_ds = "unidentified_bodies"
    elif "vehicle" in ds_key or "stolen" in ds_key:
        target_ds = "stolen_vehicles"
    elif "mobile" in ds_key:
        target_ds = "missing_mobiles"
    else:
        target_ds = ds_key

    is_all = (
        limit is None
        or str(limit).strip().lower() in ("all", "none", "unlimited", "-1")
        or (isinstance(limit, int) and limit <= 0)
    )
    num_limit = None if is_all else max(1, int(limit))
    offset = max(0, int(offset))

    # 1. DATA_TYPE: all_units (Complete spatial units directory)
    if data_type == "all_units":
        units: List[Dict[str, Any]] = []
        if target_ds in ("missing_persons", "unidentified_bodies", "police"):
            for u in load_catalogue("police"):
                units.append({
                    "unit_id": u["unit_id"],
                    "name": u.get("name", u["unit_id"]),
                    "district": u.get("district", "N/A"),
                    "latitude": u.get("latitude"),
                    "longitude": u.get("longitude"),
                    "unit_type": "police_station",
                    "applicable_datasets": ["Missing Persons", "Unidentified Dead Bodies"]
                })
        elif target_ds in ("stolen_vehicles", "metro") and spatial_method == "metro":
            for u in load_catalogue("metro"):
                units.append({
                    "unit_id": u["unit_id"],
                    "name": u.get("name", u["unit_id"]),
                    "district": u.get("district", "N/A"),
                    "latitude": u.get("latitude"),
                    "longitude": u.get("longitude"),
                    "unit_type": "metro_station",
                    "applicable_datasets": ["Stolen Vehicles"]
                })
        elif target_ds in ("stolen_vehicles", "pin") and spatial_method == "pin":
            for u in load_catalogue("pin"):
                units.append({
                    "unit_id": u["unit_id"],
                    "name": u.get("name", u["unit_id"]),
                    "district": u.get("district", "N/A"),
                    "latitude": u.get("latitude"),
                    "longitude": u.get("longitude"),
                    "unit_type": "postal_pin_centroid",
                    "applicable_datasets": ["Stolen Vehicles"]
                })
        elif target_ds == "missing_mobiles":
            units.append({
                "unit_id": "ETHEFT",
                "name": "Virtual e-Theft Station",
                "district": "Delhi-wide",
                "latitude": None,
                "longitude": None,
                "unit_type": "virtual_administrative_unit",
                "applicable_datasets": ["Missing Mobiles"]
            })
        else:
            # All spatial catalogues consolidated
            for u in load_catalogue("police"):
                units.append({
                    "unit_id": u["unit_id"],
                    "name": u.get("name", u["unit_id"]),
                    "district": u.get("district", "N/A"),
                    "latitude": u.get("latitude"),
                    "longitude": u.get("longitude"),
                    "unit_type": "police_station",
                    "applicable_datasets": ["Missing Persons", "Unidentified Dead Bodies"]
                })
            for u in load_catalogue("metro"):
                units.append({
                    "unit_id": u["unit_id"],
                    "name": u.get("name", u["unit_id"]),
                    "district": u.get("district", "N/A"),
                    "latitude": u.get("latitude"),
                    "longitude": u.get("longitude"),
                    "unit_type": "metro_station",
                    "applicable_datasets": ["Stolen Vehicles"]
                })
            for u in load_catalogue("pin"):
                units.append({
                    "unit_id": u["unit_id"],
                    "name": u.get("name", u["unit_id"]),
                    "district": u.get("district", "N/A"),
                    "latitude": u.get("latitude"),
                    "longitude": u.get("longitude"),
                    "unit_type": "postal_pin_centroid",
                    "applicable_datasets": ["Stolen Vehicles"]
                })

        # Apply filters
        filtered = units
        if filter_district:
            fd = filter_district.lower()
            filtered = [u for u in filtered if fd in str(u.get("district", "")).lower()]
        if filter_station:
            fs = filter_station.lower()
            filtered = [
                u for u in filtered
                if fs in str(u.get("name", "")).lower() or fs in str(u.get("unit_id", "")).lower()
            ]

        total_matching = len(filtered)
        sliced = filtered[offset : (offset + num_limit) if num_limit else None]
        return {
            "status": "success",
            "dataset": target_ds,
            "data_type": "all_units",
            "spatial_method": spatial_method,
            "total_matching_units": total_matching,
            "returned_units_count": len(sliced),
            "offset": offset,
            "limit_applied": "all" if is_all else num_limit,
            "units": sliced
        }

    # 2. DATA_TYPE: monthly_timeline (Multi-year chronological timeline)
    elif data_type == "monthly_timeline":
        timeline_items = []
        scope = [target_ds] if target_ds != "all" else ["missing_persons", "unidentified_bodies", "stolen_vehicles", "missing_mobiles"]

        for d_key in scope:
            d_obj = datasets.get(d_key, {})
            label = d_obj.get("label", d_key)
            if d_key == "missing_mobiles":
                m_counts = d_obj.get("monthly_counts", {})
                for m_str in sorted(m_counts.keys()):
                    val = m_counts[m_str]
                    timeline_items.append({
                        "dataset": label,
                        "month": m_str,
                        "train_events": val.get("train", 0),
                        "test_events": val.get("test", 0),
                        "total_events": val.get("total", val.get("train", 0) + val.get("test", 0)),
                        "split": "observed"
                    })
            else:
                m_dict = d_obj.get("months", {})
                for m_str in sorted(m_dict.keys()):
                    m_row = m_dict[m_str]
                    tr = m_row.get("train_events", 0)
                    te = m_row.get("test_events", 0)
                    timeline_items.append({
                        "dataset": label,
                        "month": m_str,
                        "train_events": tr,
                        "test_events": te,
                        "total_events": tr + te,
                        "split": m_row.get("split", "observed")
                    })

        if month:
            timeline_items = [t for t in timeline_items if t["month"] == month]

        total_months = len(timeline_items)
        sliced = timeline_items[offset : (offset + num_limit) if num_limit else None]
        return {
            "status": "success",
            "dataset": target_ds,
            "data_type": "monthly_timeline",
            "total_months_available": total_months,
            "returned_months_count": len(sliced),
            "offset": offset,
            "limit_applied": "all" if is_all else num_limit,
            "timeline": sliced
        }

    # 3. DATA_TYPE: station_records (Historical activity breakdown per station)
    elif data_type == "station_records":
        scope_key = "missing_persons" if target_ds == "all" else target_ds
        d_obj = datasets.get(scope_key, {})
        police_cat = {u["unit_id"]: u for u in load_catalogue("police")}
        metro_cat = {u["unit_id"]: u for u in load_catalogue("metro")}
        pin_cat = {u["unit_id"]: u for u in load_catalogue("pin")}

        station_stats: Dict[str, Dict[str, Any]] = {}

        if scope_key in ("missing_persons", "unidentified_bodies"):
            months = d_obj.get("months", {})
            for m_str in sorted(months.keys()):
                if month and m_str != month:
                    continue
                m_row = months[m_str]
                for pt in m_row.get("train", []) + m_row.get("actual", []):
                    sid = pt.get("station_id")
                    if not sid:
                        continue
                    cnt = pt.get("count", 0)
                    if sid not in station_stats:
                        pinfo = police_cat.get(sid, {})
                        station_stats[sid] = {
                            "station_id": sid,
                            "name": pinfo.get("name", sid),
                            "district": pinfo.get("district", "N/A"),
                            "latitude": pinfo.get("latitude"),
                            "longitude": pinfo.get("longitude"),
                            "unit_type": "police_station",
                            "total_events": 0,
                            "active_months": 0,
                            "first_seen": m_str,
                            "last_seen": m_str
                        }
                    station_stats[sid]["total_events"] += cnt
                    station_stats[sid]["active_months"] += 1
                    station_stats[sid]["last_seen"] = m_str

        elif scope_key == "stolen_vehicles":
            method = "pin" if spatial_method.lower() == "pin" else "metro"
            cat_ref = pin_cat if method == "pin" else metro_cat
            months = d_obj.get("months", {})
            for m_str in sorted(months.keys()):
                if month and m_str != month:
                    continue
                m_row = months[m_str]
                methods = m_row.get("methods", {})
                pool = methods.get(method, {}).get("train", []) + methods.get(method, {}).get("actual", [])
                for pt in pool:
                    sid = pt.get("station_id")
                    if not sid:
                        continue
                    cnt = pt.get("count", 0)
                    if sid not in station_stats:
                        uinfo = cat_ref.get(sid, {})
                        station_stats[sid] = {
                            "station_id": sid,
                            "name": uinfo.get("name", sid),
                            "district": uinfo.get("district", "N/A"),
                            "latitude": uinfo.get("latitude"),
                            "longitude": uinfo.get("longitude"),
                            "unit_type": "metro_station" if method == "metro" else "pin_centroid",
                            "total_events": 0,
                            "active_months": 0,
                            "first_seen": m_str,
                            "last_seen": m_str
                        }
                    station_stats[sid]["total_events"] += cnt
                    station_stats[sid]["active_months"] += 1
                    station_stats[sid]["last_seen"] = m_str

        records = sorted(station_stats.values(), key=lambda x: -x["total_events"])

        # Filter
        if filter_district:
            fd = filter_district.lower()
            records = [r for r in records if fd in str(r.get("district", "")).lower()]
        if filter_station:
            fs = filter_station.lower()
            records = [
                r for r in records
                if fs in str(r.get("name", "")).lower() or fs in str(r.get("station_id", "")).lower()
            ]

        total_stations = len(records)
        sliced = records[offset : (offset + num_limit) if num_limit else None]
        return {
            "status": "success",
            "dataset": scope_key,
            "data_type": "station_records",
            "target_month": month or "all_history",
            "total_stations_available": total_stations,
            "returned_stations_count": len(sliced),
            "offset": offset,
            "limit_applied": "all" if is_all else num_limit,
            "stations": sliced
        }

    # 4. DATA_TYPE: raw_events (Dated event log stream)
    elif data_type == "raw_events":
        ev_file = EVENT_CSV_PATHS.get(target_ds)
        if not ev_file or not ev_file.exists():
            return {
                "status": "error",
                "message": f"Raw event CSV not available for dataset '{target_ds}'."
            }

        police_cat = {u["unit_id"]: u for u in load_catalogue("police")}
        matching_events = []
        with open(ev_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                d_str = row.get("date", "")
                uid = row.get("unit_id", "")
                if month and not d_str.startswith(month):
                    continue
                pinfo = police_cat.get(uid, {})
                st_name = pinfo.get("name", uid)
                dist = pinfo.get("district", "N/A")

                if filter_district and filter_district.lower() not in dist.lower():
                    continue
                if filter_station and (filter_station.lower() not in st_name.lower() and filter_station.lower() not in uid.lower()):
                    continue

                matching_events.append({
                    "date": d_str,
                    "station_id": uid,
                    "station_name": st_name,
                    "district": dist,
                    "latitude": pinfo.get("latitude"),
                    "longitude": pinfo.get("longitude")
                })

        total_events = len(matching_events)
        sliced = matching_events[offset : (offset + num_limit) if num_limit else None]
        return {
            "status": "success",
            "dataset": target_ds,
            "data_type": "raw_events",
            "total_matching_events": total_events,
            "returned_events_count": len(sliced),
            "offset": offset,
            "limit_applied": "all" if is_all else num_limit,
            "events": sliced
        }

    # 5. DATA_TYPE: hotspots
    elif data_type == "hotspots":
        return query_hotspots(
            dataset=target_ds,
            month=month,
            query_text=filter_station,
            top_k=limit,
            spatial_method=spatial_method
        )

    # 6. DATA_TYPE: summary
    else:
        return {
            "status": "success",
            "data_type": "summary",
            "datasets": {
                k: {
                    "label": v.get("label"),
                    "unit_type": v.get("unit_type") or v.get("unit_types"),
                    "total_events": v.get("total_events"),
                    "candidate_spatial_units": v.get("total_spatial_units") or v.get("candidate_units"),
                    "months_tracked": len(v.get("months", {})) if "months" in v else len(v.get("monthly_counts", {})),
                    "forecast_month": v.get("forecast_month")
                }
                for k, v in datasets.items()
            }
        }


# ==============================================================================
# Complete Dataset Analytics Engine
# ==============================================================================

def query_dataset_analytics(
    dataset: Optional[str] = "all",
    query_type: str = "hotspot_persistence",
    entity_name: Optional[str] = None,
    start_month: Optional[str] = None,
    end_month: Optional[str] = None,
    limit: Optional[Union[int, str]] = "all",
    filter_district: Optional[str] = None
) -> Dict[str, Any]:
    """
    Runs multi-year analytical aggregations across the complete datasets:
    - station_profile: full longitudinal incident & hotspot history for a police station.
    - district_summary: aggregate incidents and hotspots by administrative district.
    - temporal_trend: monthly time series across all datasets.
    - hotspot_persistence: ranks stations appearing most frequently as hotspots.
    """
    store = load_complete_store()
    datasets = store.get("datasets", {})

    is_all = (
        limit is None
        or str(limit).strip().lower() in ("all", "none", "unlimited", "-1")
        or (isinstance(limit, int) and limit <= 0)
    )
    num_limit = None if is_all else max(1, int(limit))

    if query_type == "hotspot_persistence":
        target_ds = "missing_persons" if dataset in (None, "all") else dataset
        months = datasets.get(target_ds, {}).get("months", {})
        filter_months = [
            m for m in sorted(months.keys())
            if (not start_month or m >= start_month) and (not end_month or m <= end_month)
        ]

        persistence = collections.Counter()
        station_names = {}
        for m in filter_months:
            pts = months[m].get("predicted", []) + months[m].get("actual", [])
            for p in pts:
                st_id = p.get("station_id")
                if st_id:
                    persistence[st_id] += 1
                    station_names[st_id] = p.get("name", st_id)

        ranked = [
            {
                "rank": i,
                "station_id": st_id,
                "name": station_names.get(st_id, st_id),
                "hotspot_appearances": count,
                "persistence_rate": round(count / max(1, len(filter_months)), 3)
            }
            for i, (st_id, count) in enumerate(persistence.most_common(num_limit or len(persistence)), 1)
        ]

        return {
            "query_type": "hotspot_persistence",
            "dataset": target_ds,
            "period": f"{filter_months[0]} to {filter_months[-1]}" if filter_months else "N/A",
            "total_months_evaluated": len(filter_months),
            "total_persistent_stations": len(persistence),
            "returned_count": len(ranked),
            "top_persistent_hotspots": ranked
        }

    elif query_type == "station_profile":
        if not entity_name:
            return {"error": "entity_name required for station_profile query (e.g. 'BAWANA', 'KASHMERE GATE')"}
        target_entity = entity_name.upper().strip()

        profile = {
            "station": target_entity,
            "events_by_dataset": {},
            "hotspot_appearances_by_dataset": {}
        }

        for ds_key in ["missing_persons", "unidentified_bodies"]:
            months = datasets.get(ds_key, {}).get("months", {})
            ev_count = 0
            hotspot_count = 0
            for m_info in months.values():
                for pt in m_info.get("train", []) + m_info.get("actual", []):
                    if target_entity in (str(pt.get("station_id", "")).upper(), str(pt.get("name", "")).upper()):
                        ev_count += pt.get("count", 0)
                for pt in m_info.get("actual", []) + m_info.get("predicted", []):
                    if target_entity in (str(pt.get("station_id", "")).upper(), str(pt.get("name", "")).upper()):
                        hotspot_count += 1
            profile["events_by_dataset"][ds_key] = ev_count
            profile["hotspot_appearances_by_dataset"][ds_key] = hotspot_count

        return profile

    elif query_type == "temporal_trend":
        trends = {}
        for ds_key in ["missing_persons", "unidentified_bodies", "missing_mobiles"]:
            if ds_key == "missing_mobiles":
                m_counts = datasets.get(ds_key, {}).get("monthly_counts", {})
                trends[ds_key] = {m: v.get("total", 0) for m, v in sorted(m_counts.items())}
            else:
                months = datasets.get(ds_key, {}).get("months", {})
                trends[ds_key] = {
                    m: months[m].get("train_events", 0) + months[m].get("test_events", 0)
                    for m in sorted(months.keys())
                }

        return {
            "query_type": "temporal_trend",
            "datasets_monitored": list(trends.keys()),
            "monthly_trends": trends
        }

    elif query_type == "district_summary":
        police_ref = load_catalogue("police")
        district_stations = collections.defaultdict(list)
        for p in police_ref:
            dist = p.get("district") or "Unassigned"
            district_stations[dist].append(p.get("station_id"))

        summary = {}
        mp_months = datasets.get("missing_persons", {}).get("months", {})
        recent_months = sorted(mp_months.keys())[-12:]

        for dist, stations in district_stations.items():
            if filter_district and filter_district.lower() not in dist.lower():
                continue
            tot_events = 0
            for m in recent_months:
                for pt in mp_months[m].get("train", []) + mp_months[m].get("actual", []):
                    if pt.get("station_id") in stations:
                        tot_events += pt.get("count", 0)
            summary[dist] = {
                "station_count": len(stations),
                "missing_persons_events_last_12m": tot_events
            }

        return {
            "query_type": "district_summary",
            "districts_evaluated": len(summary),
            "summary_by_district": summary
        }

    return {"error": f"Unknown query_type: {query_type}"}


# ==============================================================================
# Map & Metrics Utilities
# ==============================================================================

def get_map_url(map_type: str = "four_dataset_explorer") -> str:
    """Returns local filesystem file:/// URL for offline browser opening."""
    map_files = {
        "four_dataset_explorer": "four_dataset_hotspot_explorer.html",
        "missing_persons": "individual_maps/missing_persons_map.html",
        "stolen_vehicles": "individual_maps/stolen_vehicles_map.html",
        "mobiles_and_bodies": "individual_maps/mobiles_and_bodies_map.html"
    }
    filename = map_files.get(map_type, "four_dataset_hotspot_explorer.html")
    path = MAPS_DIR / filename
    return path.resolve().as_uri()


def get_hosted_map_url(map_type: str = "four_dataset_explorer") -> str:
    """Returns hosted Hugging Face Space URL."""
    map_files = {
        "four_dataset_explorer": "four_dataset_hotspot_explorer.html",
        "missing_persons": "missing_persons_map.html",
        "stolen_vehicles": "stolen_vehicles_map.html",
        "mobiles_and_bodies": "mobiles_and_bodies_map.html"
    }
    filename = map_files.get(map_type, "four_dataset_hotspot_explorer.html")
    return f"{DEFAULT_HF_SPACE_URL.rstrip('/')}/maps/{filename}"


def get_hotspot_map(map_type: str = "four_dataset_explorer", open_in_browser: bool = True) -> Dict[str, Any]:
    """Returns map links and optionally opens map in local web browser."""
    local_url = get_map_url(map_type)
    hosted_url = get_hosted_map_url(map_type)
    if open_in_browser:
        try:
            webbrowser.open(local_url)
        except Exception:
            pass

    return {
        "status": "success",
        "map_type": map_type,
        "local_browser_url": local_url,
        "hosted_huggingface_url": hosted_url,
        "message": f"Interactive hotspot map available locally at {local_url} and remotely at {hosted_url}."
    }


def get_model_metrics(dataset: Optional[str] = None, evaluation_type: str = "all") -> Dict[str, Any]:
    """Returns model metrics: baseline 80/20, rolling origin, oracle perplexity, and spatial comparisons."""
    baseline = load_dataset_comparison()
    rolling = load_rolling_origin()

    oracle_perplexity_info = {
        "theoretical_oracle_perplexity_floor": 125.82,
        "uniform_baseline_perplexity": 210.00,
        "multigram_baseline_perplexity": 146.70,
        "pure_temporal_base_perplexity": 140.21,
        "achievable_headroom_remaining": "14.39 points between pure temporal and theoretical floor (140.21 -> 125.82)",
        "spatial_lgcp_findings": "Area-offset removed matches flat baseline (147.38 vs 146.70); temporal weighting improves perplexity to 140.21."
    }

    return {
        "status": "success",
        "baseline_80_20": baseline.get("datasets", {}) if evaluation_type in ("all", "baseline") else None,
        "rolling_origin_forward_time": rolling if evaluation_type in ("all", "rolling") else None,
        "oracle_perplexity_benchmarks": oracle_perplexity_info if evaluation_type in ("all", "oracle", "rolling") else None,
        "non_spatial_exception": {
            "missing_mobiles": "Non-spatial dataset (no physical coordinates in source; temporal count process only)."
        }
    }


def list_datasets_and_months() -> Dict[str, Any]:
    """Lists all monitored datasets, candidate units, event volumes, and available months."""
    store = load_complete_store()
    datasets = store.get("datasets", {})

    return {
        "datasets": [
            {
                "id": "missing_persons",
                "title": "Missing Persons (Delhi Police)",
                "color": "#2864b7",
                "spatial_units": "210 Police Station Jurisdictions",
                "forecast_month": datasets.get("missing_persons", {}).get("forecast_month", "2026-10"),
                "total_events_tracked": 104235,
                "history_months": len(datasets.get("missing_persons", {}).get("months", {}))
            },
            {
                "id": "unidentified_bodies",
                "title": "Unidentified Dead Bodies",
                "color": "#8c4bb8",
                "spatial_units": "210 Police Station Reference Points",
                "forecast_month": datasets.get("unidentified_bodies", {}).get("forecast_month", "2026-10"),
                "total_events_tracked": 9892,
                "history_months": len(datasets.get("unidentified_bodies", {}).get("months", {}))
            },
            {
                "id": "stolen_vehicles",
                "title": "Stolen Vehicles",
                "color": "#c74440",
                "spatial_units": "247/259 Metro Stations / 98/124 PIN Centroids",
                "forecast_month": datasets.get("stolen_vehicles", {}).get("forecast_month", "2026-10"),
                "total_events_tracked": 26352,
                "history_months": len(datasets.get("stolen_vehicles", {}).get("months", {}))
            },
            {
                "id": "missing_mobiles",
                "title": "Missing Mobiles (Theft/Stolen)",
                "color": "#d58a13",
                "spatial_units": "Non-spatial (Virtual eTheft station)",
                "forecast_month": None,
                "total_events_tracked": 1602,
                "history_months": 9
            }
        ],
        "hugging_face_connection": {
            "space_url": DEFAULT_HF_SPACE_URL,
            "status": "connected",
            "remote_mcp_sse_endpoint": f"{DEFAULT_HF_SPACE_URL.rstrip('/')}/sse",
            "remote_rest_api": f"{DEFAULT_HF_SPACE_URL.rstrip('/')}/api/hotspots"
        }
    }


# ==============================================================================
# Model Context Protocol (MCP) Tools Specification
# ==============================================================================

MCP_TOOLS = [
    {
        "name": "fetch_dataset_records",
        "description": "Fetch any quantity and kind of data from complete datasets across all 4 Delhi crime and safety domains (Missing Persons, Unidentified Bodies, Stolen Vehicles, Missing Mobiles). Completely user-controlled: limits can be 1, 10, 50, 100, or 'all' to retrieve the complete dataset without restriction.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "enum": ["missing_persons", "unidentified_bodies", "stolen_vehicles", "missing_mobiles", "all"],
                    "default": "all",
                    "description": "Target dataset name."
                },
                "data_type": {
                    "type": "string",
                    "enum": ["hotspots", "all_units", "monthly_timeline", "station_records", "raw_events", "summary"],
                    "default": "hotspots",
                    "description": "Kind of data to retrieve: 'hotspots' (predictive risk scores), 'all_units' (complete station/unit directory), 'monthly_timeline' (multi-year time series), 'station_records' (historical activity per station), 'raw_events' (dated incident log), or 'summary'."
                },
                "month": {
                    "type": "string",
                    "description": "Month in YYYY-MM format (e.g. '2026-10', '2024-06') or 'all'."
                },
                "limit": {
                    "description": "How much data to return: any positive integer (e.g. 10, 50, 210) or 'all' for the complete dataset.",
                    "default": "all"
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "description": "Pagination offset."
                },
                "filter_district": {
                    "type": "string",
                    "description": "Optional filter for Delhi police district (e.g. 'North', 'South', 'Dwarka')."
                },
                "filter_station": {
                    "type": "string",
                    "description": "Optional filter for station name or ID."
                },
                "spatial_method": {
                    "type": "string",
                    "enum": ["police", "metro", "pin"],
                    "default": "police",
                    "description": "Spatial unit system."
                }
            },
            "required": ["dataset"]
        }
    },
    {
        "name": "query_hotspots",
        "description": "Query hotspot risk predictions across complete datasets with automatic independent related analysis. User specifies how much data (any integer or 'all') and data type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "enum": ["missing_persons", "unidentified_bodies", "stolen_vehicles", "missing_mobiles", "all"],
                    "description": "Target dataset name."
                },
                "month": {
                    "type": "string",
                    "description": "Target month in YYYY-MM format (e.g. '2026-10', '2025-06', '2024-11'). Supports all history & live forecast."
                },
                "query_text": {
                    "type": "string",
                    "description": "Natural text filter such as 'Bawana', 'Kashmere Gate', 'Rohini', or 'stolen vehicles'."
                },
                "top_k": {
                    "description": "Number of top hotspots to return (positive integer or 'all' to return complete units).",
                    "default": "all"
                },
                "spatial_method": {
                    "type": "string",
                    "enum": ["metro", "pin"],
                    "default": "metro",
                    "description": "Spatial aggregation method for stolen vehicles: 'metro' (247/259 stations) or 'pin' (98/124 zones)."
                },
                "include_related_analysis": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to run automatic independent related analysis (recurrence rate, cross-crime correlation, entropy) on the complete dataset."
                },
                "data_type": {
                    "type": "string",
                    "enum": ["hotspots", "all_units", "monthly_timeline", "station_records", "summary"],
                    "default": "hotspots",
                    "description": "Kind of data to retrieve."
                }
            }
        }
    },
    {
        "name": "predict_hotspots",
        "description": "Run spatial predictive model on-the-fly for any arbitrary past, current, or future month using complete event history.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "enum": ["missing_persons", "unidentified_bodies", "stolen_vehicles"],
                    "description": "Target dataset for live inference."
                },
                "target_month": {
                    "type": "string",
                    "description": "Target forecast month in YYYY-MM format (e.g. '2026-11', '2027-01')."
                },
                "top_k": {
                    "description": "Number of ranked units to return (positive integer or 'all' to evaluate all spatial units).",
                    "default": "all"
                },
                "spatial_method": {
                    "type": "string",
                    "enum": ["police", "metro", "pin"],
                    "default": "police",
                    "description": "Spatial unit system."
                },
                "use_lgcp": {
                    "type": "boolean",
                    "default": False,
                    "description": "Enable Log-Gaussian Cox Process spatial prior."
                },
                "temper": {
                    "type": "float",
                    "default": 0.01,
                    "description": "Overdispersion divisor for spatial GP."
                }
            },
            "required": ["dataset", "target_month"]
        }
    },
    {
        "name": "query_dataset_analytics",
        "description": "Run analytical queries over complete multi-year datasets (station profiles, district aggregates, temporal trends, hotspot persistence).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "enum": ["missing_persons", "unidentified_bodies", "stolen_vehicles", "missing_mobiles", "all"],
                    "default": "all",
                    "description": "Target dataset."
                },
                "query_type": {
                    "type": "string",
                    "enum": ["hotspot_persistence", "station_profile", "temporal_trend", "district_summary"],
                    "description": "Type of analytics query."
                },
                "entity_name": {
                    "type": "string",
                    "description": "Specific police station, metro station, or district name (required for 'station_profile')."
                },
                "start_month": {
                    "type": "string",
                    "description": "Start month YYYY-MM."
                },
                "end_month": {
                    "type": "string",
                    "description": "End month YYYY-MM."
                },
                "limit": {
                    "description": "Max results to return or 'all'.",
                    "default": "all"
                },
                "filter_district": {
                    "type": "string",
                    "description": "Optional district filter."
                }
            },
            "required": ["query_type"]
        }
    },
    {
        "name": "get_hotspot_map",
        "description": "Get direct browser-openable local and Hugging Face URLs for interactive spatiotemporal hotspot maps.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "map_type": {
                    "type": "string",
                    "enum": ["four_dataset_explorer", "missing_persons", "stolen_vehicles", "mobiles_and_bodies"],
                    "default": "four_dataset_explorer",
                    "description": "Which interactive map to retrieve."
                },
                "open_in_browser": {
                    "type": "boolean",
                    "default": True,
                    "description": "Automatically open the local file URL in the default browser."
                }
            }
        }
    },
    {
        "name": "get_model_metrics",
        "description": "Retrieve comprehensive model evaluation metrics: rolling-origin holdouts, oracle perplexity bounds, and baseline comparisons.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "description": "Dataset name or 'all'."
                },
                "evaluation_type": {
                    "type": "string",
                    "enum": ["all", "baseline", "rolling", "oracle"],
                    "default": "all",
                    "description": "Type of metrics to return."
                }
            }
        }
    },
    {
        "name": "list_datasets_and_months",
        "description": "List all monitored datasets, candidate units, event volumes, available months, and Hugging Face endpoint status.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

MCP_RESOURCES = [
    {
        "uri": "delhi://hotspots/forecast/all",
        "name": "Complete Hotspots Forecast (All Spatial Units)",
        "mimeType": "application/json",
        "description": "Complete ranked forecasts across all candidate units for all spatial datasets."
    },
    {
        "uri": "delhi://hotspots/forecast/top7",
        "name": "Top Hotspots Forecast (Legacy)",
        "mimeType": "application/json",
        "description": "Top forecast hotspots across all spatial datasets (backward compatibility alias)."
    },
    {
        "uri": "delhi://hotspots/metrics/summary",
        "name": "Rolling Origin Metrics Summary",
        "mimeType": "application/json",
        "description": "Summary of rolling-origin temporal evaluation metrics and oracle perplexity bounds."
    },
    {
        "uri": "delhi://hotspots/datasets/complete_store",
        "name": "Delhi Hotspots Complete Store Summary",
        "mimeType": "application/json",
        "description": "Complete metadata and coverage summary of all 4 monitored datasets."
    }
]


def handle_rpc_request(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handles an incoming JSON-RPC 2.0 request according to the MCP specification."""
    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False}
                },
                "serverInfo": {
                    "name": "delhi-hotspots-ml-mcp",
                    "version": "1.1.0"
                }
            }
        }

    elif method == "notifications/initialized":
        return None

    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": MCP_TOOLS
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})

        try:
            if tool_name == "fetch_dataset_records":
                out = fetch_dataset_records(
                    dataset=args.get("dataset", "all"),
                    data_type=args.get("data_type", "hotspots"),
                    month=args.get("month"),
                    limit=args.get("limit", "all"),
                    offset=int(args.get("offset", 0)),
                    filter_district=args.get("filter_district"),
                    filter_station=args.get("filter_station"),
                    spatial_method=args.get("spatial_method", "police")
                )
            elif tool_name == "query_hotspots":
                out = query_hotspots(
                    dataset=args.get("dataset"),
                    month=args.get("month"),
                    query_text=args.get("query_text"),
                    top_k=args.get("top_k", "all"),
                    spatial_method=args.get("spatial_method", "metro"),
                    include_related_analysis=args.get("include_related_analysis", True),
                    data_type=args.get("data_type", "hotspots")
                )
            elif tool_name == "predict_hotspots":
                out = predict_hotspots(
                    dataset=args.get("dataset"),
                    target_month=args.get("target_month"),
                    top_k=args.get("top_k", "all"),
                    spatial_method=args.get("spatial_method", "police"),
                    use_lgcp=bool(args.get("use_lgcp", False)),
                    temper=float(args.get("temper", 0.01))
                )
            elif tool_name == "query_dataset_analytics":
                out = query_dataset_analytics(
                    dataset=args.get("dataset", "all"),
                    query_type=args.get("query_type", "hotspot_persistence"),
                    entity_name=args.get("entity_name"),
                    start_month=args.get("start_month"),
                    end_month=args.get("end_month"),
                    limit=args.get("limit", "all"),
                    filter_district=args.get("filter_district")
                )
            elif tool_name == "get_hotspot_map":
                out = get_hotspot_map(
                    map_type=args.get("map_type", "four_dataset_explorer"),
                    open_in_browser=args.get("open_in_browser", True)
                )
            elif tool_name == "get_model_metrics":
                out = get_model_metrics(
                    dataset=args.get("dataset"),
                    evaluation_type=args.get("evaluation_type", "all")
                )
            elif tool_name == "list_datasets_and_months":
                out = list_datasets_and_months()
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(out, indent=2)
                        }
                    ]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(e)}
            }

    elif method == "resources/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "resources": MCP_RESOURCES
            }
        }

    elif method == "resources/read":
        uri = params.get("uri")
        if uri == "delhi://hotspots/forecast/all":
            content = json.dumps(load_forecasts(limit="all"), indent=2)
        elif uri == "delhi://hotspots/forecast/top7":
            content = json.dumps(load_forecasts(limit=7), indent=2)
        elif uri == "delhi://hotspots/metrics/summary":
            content = json.dumps(load_rolling_origin(), indent=2)
        elif uri == "delhi://hotspots/datasets/complete_store":
            store = load_complete_store()
            summary = {
                "version": store.get("version"),
                "as_of": store.get("as_of"),
                "datasets": {
                    k: {
                        "label": v.get("label"),
                        "unit_type": v.get("unit_type") or v.get("unit_types"),
                        "candidate_units": v.get("candidate_units"),
                        "months_tracked": len(v.get("months", {})) if "months" in v else len(v.get("monthly_counts", {}))
                    }
                    for k, v in store.get("datasets", {}).items()
                }
            }
            content = json.dumps(summary, indent=2)
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": f"Resource not found: {uri}"}
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": content
                    }
                ]
            }
        }

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not supported: {method}"}
        }


def run_stdio_server():
    """Runs standard stdio JSON-RPC loop."""
    sys.stderr.write("Delhi Hotspots ML MCP Server started (stdio transport).\n")
    sys.stderr.write(f"Complete dataset store loaded. Hugging Face endpoint: {DEFAULT_HF_SPACE_URL}\n")
    sys.stderr.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle_rpc_request(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError as err:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {str(err)}"}
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio_server()
