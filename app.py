#!/usr/bin/env python3
"""
Delhi Hotspots ML - Hugging Face Space Application
--------------------------------------------------
Interactive Spatiotemporal Crime Hotspot Explorer & Model Context Protocol (MCP) Server.
Combines:
1. Gradio Web Interface with embedded maps, query tools, and browser-launch links.
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


# Directories
BASE_DIR = Path(__file__).resolve().parent
MAPS_DIR = BASE_DIR / "maps"
DATA_DIR = BASE_DIR / "data"

FORECAST_CSV = DATA_DIR / "four_dataset_forecast_top_seven.csv"
COMPARISON_JSON = DATA_DIR / "dataset_comparison.json"
ROLLING_JSON = DATA_DIR / "rolling_origin_summary.json"
CONFIG_JSON = DATA_DIR / "model_config.json"


# ==============================================================================
# Data Loading Utilities
# ==============================================================================

def load_forecasts() -> List[Dict[str, Any]]:
    if not FORECAST_CSV.exists():
        return []
    rows = []
    with open(FORECAST_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def load_dataset_comparison() -> Dict[str, Any]:
    if not COMPARISON_JSON.exists():
        return {}
    with open(COMPARISON_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def load_rolling_origin() -> Dict[str, Any]:
    if not ROLLING_JSON.exists():
        return {}
    with open(ROLLING_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def query_hotspots_logic(dataset: Optional[str] = None, month: Optional[str] = None, query_text: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = load_forecasts()
    ds_filter = None
    if dataset and dataset != "All Datasets":
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

    results = []
    for r in rows:
        if ds_filter and ds_filter.lower() not in r.get("dataset", "").lower():
            continue
        if month and month != "All Months" and month != r.get("forecast_month", ""):
            continue
        results.append(r)
    return results


# ==============================================================================
# Model Context Protocol (MCP) Logic
# ==============================================================================

MCP_TOOLS = [
    {
        "name": "query_hotspots",
        "description": "Query top forecast hotspots for Delhi crime and public safety datasets (Missing Persons, Unidentified Dead Bodies, Stolen Vehicles, Missing Mobiles).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "description": "Dataset identifier: 'missing_persons', 'unidentified_bodies', 'stolen_vehicles', or 'missing_mobiles'."
                },
                "month": {
                    "type": "string",
                    "description": "Target forecast month in YYYY-MM format (e.g. '2026-10')."
                },
                "query_text": {
                    "type": "string",
                    "description": "Natural search query such as 'top hotspots stolen vehicles 2026-10'."
                }
            }
        }
    },
    {
        "name": "get_hotspot_map",
        "description": "Get direct browser-openable URLs and resources for interactive spatiotemporal hotspot maps of Delhi.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "map_type": {
                    "type": "string",
                    "enum": ["four_dataset_explorer", "missing_persons", "stolen_vehicles", "mobiles_and_bodies"],
                    "default": "four_dataset_explorer",
                    "description": "Which interactive map to retrieve."
                }
            }
        }
    },
    {
        "name": "get_model_metrics",
        "description": "Get evaluation metrics: baseline 80/20 holdout vs strict forward-time rolling-origin evaluation (Accuracy, F1, Log Loss, Brier score sum, Wasserstein W1 distance).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "description": "Dataset name or 'all'."
                },
                "evaluation_type": {
                    "type": "string",
                    "enum": ["all", "baseline", "rolling"],
                    "default": "all",
                    "description": "Type of metrics: 'baseline', 'rolling', or 'all'."
                }
            }
        }
    },
    {
        "name": "list_datasets_and_months",
        "description": "List all monitored datasets, spatial representations, latest forecast months, and map links.",
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
        "description": "Summary of rolling-origin temporal evaluation metrics."
    }
]


def execute_mcp_tool(name: str, args: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    if name == "query_hotspots":
        matches = query_hotspots_logic(
            dataset=args.get("dataset"),
            month=args.get("month"),
            query_text=args.get("query_text")
        )
        items = []
        for r in matches:
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
        map_url = f"{base_url}/maps/four_dataset_hotspot_explorer.html"
        return {
            "status": "success",
            "count": len(items),
            "results": items,
            "browser_map_url": map_url,
            "browser_instruction": f"Open this link in your browser to inspect interactive layers: {map_url}",
            "note": "Proxy locations (police stations, PIN centroids, metro stations) are used; no person-level records."
        }

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
        baseline = load_dataset_comparison().get("datasets", {})
        rolling = load_rolling_origin()
        return {
            "status": "success",
            "baseline_80_20": baseline if eval_type in ("all", "baseline") else None,
            "rolling_origin_forward_time": rolling if eval_type in ("all", "rolling") else None
        }

    elif name == "list_datasets_and_months":
        return {
            "datasets": [
                {"id": "missing_persons", "name": "Missing Persons", "color": "#2864b7", "proxy": "Police station", "spatial": True},
                {"id": "unidentified_bodies", "name": "Unidentified Dead Bodies", "color": "#8c4bb8", "proxy": "Police station", "spatial": True},
                {"id": "stolen_vehicles", "name": "Stolen Vehicles", "color": "#c74440", "proxy": "PIN centroid / Metro station", "spatial": True},
                {"id": "missing_mobiles", "name": "Missing Mobiles", "color": "#d58a13", "proxy": "None (non-spatial)", "spatial": False}
            ],
            "maps": [
                {"id": "four_dataset_explorer", "url": f"{base_url}/maps/four_dataset_hotspot_explorer.html"},
                {"id": "missing_persons", "url": f"{base_url}/maps/missing_persons_map.html"},
                {"id": "stolen_vehicles", "url": f"{base_url}/maps/stolen_vehicles_map.html"},
                {"id": "mobiles_and_bodies", "url": f"{base_url}/maps/mobiles_and_bodies_map.html"}
            ]
        }
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
    matches = query_hotspots_logic(dataset, month, query_text)
    if not matches:
        return (
            "### No matching hotspots found\nTry broadening your search or selecting 'All Datasets'.",
            []
        )

    # Format table
    table_data = []
    for r in matches:
        score_val = r.get("relative_model_score")
        try:
            score_str = f"{float(score_val):.4f}" if score_val else "N/A"
        except:
            score_str = str(score_val)

        table_data.append([
            r.get("dataset"),
            r.get("rank") or "N/A",
            r.get("forecast_month"),
            r.get("location"),
            r.get("district") or "N/A",
            r.get("method") or "proxy",
            score_str,
            r.get("location_confidence") or "approximate proxy"
        ])

    summary_md = f"### Found **{len(matches)}** hotspot records\n"
    summary_md += "> **Note on Spatial Coordinates:** Locations represent administrative proxy centers (police station points, postal PIN centroids, or nearest metro stations). Missing mobile records lack physical coordinates."
    return summary_md, table_data


def get_evaluation_tables():
    # Baseline table
    baseline_rows = [
        ["Missing persons", "83,388 / 20,847", "0.395", "3.21 km", "Police-station reporting proxy"],
        ["Unidentified bodies", "7,914 / 1,978", "0.446", "2.69 km", "Police-station reference proxy"],
        ["Stolen vehicles (Metro)", "21,082 / 5,270", "0.450", "4.82 km", "Nearest metro station"],
        ["Stolen vehicles (PIN)", "21,082 / 5,270", "0.372", "6.24 km", "Postal PIN centroid"],
        ["Missing mobiles", "1,282 / 320", "N/A", "N/A", "No physical event location in source"]
    ]

    # Rolling origin table
    rolling_rows = [
        ["Missing persons", "27 (2024-06 to 2026-08)", "0.9210", "0.5234", "0.5372", "4.9907", "0.00286", "1.23 km"],
        ["Unidentified bodies", "11 (2025-10 to 2026-08)", "0.9628", "0.5169", "0.5493", "4.7368", "0.02189", "2.10 km"],
        ["Stolen vehicles (PIN)", "17 (2025-04 to 2026-08)", "0.9436", "0.5727", "0.6354", "4.0215", "0.01202", "2.00 km"],
        ["Stolen vehicles (Metro)", "17 (2025-04 to 2026-08)", "0.9777", "0.5149", "0.6436", "3.9023", "0.01283", "1.69 km"]
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
                    <span style="background: #10b981; color: white; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 9999px;">MCP Server Ready</span>
                    <span style="background: #f59e0b; color: white; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 9999px;">Privacy Preserved</span>
                </div>
            </div>
            <div style="display: flex; gap: 16px; margin-top: 14px; flex-wrap: wrap; font-size: 13px; color: #cbd5e1;">
                <span>🔵 <b>Missing Persons</b> (Station Proxy)</span>
                <span>🟣 <b>Unidentified Bodies</b> (Station Proxy)</span>
                <span>🔴 <b>Stolen Vehicles</b> (Metro / PIN)</span>
                <span>🟡 <b>Missing Mobiles</b> (Non-Spatial)</span>
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
            with gr.TabItem("🔍 Hotspots Forecast Query", id="tab_query"):
                gr.Markdown("""
                Search next-month predicted hotspot rankings and probabilities.
                You can type natural language queries like `top hotspots stolen vehicles 2026-10` or use the structured filters below.
                """)
                with gr.Row():
                    query_input = gr.Textbox(
                        value="top hotspots",
                        label="Natural Query / Keywords",
                        placeholder="e.g. top hotspots stolen vehicles, top hotspots missing persons"
                    )
                    dataset_dropdown = gr.Dropdown(
                        choices=["All Datasets", "Missing persons", "Unidentified bodies", "Stolen vehicles", "Missing mobiles"],
                        value="All Datasets",
                        label="Dataset Filter"
                    )
                    month_dropdown = gr.Dropdown(
                        choices=["All Months", "2026-10"],
                        value="2026-10",
                        label="Forecast Month"
                    )
                    search_btn = gr.Button("🔍 Search Hotspots", variant="primary")

                query_summary = gr.Markdown("### Click 'Search Hotspots' to view rankings.")
                results_table = gr.Dataframe(
                    headers=["Dataset", "Rank", "Month", "Location Proxy", "District", "Spatial Method", "Model Score", "Confidence"],
                    datatype=["str", "str", "str", "str", "str", "str", "str", "str"],
                    interactive=False
                )

                # Auto-run initial query
                search_btn.click(
                    fn=search_hotspots,
                    inputs=[dataset_dropdown, month_dropdown, query_input],
                    outputs=[query_summary, results_table]
                )

            # TAB 3: MODEL EVALUATION & METHODOLOGY
            with gr.TabItem("📊 Evaluation & Methodology", id="tab_eval"):
                gr.Markdown("""
                ### Dual Evaluation Framework
                The Delhi Hotspots ML system is evaluated on two rigorous, independent benchmarks:
                1. **Preserved Baseline (80/20 Random Holdout)**: Historical holdout evaluation.
                2. **Strict Forward-Time (Expanding-Window Rolling Origin)**: Reserves the latest 20% of complete calendar months, strictly forecasting each test month using only past events.
                """)

                gr.Markdown("#### 1. Preserved 80/20 Holdout Baseline")
                base_rows, roll_rows = get_evaluation_tables()
                gr.Dataframe(
                    headers=["Dataset", "80/20 Split (Train/Test)", "Holdout F1", "Mean Proxy Miss Distance", "Spatial Unit Basis"],
                    value=base_rows,
                    interactive=False
                )

                gr.Markdown("#### 2. Forward-Time Rolling-Origin Evaluation (Complete Months)")
                gr.Dataframe(
                    headers=["Dataset Representation", "Test Months", "Accuracy", "F1 (Top 10%)", "Avg Precision", "Log Loss", "Brier Score", "Wasserstein W1"],
                    value=roll_rows,
                    interactive=False
                )

                gr.Markdown("""
                > [!IMPORTANT]
                > **Privacy & Proxy Safeguards:**
                > - No person-level data (names, phone numbers, exact residential addresses) is stored or served.
                > - Incident locations are administrative aggregations (police stations, PIN centroids, or nearest metro stops).
                > - Missing mobiles are non-spatial because mobile theft reports contain no physical coordinates.
                """)

            # TAB 4: MCP SERVER CONNECTION & APIS
            with gr.TabItem("🔌 Model Context Protocol (MCP) Setup", id="tab_mcp"):
                gr.Markdown("""
                ### Connect AI Agents to Delhi Hotspots ML via MCP

                This Hugging Face Space functions as a **remote MCP Server** and offers local client integration.
                AI assistants (like Claude Desktop, Cursor, or custom agents) can query hotspot predictions and retrieve browser-openable map links.

                ---

                #### How Browser Opening Works
                - **Remote MCP (Hugging Face)**: When an AI agent calls `get_hotspot_map` or `query_hotspots`, the server returns direct links (`https://<space-url>/maps/...`). The user or client can open these links in any browser.
                - **Local Stdio Bridge**: When running the MCP server locally with `python -m src.delhi_hotspots.mcp_server`, calling `get_hotspot_map(open_in_browser=True)` automatically triggers Python's `webbrowser.open()`, launching the user's default browser directly!

                ---

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

                *Or run locally via stdio bridge:*
                ```json
                {
                  "mcpServers": {
                    "oculon_delhi_hotspots_local": {
                      "command": "python",
                      "args": ["-m", "src.delhi_hotspots.mcp_server"],
                      "cwd": "/path/to/DelhiHotspots_ML"
                    }
                  }
                }
                ```

                ---

                #### 2. Cursor MCP Configuration
                In Cursor Settings &rarr; Features &rarr; MCP Servers &rarr; Add New Server:
                - **Name**: `oculon_delhi_hotspots`
                - **Type**: `SSE`
                - **URL**: `https://abhyudaymishr-oculon.hf.space/sse`

                ---

                #### 3. Available MCP Tools
                - `query_hotspots(dataset, month, query_text)`: Query top-7 forecast hotspots with scores, coordinates, and browser links.
                - `get_hotspot_map(map_type)`: Return direct URL to open the interactive map in the browser.
                - `get_model_metrics(dataset, evaluation_type)`: Retrieve baseline and rolling-origin evaluation scores.
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
    async def api_hotspots(dataset: Optional[str] = None, month: Optional[str] = None, query: Optional[str] = None):
        results = query_hotspots_logic(dataset=dataset, month=month, query_text=query)
        return {
            "status": "success",
            "count": len(results),
            "results": results,
            "map_url": "/maps/four_dataset_hotspot_explorer.html"
        }

    @app.get("/api/metrics")
    async def api_metrics(eval_type: str = "all"):
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

    # Mount Gradio app onto FastAPI with ssr_mode=False to prevent port 7861 SSR collisions
    demo = build_gradio_demo()
    if HAS_GRADIO and demo:
        try:
            app = gr.mount_gradio_app(app, demo, path="/", ssr_mode=False)
        except TypeError:
            app = gr.mount_gradio_app(app, demo, path="/")


if __name__ == "__main__":
    if HAS_FASTAPI:
        import uvicorn
        port = int(os.environ.get("PORT", 7860))
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        print("FastAPI and Gradio are required to run the web server. Install via: pip install -r requirements.txt")

