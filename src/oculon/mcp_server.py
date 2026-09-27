#!/usr/bin/env python3
"""
oculon.mcp_server
-----------------
Model Context Protocol (MCP) server for Oculon / Delhi Hotspots ML.
Exposes spatial-temporal hotspot forecasts, evaluation metrics, and interactive maps.
"""

import sys
import os
import json
import csv
import webbrowser
from pathlib import Path
from typing import Dict, Any, List, Optional

# Potential search paths for data and maps
MODULE_DIR = Path(__file__).resolve().parent
POSSIBLE_DATA_DIRS = [
    MODULE_DIR / "data",
    MODULE_DIR.parent.parent / "data",
    MODULE_DIR.parent.parent / "reports",
    Path.cwd() / "data",
    Path.cwd() / "reports",
]
POSSIBLE_MAP_DIRS = [
    MODULE_DIR / "maps",
    MODULE_DIR.parent.parent / "maps",
    MODULE_DIR.parent.parent / "app",
    Path.cwd() / "maps",
    Path.cwd() / "app",
]

def find_file(filename: str, directories: List[Path]) -> Optional[Path]:
    for d in directories:
        target = d / filename
        if target.exists():
            return target
    return None

# Default hosted Hugging Face Space URL
DEFAULT_HF_SPACE_URL = os.environ.get("HF_SPACE_URL", "https://abhyudaymishr-oculon.hf.space")


