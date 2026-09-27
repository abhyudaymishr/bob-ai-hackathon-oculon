"""
Oculon: Delhi Hotspots ML
Spatiotemporal Crime & Public Safety Hotspot Forecasting with Model Context Protocol (MCP).
"""

__version__ = "1.0.0"

from .mcp_server import (
    query_hotspots,
    get_hotspot_map,
    get_model_metrics,
    list_datasets_and_months,
    run_stdio_server,
)

__all__ = [
    "query_hotspots",
    "get_hotspot_map",
    "get_model_metrics",
    "list_datasets_and_months",
    "run_stdio_server",
]
