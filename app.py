#!/usr/bin/env python3
"""
Delhi Hotspots ML - Hugging Face Space Application
--------------------------------------------------
Interactive Spatiotemporal Crime Hotspot Explorer & Model Context Protocol (MCP) Server.
Combines:
1. Gradio Web Interface with embedded maps, query tools, and live model prediction.
2. Direct static map hosting under /maps/.
3. Programmatic REST API under /api/.
4. Remote MCP SSE server under /sse and /messages for Claude, Cursor, and AI agents.
"""

import os
import sys
import json
import csv
import uuid
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

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

# ZeroGPU compatibility for Hugging Face Spaces (required if zero-a10g hardware is selected)
try:
    import spaces
    @spaces.GPU
    def _zero_gpu_init():
        return True
    _zero_gpu_init()
except Exception:
    pass

# Directories
BASE_DIR = Path(__file__).resolve().parent
MAPS_DIR = BASE_DIR / "maps" if (BASE_DIR / "maps").exists() else BASE_DIR / "src" / "oculon" / "maps"
DATA_DIR = BASE_DIR / "data" if (BASE_DIR / "data").exists() else BASE_DIR / "src" / "oculon" / "data"

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

def load_forecasts() -> List[Dict[str, Any]]:
    if mcp_server:
        return mcp_server.load_forecasts()
    if not FORECAST_CSV.exists():
        return []
    rows = []
    with open(FORECAST_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
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

    if name == "query_hotspots":
        res = mcp_server.query_hotspots(
            dataset=args.get("dataset"),
            month=args.get("month"),
            query_text=args.get("query_text"),
            top_k=int(args.get("top_k", 7)),
            spatial_method=args.get("spatial_method", "metro"),
            include_related_analysis=args.get("include_related_analysis", True)
        )
        res["hosted_map_url"] = f"{base_url}/maps/four_dataset_hotspot_explorer.html"
        return res

    elif name == "predict_hotspots":
        res = mcp_server.predict_hotspots(
            dataset=args.get("dataset", "missing_persons"),
            target_month=args.get("target_month", "2026-11"),
            top_k=int(args.get("top_k", 10)),
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
            end_month=args.get("end_month")
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
            "browser_map_url": map_url,
            "html_link": f'<a href="{map_url}" target="_blank">Open {map_type} map in browser</a>',
            "message": f"Interactive hotspot map available at: {map_url}. Open this URL directly in your browser."
        }

    elif name == "get_model_metrics":
        eval_type = args.get("evaluation_type", "all")
        return mcp_server.get_model_metrics(dataset=args.get("dataset"), evaluation_type=eval_type)

    elif name == "list_datasets_and_months":
        res = mcp_server.list_datasets_and_months()
        res["hugging_face_connection"]["space_url"] = base_url
        res["hugging_face_connection"]["remote_mcp_sse_endpoint"] = f"{base_url}/sse"
        return res

    else:
        raise ValueError(f"Unknown tool: {name}")


def handle_rpc_message(req: Dict[str, Any], base_url: str) -> Optional[Dict[str, Any]]:
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
                    "name": "delhi-hotspots-ml-hf-space",
                    "version": "1.0.0"
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
        if uri == "delhi://hotspots/forecast/top7":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(load_forecasts(), indent=2)}]}
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
    "🌐 Unified 4-Dataset Spatiotemporal Explorer": "four_dataset_hotspot_explorer.html",
    "🚗 Stolen Vehicles Map (Metro & PIN)": "stolen_vehicles_map.html",
    "👤 Missing Persons Map (Station Proxies)": "missing_persons_map.html",
    "📱 Missing Mobiles & ⚰️ Unidentified Bodies": "mobiles_and_bodies_map.html"
}