def load_forecasts() -> List[Dict[str, Any]]:
    """Loads pre-computed top 7 forecasts across datasets."""
    p = find_file("four_dataset_forecast_top_seven.csv", POSSIBLE_DATA_DIRS)
    if not p:
        return []
    rows = []
    with open(p, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def load_dataset_comparison() -> Dict[str, Any]:
    """Loads baseline 80/20 holdout metrics and dataset coverage."""
    p = find_file("dataset_comparison.json", POSSIBLE_DATA_DIRS)
    if not p:
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def load_rolling_origin() -> Dict[str, Any]:
    """Loads forward-time rolling-origin evaluation metrics."""
    p = find_file("rolling_origin_summary.json", POSSIBLE_DATA_DIRS)
    if not p:
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def query_hotspots(dataset: Optional[str] = None, month: Optional[str] = None, query_text: Optional[str] = None) -> Dict[str, Any]:
    """Query top hotspot forecasts with optional dataset, month, or keyword filter."""
    forecasts = load_forecasts()
    filtered = []

    ds_filter = None
    if dataset:
        ds_lower = dataset.lower().replace(" ", "_")
        if "person" in ds_lower:
            ds_filter = "Missing persons"
        elif "body" in ds_lower or "bodies" in ds_lower:
            ds_filter = "Unidentified bodies"
        elif "vehicle" in ds_lower or "stolen" in ds_lower:
            ds_filter = "Stolen vehicles"
        elif "mobile" in ds_lower:
            ds_filter = "Missing mobiles"

    if query_text:
        q = query_text.lower()
        if "person" in q and not ds_filter:
            ds_filter = "Missing persons"
        elif ("body" in q or "bodies" in q) and not ds_filter:
            ds_filter = "Unidentified bodies"
        elif ("vehicle" in q or "stolen" in q) and not ds_filter:
            ds_filter = "Stolen vehicles"
        elif "mobile" in q and not ds_filter:
            ds_filter = "Missing mobiles"

    for row in forecasts:
        if ds_filter and ds_filter.lower() not in row.get("dataset", "").lower():
            continue
        if month and month != row.get("forecast_month", ""):
            continue
        filtered.append(row)

    items = []
    for r in filtered:
        items.append({
            "dataset": r.get("dataset"),
            "rank": int(r.get("rank", 0)) if r.get("rank") else None,
            "forecast_month": r.get("forecast_month"),
            "location_proxy": r.get("location"),
            "district": r.get("district") or "N/A",
            "spatial_method": r.get("method"),
            "latitude": float(r.get("latitude")) if r.get("latitude") else None,
            "longitude": float(r.get("longitude")) if r.get("longitude") else None,
            "relative_score": float(r.get("relative_model_score")) if r.get("relative_model_score") else None,
            "confidence": r.get("location_confidence")
        })

    map_url = get_map_url("four_dataset_explorer")
    hosted_url = get_hosted_map_url("four_dataset_explorer")
    return {
        "status": "success",
        "count": len(items),
        "results": items,
        "browser_map_url": map_url,
        "hosted_space_url": hosted_url,
        "note": "Coordinates are administrative station proxies or PIN/metro approximations, not exact incident scenes."
    }


def get_map_url(map_type: str = "four_dataset_explorer") -> str:
    """Returns local file URI or hosted Hugging Face Space map URL."""
    base_hf = os.environ.get("HF_SPACE_URL", DEFAULT_HF_SPACE_URL).rstrip("/")
    map_files = {
        "four_dataset_explorer": "four_dataset_hotspot_explorer.html",
        "missing_persons": "missing_persons_map.html",
        "stolen_vehicles": "stolen_vehicles_map.html",
        "mobiles_and_bodies": "mobiles_and_bodies_map.html"
    }
    filename = map_files.get(map_type, "four_dataset_hotspot_explorer.html")

    p = find_file(filename, POSSIBLE_MAP_DIRS)
    if not p:
        # Check subfolder individual_maps
        p = find_file(f"individual_maps/{filename}", POSSIBLE_MAP_DIRS)
    if p and p.exists():
        return p.as_uri()
    return f"{base_hf}/maps/{filename}"


def get_hosted_map_url(map_type: str = "four_dataset_explorer") -> str:
    """Returns the public hosted Hugging Face Space map URL."""
    base_hf = os.environ.get("HF_SPACE_URL", DEFAULT_HF_SPACE_URL).rstrip("/")
    map_files = {
        "four_dataset_explorer": "four_dataset_hotspot_explorer.html",
        "missing_persons": "missing_persons_map.html",
        "stolen_vehicles": "stolen_vehicles_map.html",
        "mobiles_and_bodies": "mobiles_and_bodies_map.html"
    }
    filename = map_files.get(map_type, "four_dataset_hotspot_explorer.html")
    return f"{base_hf}/maps/{filename}"


def get_hotspot_map(map_type: str = "four_dataset_explorer", open_in_browser: bool = True) -> Dict[str, Any]:
    """
    Returns the interactive map link and launches the user's default browser if running in a client environment.
    """
    map_url = get_map_url(map_type)
    hosted_url = get_hosted_map_url(map_type)
    browser_opened = False

    if open_in_browser:
        try:
            browser_opened = webbrowser.open(map_url, new=2)
        except Exception:
            browser_opened = False

    return {
        "status": "success",
        "map_type": map_type,
        "browser_map_url": map_url,
        "hosted_space_url": hosted_url,
        "browser_opened_locally": browser_opened,
        "message": f"Interactive hotspot map available at: {map_url}. Hosted on Hugging Face: {hosted_url}. " +
                   ("Browser opened automatically." if browser_opened else "Click or navigate to the link to open in your browser.")
    }


def get_model_metrics(dataset: Optional[str] = None, evaluation_type: str = "all") -> Dict[str, Any]:
    """Returns baseline 80/20 holdout metrics or strict forward-time rolling-origin evaluation."""
    baseline = load_dataset_comparison()
    rolling = load_rolling_origin()

    return {
        "status": "success",
        "baseline_80_20": baseline.get("datasets", {}) if evaluation_type in ("all", "baseline") else None,
        "rolling_origin_forward_time": rolling if evaluation_type in ("all", "rolling") else None,
        "notes": {
            "missing_mobiles": "Non-spatial dataset (no physical coordinates in source).",
            "proxy_locations": "Missing persons and dead bodies map to police station proxies; stolen vehicles map to PIN centroids or nearest metro stations."
        }
    }


def list_datasets_and_months() -> Dict[str, Any]:
    """Lists available datasets, colors, spatial representation, and forecast periods."""
    return {
        "datasets": [
            {
                "id": "missing_persons",
                "label": "Missing Persons",
                "color": "#2864b7",
                "unit": "Police-station reporting-area proxy",
                "latest_forecast_month": "2026-10",
                "spatial_capability": True
            },
            {
                "id": "unidentified_bodies",
                "label": "Unidentified Dead Bodies",
                "color": "#8c4bb8",
                "unit": "Police-station reference proxy",
                "latest_forecast_month": "2026-10",
                "spatial_capability": True
            },
            {
                "id": "stolen_vehicles",
                "label": "Stolen Vehicles",
                "color": "#c74440",
                "unit": "Approximate postal centroid or nearest metro station",
                "latest_forecast_month": "2026-10",
                "spatial_capability": True
            },
            {
                "id": "missing_mobiles",
                "label": "Missing Mobiles",
                "color": "#d58a13",
                "unit": "Unlocated (temporal counts only, no physical coordinates)",
                "latest_forecast_month": None,
                "spatial_capability": False
            }
        ],
        "available_maps": [
            {"id": "four_dataset_explorer", "title": "Delhi 4-Dataset Spatiotemporal Hotspot Explorer"},
            {"id": "missing_persons", "title": "Missing Persons Station Proxy Map"},
            {"id": "stolen_vehicles", "title": "Stolen Vehicles (PIN & Metro) Map"},
            {"id": "mobiles_and_bodies", "title": "Mobiles & Unidentified Bodies Map"}
        ]
    }


MCP_TOOLS = [
    {
        "name": "query_hotspots",
        "description": "Query top forecast hotspots for Delhi crime and public safety datasets (Missing Persons, Unidentified Dead Bodies, Stolen Vehicles, Missing Mobiles).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "description": "Dataset name: 'missing_persons', 'unidentified_bodies', 'stolen_vehicles', or 'missing_mobiles'."
                },
                "month": {
                    "type": "string",
                    "description": "Target forecast month in YYYY-MM format (e.g. '2026-10')."
                },
                "query_text": {
                    "type": "string",
                    "description": "Natural text query such as 'top hotspots stolen vehicles 2026-10'."
                }
            }
        }
    },
    {
        "name": "get_hotspot_map",
        "description": "Get the URL of the interactive spatiotemporal map and optionally open it in the local default web browser.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "map_type": {
                    "type": "string",
                    "enum": ["four_dataset_explorer", "missing_persons", "stolen_vehicles", "mobiles_and_bodies"],
                    "default": "four_dataset_explorer",
                    "description": "Which interactive map to view."
                },
                "open_in_browser": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to actively launch the user's default web browser to display the map."
                }
            }
        }
    },
    {
        "name": "get_model_metrics",
        "description": "Get model evaluation metrics: baseline 80/20 holdout vs strict forward-time rolling-origin evaluation (Accuracy, F1, Log Loss, Brier score, Wasserstein W1 distance).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "description": "Dataset identifier or 'all'."
                },
                "evaluation_type": {
                    "type": "string",
                    "enum": ["all", "baseline", "rolling"],
                    "default": "all",
                    "description": "Evaluation type: 'baseline', 'rolling', or 'all'."
                }
            }
        }
    },
    {
        "name": "list_datasets_and_months",
        "description": "List all four monitored datasets, spatial representations, available months, and interactive maps.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

MCP_RESOURCES = [
    {
        "uri": "delhi://hotspots/forecast/top7",
        "name": "Top 7 Hotspots Forecast",
        "mimeType": "application/json",
        "description": "Pre-computed top 7 forecast hotspots per spatial dataset."
    },
    {
        "uri": "delhi://hotspots/metrics/summary",
        "name": "Rolling Origin Metrics Summary",
        "mimeType": "application/json",
        "description": "Summary of rolling-origin temporal evaluation metrics across models."
    }
]


def handle_rpc_request(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
                    "name": "oculon-mcp",
                    "version": "1.0.0"
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
            if tool_name == "query_hotspots":
                out = query_hotspots(
                    dataset=args.get("dataset"),
                    month=args.get("month"),
                    query_text=args.get("query_text")
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
        if uri == "delhi://hotspots/forecast/top7":
            content = json.dumps(load_forecasts(), indent=2)
        elif uri == "delhi://hotspots/metrics/summary":
            content = json.dumps(load_rolling_origin(), indent=2)
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
    sys.stderr.write("Oculon MCP Server started (stdio transport).\n")
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


def main():
    """Console script entrypoint for oculon / oculon-mcp."""
    run_stdio_server()


if __name__ == "__main__":
    main()
