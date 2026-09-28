#!/usr/bin/env python3
"""
Delhi Hotspots ML - Hugging Face Space Application
--------------------------------------------------
Interactive Spatiotemporal Crime Hotspot Explorer & Model Context Protocol (MCP) Server.
Combines:
1. Gradio Web Interface with embedded maps, user-controlled query tools, and live model prediction.
2. Direct static map hosting under /maps/.
3. Programmatic REST API under /api/ with complete dataset fetching and dynamic limits.
4. Remote MCP SSE server under /sse and /messages for Claude, Cursor, and AI agents.
"""

# ZeroGPU compatibility for Hugging Face Spaces: MUST be imported before Gradio or FastAPI
try:
    import spaces
except Exception:
    class _MockSpaces:
        def GPU(self, *args, **kwargs):
            def decorator(fn):
                return fn
            if args and callable(args[0]):
                return args[0]
            return decorator
    spaces = _MockSpaces()

@spaces.GPU
def _dummy_gpu_function():
    return True

import os
import sys
import json
import csv
import uuid
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

try:
    import gradio as gr
    HAS_GRADIO = True
except ImportError:
    HAS_GRADIO = False
    gr = None

try:
    from fastapi import FastAPI, Request, Response
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False



# Directories
BASE_DIR = Path(__file__).resolve().parent
MAPS_DIR = BASE_DIR / "maps" if (BASE_DIR / "maps").exists() else BASE_DIR / "src" / "oculon" / "maps"
DATA_DIR = BASE_DIR / "data" if (BASE_DIR / "data").exists() else BASE_DIR / "src" / "oculon" / "data"

FORECAST_ALL_CSV = DATA_DIR / "four_dataset_forecast_all_units.csv"
FORECAST_CSV = DATA_DIR / "four_dataset_forecast_top_seven.csv"
COMPARISON_JSON = DATA_DIR / "dataset_comparison.json"
ROLLING_JSON = DATA_DIR / "rolling_origin_summary.json"
CONFIG_JSON = DATA_DIR / "model_config.json"
COMPLETE_STORE_JSON = DATA_DIR / "four_dataset_complete_store.json"

# Import enhanced MCP server engine from bundled package
sys.path.insert(0, str(BASE_DIR))
try:
    from src.oculon import mcp_server
except ImportError:
    try:
        import mcp_server
    except ImportError:
        mcp_server = None


# ==============================================================================
# Data Loading Utilities
# ==============================================================================

