---
title: Oculon - Delhi Hotspots ML Explorer & MCP Server
emoji: 👁️
colorFrom: blue
colorTo: red
sdk: gradio
sdk_version: 5.20.0
app_file: app.py
pinned: false
license: mit
short_description: Delhi hotspot forecasting via MCP & Gradio
---

# 👁️ Oculon: Delhi Hotspots ML Explorer & MCP Server

An interactive, multi-dataset spatial-temporal hotspot forecasting service and **Model Context Protocol (MCP)** server for Delhi crime and public safety data, hosted on Hugging Face Spaces at **`AbhyudayMishr/Oculon`**.

[![PyPI version](https://img.shields.io/pypi/v/oculon.svg)](https://pypi.org/project/oculon/)
[![Gradio](https://img.shields.io/badge/UI-Gradio%205-orange.svg)](https://gradio.app/)
[![MCP Ready](https://img.shields.io/badge/MCP-Server%20Ready-blue.svg)](https://modelcontextprotocol.io/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![Privacy Compliant](https://img.shields.io/badge/Data-Privacy%20Preserved-yellow.svg)](#privacy-guarantees)

---

## 🌟 Features

1. **4 Monitored Datasets with Independent Timelines**:
   - 🔵 **Missing Persons**: Police station proxy coordinates.
   - 🟣 **Unidentified Dead Bodies**: Police station proxy coordinates.
   - 🔴 **Stolen Vehicles**: Approximate postal PIN centroids & nearest Metro station units.
   - 🟡 **Missing Mobiles**: Non-spatial temporal trends (no physical coordinates in source).

2. **Interactive Map Explorer with Direct Browser Opening**:
   - Explore historical observations, predictions, and upcoming month forecasts.
   - Includes full-featured SVG layers: administrative boundaries, metro lines, railway lines, and primary road networks.
   - Dedicated action button: **🚀 Open Map in Fullscreen Browser Tab** to view maps without iframe constraints.

3. **Dual Rigorous Benchmark Evaluation**:
   - **Baseline 80/20 Random Holdout**: Historical holdout F1 and symmetric miss distance.
   - **Strict Forward-Time (Expanding-Window Rolling Origin)**: Reserves the latest 20% of complete calendar months, scoring each target month using only strictly prior events. Evaluates Multiclass Log Loss, Brier score sum, and Wasserstein $W_1$ distance.

4. **Model Context Protocol (MCP) Server**:
   - Connect LLM agents (Claude Desktop, Cursor, Antigravity, custom agents) over standard MCP SSE (`/sse` and `/messages`).
   - Query hotspots, fetch model metrics, and retrieve browser-openable map links directly into agent conversations.

---

## 🚀 How to Run Guide

### Method 1: Instant Cloud Access (No Setup Required)
- **Live Interactive Web App**: [https://abhyudaymishr-oculon.hf.space](https://abhyudaymishr-oculon.hf.space)
- **Hugging Face Space**: [https://huggingface.co/spaces/AbhyudayMishr/Oculon](https://huggingface.co/spaces/AbhyudayMishr/Oculon)
- **Standalone Interactive Map**: [https://abhyudaymishr-oculon.hf.space/maps/four_dataset_hotspot_explorer.html](https://abhyudaymishr-oculon.hf.space/maps/four_dataset_hotspot_explorer.html)

---

### Method 2: Install via `pip` (PyPI)

You can install `oculon` directly from PyPI into any Python environment:

```bash
pip install oculon
```

Or install directly from GitHub:
```bash
pip install git+https://github.com/abhyudaymishr/bob-ai-hackathon-oculon.git
```

Or for editable development:
```bash
git clone https://github.com/abhyudaymishr/bob-ai-hackathon-oculon.git
cd bob-ai-hackathon-oculon
pip install -e .
```

#### CLI Commands Available Out of the Box:
- **`oculon`** / **`oculon-mcp`**: Run the stdio Model Context Protocol (MCP) server directly (for Claude Desktop, Cursor, Antigravity, BoB, etc.):
  ```bash
  oculon
  ```
  *(or `python -m oculon`)*
- **`oculon-app`**: Launch the local Gradio + FastAPI interactive web dashboard and map server:
  ```bash
  oculon-app
  ```

#### Programmatic Python Usage:
```python
import oculon

# Query top hotspots for a dataset and month
hotspots = oculon.query_hotspots("missing_persons", "2026-04", top_k=5)
print(hotspots)

# Retrieve interactive map info
map_info = oculon.get_hotspot_map("all_datasets")
print(map_info["url"])

# Get evaluation metrics
metrics = oculon.get_model_metrics("missing_persons")
print(metrics)
```

---

### Method 3: Run from Source

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/abhyudaymishr/bob-ai-hackathon-oculon.git
   cd bob-ai-hackathon-oculon
   ```

2. **Create and Activate a Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the Application**:
   ```bash
   python app.py
   ```
   - **Gradio Dashboard**: `http://localhost:7860`
   - **Interactive Maps**: `http://localhost:7860/maps/four_dataset_hotspot_explorer.html`
   - **REST API**: `http://localhost:7860/api/hotspots`
   - **Local MCP SSE Stream**: `http://localhost:7860/sse`

---

### Method 4: Standalone Stdio MCP Bridge (Auto-Opens Local Browser)

To connect Claude Desktop or Cursor to a local instance that **actively launches your machine's default browser** when a map is queried:

```bash
python3 -m oculon.mcp_server
```

---

## 🔌 Connecting via Model Context Protocol (MCP)

### 1. Claude Desktop (Remote SSE)
Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "oculon_delhi_hotspots": {
      "url": "https://abhyudaymishr-oculon.hf.space/sse"
    }
  }
}
```

### 2. Cursor
In Cursor **Settings** &rarr; **Features** &rarr; **MCP Servers** &rarr; **Add New Server**:
- **Name**: `oculon_delhi_hotspots`
- **Type**: `SSE`
- **URL**: `https://abhyudaymishr-oculon.hf.space/sse`


---

## 🛠️ MCP Tools

| Tool | Parameters | Description |
| --- | --- | --- |
| `query_hotspots` | `dataset`, `month`, `query_text` | Query top forecasted hotspots with scores, coordinates, and direct map link. |
| `get_hotspot_map` | `map_type` | Returns browser-openable URL to the interactive map. |
| `get_model_metrics` | `dataset`, `evaluation_type` | Returns baseline 80/20 and rolling-origin validation metrics. |
| `list_datasets_and_months` | *(none)* | Lists available datasets, color representations, and forecast months. |

---

## 🌐 Programmatic REST Endpoints

- `GET /maps/{map_name}.html`: Direct raw static map view.
- `GET /api/hotspots?dataset=...&month=...`: JSON hotspot forecasts.
- `GET /api/metrics`: JSON model evaluation benchmarks.
- `GET /api/maps`: Available map URLs.
- `GET /sse`: Server-Sent Events stream for MCP clients.
- `POST /messages?session_id=...`: JSON-RPC 2.0 message handler for MCP.

---

## 🛡️ Privacy Guarantees

- **No Raw Person-Level Records**: All raw source CSVs containing names, phone numbers, or individual victim identifiers are strictly excluded.
- **Proxy Coordinates Only**: Mapped points correspond to official police station coordinates, metro stations, or centroid postal codes, never private residential or incident addresses.
- **Aggregated Payloads**: All served layers consist solely of statistical model probabilities, counts, and geographic reference geometries.