def get_map_iframe(selected_label: str) -> str:
    filename = MAP_OPTIONS.get(selected_label, "four_dataset_hotspot_explorer.html")
    map_url = f"/maps/{filename}"
    return f"""
    <div style="margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; background: #f8fafc; padding: 12px 16px; border-radius: 8px; border: 1px solid #e2e8f0;">
        <span style="font-weight: 600; color: #1e293b;">Active Map: <code style="color: #2563eb;">{filename}</code></span>
        <a href="{map_url}" target="_blank" style="display: inline-flex; align-items: center; gap: 6px; background-color: #2563eb; color: white; text-decoration: none; font-weight: 600; padding: 8px 16px; border-radius: 6px; font-size: 14px; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#1d4ed8'" onmouseout="this.style.backgroundColor='#2563eb'">
            🚀 Open Map in Fullscreen Browser Tab &rarr;
        </a>
    </div>
    <iframe src="{map_url}" style="width: 100%; height: 780px; border: 1px solid #cbd5e1; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);" title="Delhi Hotspots Map"></iframe>
    """


def search_hotspots(dataset: str, month: str, query_text: str):
    if not mcp_server:
        return "MCP server not initialized", [], "{}"
    res = mcp_server.query_hotspots(
        dataset=dataset if dataset != "All Datasets" else None,
        month=month if month != "All Months" else None,
        query_text=query_text,
        top_k=10
    )
    hotspots = res.get("hotspots", [])
    if not hotspots:
        return (
            "### No matching hotspots found\nTry broadening your search or selecting 'All Datasets'.",
            [],
            "{}"
        )

    table_data = []
    for r in hotspots:
        score_val = r.get("relative_multigram_score")
        score_str = f"{float(score_val):.6f}" if score_val else "N/A"
        table_data.append([
            res.get("dataset", dataset),
            str(r.get("rank") or "N/A"),
            res.get("target_month", month),
            r.get("name") or r.get("station_id"),
            r.get("district") or "N/A",
            r.get("spatial_representation") or "proxy",
            score_str,
            str(r.get("incident_count", 0)),
            r.get("classification") or "forecast"
        ])

    related = res.get("related_independent_analysis", {})
    related_json = json.dumps(related, indent=2)

    summary_md = f"### Found **{len(hotspots)}** hotspot locations for **{res.get('target_month')}** ({res.get('dataset')})\n"
    summary_md += f"- **Citywide Total Events**: {related.get('citywide_monthly_events', 'N/A'):,} (Ratio vs 12m Median: {related.get('volume_vs_median_ratio', 'N/A')}x)\n"
    summary_md += f"- **Hotspot Entropy**: {related.get('predictive_entropy_nats', 'N/A')} nats &bull; **Effective Dispersion**: {related.get('effective_hotspot_dispersion_units', 'N/A')} units\n"
    return summary_md, table_data, related_json