def load_forecasts(
    dataset: Optional[str] = None,
    limit: Optional[Union[int, str]] = None
) -> List[Dict[str, Any]]:
    if mcp_server:
        return mcp_server.load_forecasts(dataset=dataset, limit=limit)
    source_csv = FORECAST_ALL_CSV if FORECAST_ALL_CSV.exists() else FORECAST_CSV
    if not source_csv.exists():
        return []
    rows = []
    with open(source_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    if dataset:
        ds_low = dataset.lower().replace(" ", "_")
        rows = [r for r in rows if ds_low in r.get("dataset", "").lower().replace(" ", "_")]
    if limit is not None and str(limit).lower() not in ("all", "none", "unlimited", "-1"):
        try:
            rows = rows[:max(1, int(limit))]
        except (ValueError, TypeError):
            pass
    return rows


def load_dataset_comparison() -> Dict[str, Any]:
    if mcp_server:
        return mcp_server.load_dataset_comparison()
    if not COMPARISON_JSON.exists():
        return {}
    with open(COMPARISON_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def load_rolling_origin() -> Dict[str, Any]:
    if mcp_server:
        return mcp_server.load_rolling_origin()
    if not ROLLING_JSON.exists():
        return {}
    with open(ROLLING_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================================================================
# Model Context Protocol (MCP) Logic
# ==============================================================================

MCP_TOOLS = mcp_server.MCP_TOOLS if mcp_server else []
MCP_RESOURCES = mcp_server.MCP_RESOURCES if mcp_server else []


def execute_mcp_tool(name: str, args: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    if not mcp_server:
        raise RuntimeError("MCP Server engine is not available.")

    if name == "fetch_dataset_records":
        return mcp_server.fetch_dataset_records(
            dataset=args.get("dataset", "all"),
            data_type=args.get("data_type", "hotspots"),
            month=args.get("month"),
            limit=args.get("limit", "all"),
            offset=int(args.get("offset", 0)),
            filter_district=args.get("filter_district"),
            filter_station=args.get("filter_station"),
            spatial_method=args.get("spatial_method", "police")
        )

    elif name == "query_hotspots":
        res = mcp_server.query_hotspots(
            dataset=args.get("dataset"),
            month=args.get("month"),
            query_text=args.get("query_text"),
            top_k=args.get("top_k", "all"),
            spatial_method=args.get("spatial_method", "metro"),
            include_related_analysis=args.get("include_related_analysis", True),
            data_type=args.get("data_type", "hotspots")
        )
        res["hosted_map_url"] = f"{base_url}/maps/four_dataset_hotspot_explorer.html"
        return res

    elif name == "predict_hotspots":
        res = mcp_server.predict_hotspots(
            dataset=args.get("dataset", "missing_persons"),
            target_month=args.get("target_month", "2026-11"),
            top_k=args.get("top_k", "all"),
            spatial_method=args.get("spatial_method", "police"),
            use_lgcp=bool(args.get("use_lgcp", False)),
            temper=float(args.get("temper", 0.01))
        )
        return res

    elif name == "query_dataset_analytics":
        res = mcp_server.query_dataset_analytics(
            dataset=args.get("dataset", "all"),
            query_type=args.get("query_type", "hotspot_persistence"),
            entity_name=args.get("entity_name"),
            start_month=args.get("start_month"),
            end_month=args.get("end_month"),
            limit=args.get("limit", "all"),
            filter_district=args.get("filter_district")
        )
        return res

    elif name == "get_hotspot_map":
        map_type = args.get("map_type", "four_dataset_explorer")
        map_files = {
            "four_dataset_explorer": "four_dataset_hotspot_explorer.html",
            "missing_persons": "missing_persons_map.html",
            "stolen_vehicles": "stolen_vehicles_map.html",
            "mobiles_and_bodies": "mobiles_and_bodies_map.html"
        }
        filename = map_files.get(map_type, "four_dataset_hotspot_explorer.html")
        map_url = f"{base_url}/maps/{filename}"
        return {
            "status": "success",
            "map_type": map_type,
            "hosted_map_url": map_url,
            "message": f"Interactive hotspot map available at {map_url}."
        }

    elif name == "get_model_metrics":
        return mcp_server.get_model_metrics(
            dataset=args.get("dataset"),
            evaluation_type=args.get("evaluation_type", "all")
        )

    elif name == "list_datasets_and_months":
        res = mcp_server.list_datasets_and_months()
        res["hugging_face_connection"]["space_url"] = base_url
        res["hugging_face_connection"]["remote_mcp_sse_endpoint"] = f"{base_url}/sse"
        res["hugging_face_connection"]["remote_rest_api"] = f"{base_url}/api/hotspots"
        return res

    raise ValueError(f"Unknown MCP tool: {name}")


def handle_remote_rpc(req: Dict[str, Any], base_url: str) -> Optional[Dict[str, Any]]:
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
                    "name": "oculon-delhi-hotspots-hf-space",
                    "version": "1.1.0"
                }
            }
        }
    elif method == "notifications/initialized":
        return None
    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    elif method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS}}
    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        try:
            res = execute_mcp_tool(tool_name, args, base_url)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(res, indent=2)}]
                }
            }
        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}}
    elif method == "resources/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": MCP_RESOURCES}}
    elif method == "resources/read":
        uri = params.get("uri")
        if uri == "delhi://hotspots/forecast/all":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(load_forecasts(limit="all"), indent=2)}]}
            }
        elif uri == "delhi://hotspots/forecast/top7":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(load_forecasts(limit=7), indent=2)}]}
            }
        elif uri == "delhi://hotspots/metrics/summary":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(load_rolling_origin(), indent=2)}]}
            }
        else:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": f"Resource not found: {uri}"}}
    else:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not supported: {method}"}}


# Active SSE client sessions
sse_sessions: Dict[str, asyncio.Queue] = {}


# ==============================================================================
# Gradio UI Construction
# ==============================================================================

MAP_OPTIONS = {
    "Unified 4-Dataset Spatiotemporal Explorer": "four_dataset_hotspot_explorer.html",
    "Stolen Vehicles Map (Metro & PIN)": "stolen_vehicles_map.html",
    "Missing Persons Map (Station Proxies)": "missing_persons_map.html",
    "Missing Mobiles & Unidentified Bodies": "mobiles_and_bodies_map.html"
}

def get_map_iframe(selected_label: str) -> str:
    filename = MAP_OPTIONS.get(selected_label, "four_dataset_hotspot_explorer.html")
    map_url = f"/maps/{filename}"
    return f"""
    <div style="margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; background: #f8fafc; padding: 12px 16px; border-radius: 8px; border: 1px solid #e2e8f0;">
        <span style="font-weight: 600; color: #1e293b;">Active Map: <code style="color: #2563eb;">{filename}</code></span>
        <a href="{map_url}" target="_blank" style="display: inline-flex; align-items: center; gap: 6px; background-color: #2563eb; color: white; text-decoration: none; font-weight: 600; padding: 8px 16px; border-radius: 6px; font-size: 14px; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#1d4ed8'" onmouseout="this.style.backgroundColor='#2563eb'">
            Open Map in Fullscreen Browser Tab &rarr;
        </a>
    </div>
    <iframe src="{map_url}" style="width: 100%; height: 780px; border: 1px solid #cbd5e1; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);" title="Delhi Hotspots Map"></iframe>
    """


@spaces.GPU
def search_hotspots(
    dataset: str,
    month: str,
    query_text: str,
    limit_count: int = 25,
    fetch_all: bool = False,
    data_type: str = "hotspots",
    district_filter: str = ""
):
    if not mcp_server:
        return "MCP server not initialized", [], "{}", ""

    eff_limit = "all" if fetch_all else int(limit_count)
    res = mcp_server.fetch_dataset_records(
        dataset=dataset if dataset != "All Datasets" else "all",
        data_type=data_type,
        month=month if month != "All Months" else None,
        limit=eff_limit,
        filter_district=district_filter if district_filter.strip() else None,
        filter_station=query_text if query_text.strip() else None
    )

    table_data = []
    csv_rows = []

    if data_type == "all_units":
        units = res.get("units", [])
        headers = ["Unit ID", "Name", "District", "Latitude", "Longitude", "Unit Type"]
        csv_rows.append(",".join(headers))
        for u in units:
            row = [
                str(u.get("unit_id", "")),
                str(u.get("name", "")),
                str(u.get("district", "N/A")),
                str(u.get("latitude", "")),
                str(u.get("longitude", "")),
                str(u.get("unit_type", ""))
            ]
            table_data.append(row)
            csv_rows.append('"' + '","'.join(row) + '"')
        tot = res.get('total_matching_units', len(units))
        summary_md = f"### Fetched **{len(units)}** of **{tot}** Monitored Units (Dataset: {dataset})"

    elif data_type == "monthly_timeline":
        timeline = res.get("timeline", [])
        headers = ["Dataset", "Month", "Train Events", "Test Events", "Total Events", "Split"]
        csv_rows.append(",".join(headers))
        for t in timeline:
            row = [
                str(t.get("dataset", "")),
                str(t.get("month", "")),
                str(t.get("train_events", 0)),
                str(t.get("test_events", 0)),
                str(t.get("total_events", 0)),
                str(t.get("split", "observed"))
            ]
            table_data.append(row)
            csv_rows.append('"' + '","'.join(row) + '"')
        summary_md = f"### Fetched **{len(timeline)}** Monthly Observations (Dataset: {dataset})"

    elif data_type == "station_records":
        stations = res.get("stations", [])
        headers = ["Station ID", "Name", "District", "Total Events", "Active Months", "First Seen", "Last Seen"]
        csv_rows.append(",".join(headers))
        for s in stations:
            row = [
                str(s.get("station_id", "")),
                str(s.get("name", "")),
                str(s.get("district", "N/A")),
                str(s.get("total_events", 0)),
                str(s.get("active_months", 0)),
                str(s.get("first_seen", "")),
                str(s.get("last_seen", ""))
            ]
            table_data.append(row)
            csv_rows.append('"' + '","'.join(row) + '"')
        summary_md = f"### Fetched **{len(stations)}** Station Records (Dataset: {dataset})"

    else:
        # Default: hotspots predictions
        hotspots = res.get("hotspots", [])
        headers = ["Rank", "Location Proxy", "District", "Spatial Basis", "Model Score", "Incidents", "Classification"]
        csv_rows.append(",".join(headers))
        for r in hotspots:
            score_val = r.get("relative_multigram_score")
            score_str = f"{float(score_val):.6f}" if score_val else "N/A"
            row = [
                str(r.get("rank") or "N/A"),
                str(r.get("name") or r.get("station_id")),
                str(r.get("district") or "N/A"),
                str(r.get("spatial_representation") or "proxy"),
                score_str,
                str(r.get("incident_count", 0)),
                str(r.get("classification") or "forecast")
            ]
            table_data.append(row)
            csv_rows.append('"' + '","'.join(row) + '"')

        related = res.get("related_independent_analysis", {})
        summary_md = f"### Found **{len(hotspots)}** Hotspot Locations for **{res.get('target_month', month)}** ({res.get('dataset', dataset)})"
        if related and "citywide_monthly_events" in related:
            summary_md += f"\n- **Citywide Total Events**: {related.get('citywide_monthly_events', 'N/A'):,} (Ratio vs 12m Median: {related.get('volume_vs_median_ratio', 'N/A')}x)"
            summary_md += f"\n- **Hotspot Entropy**: {related.get('predictive_entropy_nats', 'N/A')} nats &bull; **Effective Dispersion**: {related.get('effective_hotspot_dispersion_units', 'N/A')} units"

    related_json = json.dumps(res.get("related_independent_analysis", res), indent=2)
    csv_text = "\n".join(csv_rows)
    return summary_md, table_data, related_json, csv_text