def run_live_prediction(dataset: str, target_month: str, top_k: int):
    if not mcp_server:
        return "MCP Server not initialized", []
    res = mcp_server.predict_hotspots(
        dataset=dataset,
        target_month=target_month,
        top_k=int(top_k)
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

    summary = f"### Live On-The-Fly Forecast for **{target_month}** ({dataset})\n"
    summary += f"- **History Used**: {res.get('history_events_used', 'N/A'):,} dated records up to `{res.get('history_cutoff_date')}`\n"
    summary += f"- **Predictive Perplexity**: **{res.get('predictive_perplexity')}** (Entropy: {res.get('predictive_entropy_nats')} nats)\n"
    return summary, table


def get_evaluation_tables():
    baseline_rows = [
        ["Missing persons", "83,388 / 20,847", "0.395", "3.21 km", "Police-station reporting proxy"],
        ["Unidentified bodies", "7,914 / 1,978", "0.446", "2.69 km", "Police-station reference proxy"],
        ["Stolen vehicles (Metro)", "21,082 / 5,270", "0.450", "4.82 km", "Nearest metro station"],
        ["Stolen vehicles (PIN)", "21,082 / 5,270", "0.372", "6.24 km", "Postal PIN centroid"],
        ["Missing mobiles", "1,282 / 320", "N/A", "N/A", "No physical event location in source"]
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
                    <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #f8fafc;">👁️ Oculon: Delhi Hotspots ML Explorer</h1>
                    <p style="margin: 6px 0 0 0; color: #94a3b8; font-size: 15px;">
                        Spatiotemporal crime & safety hotspot forecasting for Delhi &bull; Hugging Face Space: <code>AbhyudayMishr/Oculon</code>
                    </p>
                </div>
                <div style="display: flex; gap: 8px;">
                    <span style="background: #2563eb; color: white; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 9999px;">Gradio UI</span>
                    <span style="background: #10b981; color: white; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 9999px;">Complete Datasets MCP</span>
                    <span style="background: #f59e0b; color: white; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 9999px;">Live Model Running</span>
                </div>
            </div>
            <div style="display: flex; gap: 16px; margin-top: 14px; flex-wrap: wrap; font-size: 13px; color: #cbd5e1;">
                <span>🔵 <b>Missing Persons</b> (104,235 events &bull; 210 Stations)</span>
                <span>🟣 <b>Unidentified Bodies</b> (9,892 events &bull; 210 Stations)</span>
                <span>🔴 <b>Stolen Vehicles</b> (26,352 events &bull; 247 Metro / 124 PIN)</span>
                <span>🟡 <b>Missing Mobiles</b> (1,602 events &bull; Virtual eTheft)</span>
            </div>
        </div>
        """)

        with gr.Tabs():
            # TAB 1: MAP EXPLORER
            with gr.TabItem("🗺️ Interactive Hotspots Map", id="tab_map"):
                with gr.Row():
                    map_selector = gr.Radio(
                        choices=list(MAP_OPTIONS.keys()),
                        value="🌐 Unified 4-Dataset Spatiotemporal Explorer",
                        label="Choose Interactive Map Visualization",
                        interactive=True
                    )

                map_frame = gr.HTML(value=get_map_iframe("🌐 Unified 4-Dataset Spatiotemporal Explorer"))
                map_selector.change(fn=get_map_iframe, inputs=[map_selector], outputs=[map_frame])

            # TAB 2: QUERY HOTSPOTS
            with gr.TabItem("🔍 Complete Dataset Hotspots Query", id="tab_query"):
                gr.Markdown("""
                Search hotspot rankings and probabilities across the complete multi-year dataset with **automatic independent related analysis** (persistence, cross-crime correlation, entropy).
                """)
                with gr.Row():
                    query_input = gr.Textbox(
                        value="Bawana",
                        label="Natural Query / Keywords",
                        placeholder="e.g. Bawana, Kashmere Gate, Rohini, top hotspots"
                    )
                    dataset_dropdown = gr.Dropdown(
                        choices=["All Datasets", "Missing persons", "Unidentified bodies", "Stolen vehicles", "Missing mobiles"],
                        value="Missing persons",
                        label="Dataset Filter"
                    )
                    month_dropdown = gr.Dropdown(
                        choices=["2026-10", "2026-09", "2026-08", "2025-06", "2025-01", "2024-11", "2024-06", "All Months"],
                        value="2026-10",
                        label="Month"
                    )
                    search_btn = gr.Button("🔍 Query Complete Dataset", variant="primary")

                query_summary = gr.Markdown("### Click 'Query Complete Dataset' to view rankings.")
                results_table = gr.Dataframe(
                    headers=["Dataset", "Rank", "Month", "Location Proxy", "District", "Spatial Method", "Model Score", "Incident Count", "Classification"],
                    datatype=["str", "str", "str", "str", "str", "str", "str", "str", "str"],
                    interactive=False
                )

                gr.Markdown("#### 📈 Independent Related Intelligence (Executed Automatically)")
                related_output = gr.Code(language="json", label="Independent Related Spatiotemporal Analysis (Complete Store)")

                search_btn.click(
                    fn=search_hotspots,
                    inputs=[dataset_dropdown, month_dropdown, query_input],
                    outputs=[query_summary, results_table, related_output]
                )

            # TAB 3: LIVE MODEL INFERENCE
            with gr.TabItem("⚡ Live Model Prediction Engine", id="tab_live"):
                gr.Markdown("""
                ### On-The-Fly Model Execution
                Run the spatial multigram and temporal forecasting model dynamically for **any future or past month** using the complete historical event stream.
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
                    live_k = gr.Slider(minimum=3, maximum=25, value=10, step=1, label="Top K Hotspots")
                    predict_btn = gr.Button("⚡ Run Live Model Forecast", variant="primary")

                live_summary = gr.Markdown("### Choose a dataset and month, then click 'Run Live Model Forecast'.")
                live_table = gr.Dataframe(
                    headers=["Rank", "Station Name", "District", "Probability Score", "Coordinates", "Spatial Basis"],
                    interactive=False
                )

                predict_btn.click(
                    fn=run_live_prediction,
                    inputs=[live_ds, live_month, live_k],
                    outputs=[live_summary, live_table]
                )

            # TAB 4: MODEL EVALUATION & METHODOLOGY
            with gr.TabItem("📊 Evaluation & Methodology", id="tab_eval"):
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
                    headers=["Dataset", "80/20 Split (Train/Test)", "Holdout F1", "Mean Proxy Miss Distance", "Spatial Unit Basis"],
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
            with gr.TabItem("🔌 Model Context Protocol (MCP) Setup", id="tab_mcp"):
                gr.Markdown("""
                ### Connect AI Agents to Delhi Hotspots ML via MCP

                This Hugging Face Space functions as a **complete remote MCP Server** that can run independent related queries and live model inference on the complete datasets.

                #### 1. Claude Desktop Configuration
                Add this to your `claude_desktop_config.json` (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

                ```json
                {
                  "mcpServers": {
                    "oculon_delhi_hotspots": {
                      "url": "https://abhyudaymishr-oculon.hf.space/sse"
                    }
                  }
                }
                ```

                #### 2. Available Tools on Remote & Local MCP
                - `query_hotspots(dataset, month, query_text, top_k)`: Query complete datasets with automatic independent related analysis.
                - `predict_hotspots(dataset, target_month, top_k)`: Run live model prediction on-the-fly for any month.
                - `query_dataset_analytics(dataset, query_type, entity_name)`: Multi-year aggregations (persistence, station profiles, district summaries).
                - `get_hotspot_map(map_type)`: Return direct URL to open interactive maps.
                - `get_model_metrics(dataset, evaluation_type)`: Retrieve baseline, rolling-origin, and oracle perplexity bounds.
                - `list_datasets_and_months()`: List datasets, spatial properties, and map links.
                """)

    return demo


# ==============================================================================
# FastAPI Backend Integration
# ==============================================================================

app = None
if HAS_FASTAPI:
    app = FastAPI(title="Delhi Hotspots ML Server")

    # Mount static maps for direct browser navigation
    if MAPS_DIR.exists():
        app.mount("/maps", StaticFiles(directory=str(MAPS_DIR), html=True), name="maps")

    @app.get("/api/hotspots")
    async def api_hotspots(dataset: Optional[str] = None, month: Optional[str] = None, query: Optional[str] = None, top_k: int = 7):
        if not mcp_server:
            return JSONResponse(status_code=500, content={"error": "MCP server unavailable"})
        return mcp_server.query_hotspots(dataset=dataset, month=month, query_text=query, top_k=top_k)

    @app.post("/api/query_hotspots")
    async def api_query_hotspots(request: Request):
        try:
            body = await request.json()
        except:
            body = {}
        if not mcp_server:
            return JSONResponse(status_code=500, content={"error": "MCP server unavailable"})
        res = mcp_server.query_hotspots(
            dataset=body.get("dataset"),
            month=body.get("month"),
            query_text=body.get("query_text"),
            top_k=int(body.get("top_k", 7)),
            spatial_method=body.get("spatial_method", "metro"),
            include_related_analysis=body.get("include_related_analysis", True)
        )
        return res

    @app.post("/api/predict_hotspots")
    async def api_predict_hotspots(request: Request):
        try:
            body = await request.json()
        except:
            body = {}
        if not mcp_server:
            return JSONResponse(status_code=500, content={"error": "MCP server unavailable"})
        res = mcp_server.predict_hotspots(
            dataset=body.get("dataset", "missing_persons"),
            target_month=body.get("target_month", "2026-11"),
            top_k=int(body.get("top_k", 10)),
            spatial_method=body.get("spatial_method", "police"),
            use_lgcp=bool(body.get("use_lgcp", False)),
            temper=float(body.get("temper", 0.01))
        )
        return res

    @app.post("/api/query_analytics")
    async def api_query_analytics(request: Request):
        try:
            body = await request.json()
        except:
            body = {}
        if not mcp_server:
            return JSONResponse(status_code=500, content={"error": "MCP server unavailable"})
        res = mcp_server.query_dataset_analytics(
            dataset=body.get("dataset", "all"),
            query_type=body.get("query_type", "hotspot_persistence"),
            entity_name=body.get("entity_name"),
            start_month=body.get("start_month"),
            end_month=body.get("end_month")
        )
        return res

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

    @app.get("/api/maps")
    async def api_maps():
        return {
            "four_dataset_explorer": "/maps/four_dataset_hotspot_explorer.html",
            "missing_persons": "/maps/missing_persons_map.html",
            "stolen_vehicles": "/maps/stolen_vehicles_map.html",
            "mobiles_and_bodies": "/maps/mobiles_and_bodies_map.html"
        }

    # MCP SSE Transport Endpoints
    @app.get("/sse")
    async def mcp_sse(request: Request):
        session_id = str(uuid.uuid4())
        queue: asyncio.Queue = asyncio.Queue()
        sse_sessions[session_id] = queue

        forwarded_proto = request.headers.get("x-forwarded-proto", "https" if request.url.scheme == "https" else "http")
        host = request.headers.get("host", request.url.netloc)
        base_url = f"{forwarded_proto}://{host}"

        async def event_generator():
            endpoint_url = f"/messages?session_id={session_id}"
            yield f"event: endpoint\ndata: {endpoint_url}\n\n"

            try:
                while True:
                    msg = await queue.get()
                    yield f"event: message\ndata: {json.dumps(msg)}\n\n"
            except asyncio.CancelledError:
                pass
            finally:
                sse_sessions.pop(session_id, None)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    @app.post("/messages")
    async def mcp_messages(request: Request, session_id: Optional[str] = None):
        try:
            body = await request.json()
        except Exception as e:
            return JSONResponse(status_code=400, content={"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}})

        forwarded_proto = request.headers.get("x-forwarded-proto", "https" if request.url.scheme == "https" else "http")
        host = request.headers.get("host", request.url.netloc)
        base_url = f"{forwarded_proto}://{host}"

        response_payload = handle_rpc_message(body, base_url)

        if session_id and session_id in sse_sessions and response_payload:
            await sse_sessions[session_id].put(response_payload)
            return Response(status_code=202, content="Accepted")

        return JSONResponse(content=response_payload)

    # Mount Gradio app onto FastAPI with ssr_mode=False
    demo = build_gradio_demo()
    if HAS_GRADIO and demo:
        try:
            app = gr.mount_gradio_app(app, demo, path="/", ssr_mode=False)
        except TypeError:
            app = gr.mount_gradio_app(app, demo, path="/")


def main():
    if HAS_FASTAPI:
        import uvicorn
        port = int(os.environ.get("PORT", 7860))
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        print("FastAPI and Gradio are required to run the web server. Install via: pip install -r requirements.txt")


if __name__ == "__main__":
    main()