@spaces.GPU
def run_live_prediction(dataset: str, target_month: str, top_k: int, evaluate_all: bool = False):
    if not mcp_server:
        return "MCP Server not initialized", []
    eff_k = "all" if evaluate_all else int(top_k)
    res = mcp_server.predict_hotspots(
        dataset=dataset,
        target_month=target_month,
        top_k=eff_k
    )
    if res.get("status") != "success":
        return f"### Error: {res.get('message')}", []

    hotspots = res.get("hotspots", [])
    table = []
    for h in hotspots:
        table.append([
            str(h.get("rank")),
            h.get("name"),
            h.get("district", "N/A"),
            f"{float(h.get('relative_multigram_score', 0)):.6f}",
            f"{h.get('latitude', '')}, {h.get('longitude', '')}",
            h.get("spatial_representation")
        ])

    user_lim = "All" if evaluate_all else str(top_k)
    summary = f"### Live On-The-Fly Forecast for **{target_month}** ({dataset})\n"
    summary += f"- **Candidate Units Evaluated**: **{len(hotspots)}** stations (User limit: `{user_lim}`)\n"
    summary += f"- **History Used**: {res.get('history_events_used', 'N/A'):,} dated records up to `{res.get('history_cutoff_date')}`\n"
    summary += f"- **Predictive Perplexity**: **{res.get('predictive_perplexity')}** (Entropy: {res.get('predictive_entropy_nats')} nats)\n"
    return summary, table


def get_evaluation_tables():
    baseline_rows = [
        ["Missing persons", "83,388 / 20,847", "0.395", "3.21 km", "Police-station reporting proxy (210 units)"],
        ["Unidentified bodies", "7,914 / 1,978", "0.446", "2.69 km", "Police-station reference proxy (210 units)"],
        ["Stolen vehicles (Metro)", "21,082 / 5,270", "0.450", "4.82 km", "Nearest metro station (259 units)"],
        ["Stolen vehicles (PIN)", "21,082 / 5,270", "0.372", "6.24 km", "Postal PIN centroid (98 units)"],
        ["Missing mobiles", "1,282 / 320", "N/A", "N/A", "Virtual eTheft station (non-spatial)"]
    ]

    rolling_rows = [
        ["Missing persons (Baseline)", "27 (2024-06 to 2026-08)", "0.9210", "0.5234", "0.5372", "4.9907", "146.70", "1.23 km"],
        ["Missing persons (Pure Temporal)", "27 (2024-06 to 2026-08)", "0.9369", "0.6191", "0.6684", "4.9432", "140.21", "0.88 km"],
        ["Unidentified bodies", "11 (2025-10 to 2026-08)", "0.9628", "0.5169", "0.5493", "4.7368", "117.02", "2.10 km"],
        ["Stolen vehicles (PIN)", "17 (2025-04 to 2026-08)", "0.9436", "0.5727", "0.6354", "4.0215", "55.96", "2.00 km"],
        ["Stolen vehicles (Metro)", "17 (2025-04 to 2026-08)", "0.9777", "0.5149", "0.6436", "3.9023", "49.15", "1.69 km"]
    ]

    return baseline_rows, rolling_rows


# ==============================================================================
# Gradio UI Construction
# ==============================================================================

def build_gradio_demo():
    if not HAS_GRADIO:
        return None

    with gr.Blocks(title="Oculon - Delhi Hotspots ML Explorer & MCP Server", theme=gr.themes.Soft(primary_hue="blue")) as demo:
        gr.HTML("""
        <div style="background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%); color: white; padding: 24px; border-radius: 12px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #f8fafc;">Oculon: Delhi Hotspots ML Explorer</h1>
                    <p style="margin: 6px 0 0 0; color: #94a3b8; font-size: 15px;">
                        Spatiotemporal crime & safety forecasting &bull; Completely user-controlled queries across all 4 datasets &bull; Hugging Face Space: <code>AbhyudayMishr/Oculon</code>
                    </p>
                </div>
                <div style="display: flex; gap: 8px;">
                    <span style="background: #2563eb; color: white; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 9999px;">Gradio UI</span>
                    <span style="background: #10b981; color: white; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 9999px;">Universal Dataset MCP</span>
                    <span style="background: #f59e0b; color: white; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 9999px;">Live Model Running</span>
                </div>
            </div>
            <div style="display: flex; gap: 16px; margin-top: 14px; flex-wrap: wrap; font-size: 13px; color: #cbd5e1;">
                <span><b>Missing Persons</b>: 104,235 events &bull; 210 Stations &bull; 136 Months</span>
                <span><b>Unidentified Bodies</b>: 9,892 events &bull; 210 Stations &bull; 53 Months</span>
                <span><b>Stolen Vehicles</b>: 26,352 events &bull; 259 Metro / 98 PIN &bull; 83 Months</span>
                <span><b>Missing Mobiles</b>: 1,602 events &bull; Virtual eTheft &bull; 9 Months</span>
            </div>
        </div>
        """)

        with gr.Tabs():
            # TAB 1: MAP EXPLORER
            with gr.TabItem("Interactive Hotspots Map", id="tab_map"):
                with gr.Row():
                    map_selector = gr.Radio(
                        choices=list(MAP_OPTIONS.keys()),
                        value="Unified 4-Dataset Spatiotemporal Explorer",
                        label="Choose Interactive Map Visualization",
                        interactive=True
                    )

                map_frame = gr.HTML(value=get_map_iframe("Unified 4-Dataset Spatiotemporal Explorer"))
                map_selector.change(fn=get_map_iframe, inputs=[map_selector], outputs=[map_frame])

            # TAB 2: QUERY HOTSPOTS (USER-CONTROLLED QUANTITY & KIND)
            with gr.TabItem("Complete Dataset Hotspots Query", id="tab_query"):
                gr.Markdown("""
                ### Flexible User-Controlled Query Engine
                Select **what kind of data** you need and **how much data** to return (any count or the complete dataset).
                Runs automatic independent related analysis across multi-year history.
                """)
                with gr.Row():
                    dataset_dropdown = gr.Dropdown(
                        choices=["All Datasets", "Missing persons", "Unidentified bodies", "Stolen vehicles", "Missing mobiles"],
                        value="Missing persons",
                        label="1. Dataset"
                    )
                    data_type_dropdown = gr.Dropdown(
                        choices=["hotspots", "all_units", "monthly_timeline", "station_records"],
                        value="hotspots",
                        label="2. Data Type"
                    )
                    month_dropdown = gr.Dropdown(
                        choices=["2026-10", "2026-09", "2026-08", "2025-06", "2025-01", "2024-11", "2024-06", "All Months"],
                        value="2026-10",
                        label="3. Month Filter"
                    )

                with gr.Row():
                    query_input = gr.Textbox(
                        value="",
                        label="Station Search / Keyword Filter",
                        placeholder="e.g. Bawana, Kashmere Gate, Rohini, Kapashera"
                    )
                    district_input = gr.Textbox(
                        value="",
                        label="District Filter",
                        placeholder="e.g. North, South East, Dwarka, Central"
                    )
                    limit_slider = gr.Slider(
                        minimum=1,
                        maximum=259,
                        value=25,
                        step=1,
                        label="Number of Records to Return"
                    )
                    all_chk = gr.Checkbox(
                        value=False,
                        label="Fetch Complete Dataset (All Records, No Cap)"
                    )

                search_btn = gr.Button("Execute User-Controlled Query", variant="primary")

                query_summary = gr.Markdown("### Click 'Execute User-Controlled Query' to view records.")
                results_table = gr.Dataframe(
                    headers=["Col 1", "Col 2", "Col 3", "Col 4", "Col 5", "Col 6", "Col 7"],
                    interactive=False
                )

                with gr.Accordion("Raw CSV Export & Independent Intelligence", open=False):
                    csv_export_box = gr.Textbox(label="Direct CSV Output (Copyable / Exportable)", lines=5)
                    related_output = gr.Code(language="json", label="Independent Related Intelligence")

                search_btn.click(
                    fn=search_hotspots,
                    inputs=[dataset_dropdown, month_dropdown, query_input, limit_slider, all_chk, data_type_dropdown, district_input],
                    outputs=[query_summary, results_table, related_output, csv_export_box]
                )

            # TAB 3: LIVE MODEL INFERENCE
            with gr.TabItem("Live Model Prediction Engine", id="tab_live"):
                gr.Markdown("""
                ### Dynamic On-The-Fly Model Execution
                Run the spatial multigram model dynamically for **any month** using the complete historical event stream.
                Evaluate any custom count of units or all 210 candidate police stations.
                """)
                with gr.Row():
                    live_ds = gr.Dropdown(
                        choices=["missing_persons", "unidentified_bodies", "stolen_vehicles"],
                        value="missing_persons",
                        label="Target Dataset"
                    )
                    live_month = gr.Textbox(
                        value="2026-11",
                        label="Target Forecast Month (YYYY-MM)"
                    )
                    live_k = gr.Slider(minimum=1, maximum=210, value=25, step=1, label="Ranked Units to Evaluate")
                    live_all = gr.Checkbox(value=False, label="Evaluate All Candidate Spatial Units (Full Universe)")
                    predict_btn = gr.Button("Run Live Model Forecast", variant="primary")

                live_summary = gr.Markdown("### Choose parameters and click 'Run Live Model Forecast'.")
                live_table = gr.Dataframe(
                    headers=["Rank", "Station Name", "District", "Probability Score", "Coordinates", "Spatial Basis"],
                    interactive=False
                )

                predict_btn.click(
                    fn=run_live_prediction,
                    inputs=[live_ds, live_month, live_k, live_all],
                    outputs=[live_summary, live_table]
                )

            # TAB 4: MODEL EVALUATION & METHODOLOGY
            with gr.TabItem("Evaluation & Methodology", id="tab_eval"):
                gr.Markdown("""
                ### Dual Evaluation & Oracle Perplexity Framework
                The Delhi Hotspots ML system is evaluated on two rigorous, independent benchmarks:
                1. **Preserved Baseline (80/20 Random Holdout)**: Historical holdout evaluation.
                2. **Strict Forward-Time (Expanding-Window Rolling Origin)**: Reserves the latest 20% of complete calendar months, strictly forecasting each test month using only past events.
                3. **Theoretical Oracle Floor**: Evaluated at **125.82** perplexity across 27 holdout months.
                """)

                gr.Markdown("#### 1. Preserved 80/20 Holdout Baseline")
                base_rows, roll_rows = get_evaluation_tables()
                gr.Dataframe(
                    headers=["Dataset", "80/20 Split (Train/Test)", "Holdout F1", "Mean Miss Distance", "Spatial Basis"],
                    value=base_rows,
                    interactive=False
                )

                gr.Markdown("#### 2. Forward-Time Rolling-Origin Evaluation (27 Complete Test Months)")
                gr.Dataframe(
                    headers=["Dataset Representation", "Test Window", "Accuracy", "F1 (Top 10%)", "Avg Precision", "Log Loss", "Perplexity", "Wasserstein W1"],
                    value=roll_rows,
                    interactive=False
                )

            # TAB 5: MCP SERVER CONNECTION & APIS
            with gr.TabItem("Model Context Protocol (MCP) Setup", id="tab_mcp"):
                gr.Markdown("""
                ### Connect AI Agents to Delhi Hotspots ML via MCP

                This Hugging Face Space functions as a **complete remote MCP Server** that can run independent related queries and live model inference on the complete datasets.

                #### 1. Claude Desktop Configuration
                Add this to your `claude_desktop_config.json`:

                ```json
                {
                  "mcpServers": {
                    "oculon_delhi_hotspots": {
                      "url": "https://abhyudaymishr-oculon.hf.space/sse"
                    }
                  }
                }
                ```

                #### 2. Available Universal MCP Tools
                - `fetch_dataset_records(dataset, data_type, month, limit, offset, filter_district, filter_station)`: Completely user-controlled fetching (any limit or 'all') for any data type.
                - `query_hotspots(dataset, month, query_text, top_k)`: Query complete datasets with user-chosen top_k.
                - `predict_hotspots(dataset, target_month, top_k)`: Run live model prediction on-the-fly for any month.
                - `query_dataset_analytics(dataset, query_type, entity_name, limit)`: Historical longitudinal aggregations.
                - `get_hotspot_map(map_type)`: Direct URLs to interactive Leaflet hotspot maps.
                - `get_model_metrics(dataset, evaluation_type)`: Dual-evaluation benchmarks and oracle perplexity floor.

                #### 3. Programmatic REST API
                - `GET /api/hotspots?dataset=missing_persons&top_k=50`
                - `GET /api/fetch_records?dataset=stolen_vehicles&data_type=all_units&limit=all`
                - `POST /api/query_hotspots` (body: `{"dataset": "unidentified_bodies", "top_k": "all"}`)
                - `POST /api/fetch_records` (body: `{"dataset": "missing_persons", "data_type": "monthly_timeline", "limit": "all"}`)
                - `POST /api/predict_hotspots` (body: `{"dataset": "missing_persons", "target_month": "2026-12", "top_k": 210}`)
                """)

    return demo


# ==============================================================================
# FastAPI Application & REST Endpoints
# ==============================================================================

app = None
if HAS_FASTAPI:
    app = FastAPI(title="Delhi Hotspots ML Server")

    # Mount static maps for direct browser navigation
    if MAPS_DIR.exists():
        app.mount("/maps", StaticFiles(directory=str(MAPS_DIR), html=True), name="maps")

    @app.get("/api/hotspots")
    async def api_hotspots(
        dataset: Optional[str] = None,
        month: Optional[str] = None,
        query: Optional[str] = None,
        top_k: Optional[str] = "all",
        data_type: str = "hotspots",
        spatial_method: str = "metro"
    ):
        if not mcp_server:
            return JSONResponse(status_code=500, content={"error": "MCP server unavailable"})
        return mcp_server.query_hotspots(
            dataset=dataset,
            month=month,
            query_text=query,
            top_k=top_k,
            spatial_method=spatial_method,
            data_type=data_type
        )

    @app.post("/api/query_hotspots")
    async def api_query_hotspots(request: Request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not mcp_server:
            return JSONResponse(status_code=500, content={"error": "MCP server unavailable"})
        return mcp_server.query_hotspots(
            dataset=body.get("dataset"),
            month=body.get("month"),
            query_text=body.get("query_text"),
            top_k=body.get("top_k", "all"),
            spatial_method=body.get("spatial_method", "metro"),
            include_related_analysis=body.get("include_related_analysis", True),
            data_type=body.get("data_type", "hotspots")
        )

    @app.get("/api/fetch_records")
    async def api_get_fetch_records(
        dataset: str = "all",
        data_type: str = "hotspots",
        month: Optional[str] = None,
        limit: Optional[str] = "all",
        offset: int = 0,
        filter_district: Optional[str] = None,
        filter_station: Optional[str] = None,
        spatial_method: str = "police"
    ):
        if not mcp_server:
            return JSONResponse(status_code=500, content={"error": "MCP server unavailable"})
        return mcp_server.fetch_dataset_records(
            dataset=dataset,
            data_type=data_type,
            month=month,
            limit=limit,
            offset=offset,
            filter_district=filter_district,
            filter_station=filter_station,
            spatial_method=spatial_method
        )

    @app.post("/api/fetch_records")
    async def api_post_fetch_records(request: Request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not mcp_server:
            return JSONResponse(status_code=500, content={"error": "MCP server unavailable"})
        return mcp_server.fetch_dataset_records(
            dataset=body.get("dataset", "all"),
            data_type=body.get("data_type", "hotspots"),
            month=body.get("month"),
            limit=body.get("limit", "all"),
            offset=int(body.get("offset", 0)),
            filter_district=body.get("filter_district"),
            filter_station=body.get("filter_station"),
            spatial_method=body.get("spatial_method", "police")
        )

    @app.post("/api/predict_hotspots")
    async def api_predict_hotspots(request: Request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not mcp_server:
            return JSONResponse(status_code=500, content={"error": "MCP server unavailable"})
        return mcp_server.predict_hotspots(
            dataset=body.get("dataset", "missing_persons"),
            target_month=body.get("target_month", "2026-11"),
            top_k=body.get("top_k", "all"),
            spatial_method=body.get("spatial_method", "police"),
            use_lgcp=bool(body.get("use_lgcp", False)),
            temper=float(body.get("temper", 0.01))
        )

    @app.post("/api/query_analytics")
    async def api_query_analytics(request: Request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not mcp_server:
            return JSONResponse(status_code=500, content={"error": "MCP server unavailable"})
        return mcp_server.query_dataset_analytics(
            dataset=body.get("dataset", "all"),
            query_type=body.get("query_type", "hotspot_persistence"),
            entity_name=body.get("entity_name"),
            start_month=body.get("start_month"),
            end_month=body.get("end_month"),
            limit=body.get("limit", "all"),
            filter_district=body.get("filter_district")
        )

    @app.get("/api/metrics")
    async def api_metrics(eval_type: str = "all"):
        if mcp_server:
            return mcp_server.get_model_metrics(evaluation_type=eval_type)
        baseline = load_dataset_comparison().get("datasets", {})
        rolling = load_rolling_origin()
        return {
            "status": "success",
            "baseline_80_20": baseline if eval_type in ("all", "baseline") else None,
            "rolling_origin": rolling if eval_type in ("all", "rolling") else None
        }

    def _get_public_base_url(req: Request) -> str:
        base = str(req.base_url).rstrip("/")
        proto = req.headers.get("x-forwarded-proto", "")
        if proto == "https" or "hf.space" in base or "huggingface.co" in base:
            base = base.replace("http://", "https://")
        return base

    # SSE endpoints for Remote Model Context Protocol (MCP) clients (both /sse and /gradio_api/mcp/sse)
    @app.api_route("/sse", methods=["GET", "HEAD", "OPTIONS"])
    @app.api_route("/gradio_api/mcp/sse", methods=["GET", "HEAD", "OPTIONS"])
    async def sse_endpoint(request: Request):
        if request.method in ("HEAD", "OPTIONS"):
            return Response(
                status_code=200,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS, POST",
                    "Access-Control-Allow-Headers": "*",
                }
            )

        session_id = str(uuid.uuid4())
        queue = asyncio.Queue()
        sse_sessions[session_id] = queue

        base_url = _get_public_base_url(request)
        msg_path = "/gradio_api/mcp/messages" if "gradio_api" in request.url.path else "/messages"
        endpoint_url = f"{base_url}{msg_path}?sessionId={session_id}"

        async def event_generator():
            try:
                yield f"event: endpoint\ndata: {endpoint_url}\n\n"
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        message = await asyncio.wait_for(queue.get(), timeout=20.0)
                        yield f"event: message\ndata: {json.dumps(message)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": keep-alive\n\n"
            finally:
                sse_sessions.pop(session_id, None)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Expose-Headers": "*",
            }
        )

    @app.api_route("/messages", methods=["POST", "OPTIONS"])
    @app.api_route("/gradio_api/mcp/messages", methods=["POST", "OPTIONS"])
    async def messages_endpoint(request: Request):
        if request.method == "OPTIONS":
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                }
            )

        session_id = request.query_params.get("sessionId")
        if not session_id or session_id not in sse_sessions:
            return JSONResponse(status_code=404, content={"error": "Session not found or expired"})

        try:
            req_body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

        base_url = _get_public_base_url(request)
        resp = handle_remote_rpc(req_body, base_url)
        if resp is not None:
            await sse_sessions[session_id].put(resp)

        return Response(
            status_code=202,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Expose-Headers": "*",
            }
        )

    # Mount Gradio Blocks inside FastAPI
    if HAS_GRADIO:
        demo = build_gradio_demo()
        if demo:
            app = gr.mount_gradio_app(app, demo, path="/")
            # Explicitly notify Hugging Face ZeroGPU host of decorated functions
            try:
                from spaces.zero import client as zero_client
                zero_client.startup_report()
                print("ZeroGPU startup_report successfully transmitted to HF host.")
            except Exception as e:
                print(f"ZeroGPU startup_report notice: {e}")


if __name__ == "__main__":
    if HAS_FASTAPI and app:
        import uvicorn
        # Hugging Face Spaces routes external traffic to port 7860.
        # If PORT is set to 7861 by ZeroGPU / internal Node SSR proxy, uvicorn must bind to 7860.
        raw_port = os.environ.get("PORT", "7860")
        port = 7860 if raw_port == "7861" else (int(raw_port) if raw_port.isdigit() else 7860)
        print(f"Starting Oculon Uvicorn server on 0.0.0.0:{port}...")
        try:
            uvicorn.run(app, host="0.0.0.0", port=port)
        except OSError as e:
            if "already in use" in str(e).lower() and port != 7860:
                print(f"Warning: Port {port} in use. Retrying on port 7860...")
                uvicorn.run(app, host="0.0.0.0", port=7860)
            else:
                raise
    elif HAS_GRADIO:
        demo = build_gradio_demo()
        if demo:
            demo.launch(server_name="0.0.0.0", server_port=7860)
