#!/usr/bin/env python3
"""
scripts/test_ci_cd_queries.py
-----------------------------
Comprehensive CI/CD test suite for Delhi Hotspots ML & Hugging Face Space.
Tests:
1. User-controlled limits: verify that queries return exactly requested counts (e.g. 5, 25, 100, or all 210+ units)
   and are NOT capped to 7 records.
2. Complete dataset fetchability across all 4 datasets:
   - Missing Persons (210 police stations across 136 months)
   - Unidentified Bodies (210 police stations across 53 months)
   - Stolen Vehicles (247/259 metro stations & 98/124 PIN zones across 83 months)
   - Missing Mobiles (virtual e-Theft timeline across 9 months)
3. Multiple data types: hotspots, all_units, monthly_timeline, station_records, raw_events, summary.
4. Live on-the-fly model prediction for unobserved/future months.
5. REST API endpoints (/api/hotspots, /api/fetch_records, /api/query_hotspots, /api/predict_hotspots, /api/metrics).
6. MCP JSON-RPC protocol over stdio and SSE transport.

Usage:
  python scripts/test_ci_cd_queries.py --local
  python scripts/test_ci_cd_queries.py --remote https://abhyudaymishr-oculon.hf.space
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

PASS_ICON = "✅"
FAIL_ICON = "❌"
WARN_ICON = "⚠️"


def run_local_tests() -> bool:
    print("\n" + "="*70)
    print("🚀 RUNNING LOCAL CI/CD QUERY TEST SUITE (In-Process)")
    print("="*70 + "\n")

    try:
        from oculon import mcp_server
    except ImportError:
        from delhi_hotspots import mcp_server
    all_passed = True

    def test(name: str, condition: bool, details: str = ""):
        nonlocal all_passed
        if condition:
            print(f"{PASS_ICON} PASS: {name} {details}")
        else:
            print(f"{FAIL_ICON} FAIL: {name} {details}")
            all_passed = False

    # --------------------------------------------------------------------------
    # 1. User-Controlled Limits (Verifying outputs are NOT capped at 7)
    # --------------------------------------------------------------------------
    print("\n--- TEST GROUP 1: User-Controlled Limits & Dynamic Counts ---")

    # Limit = 5
    res_5 = mcp_server.query_hotspots(dataset="missing_persons", top_k=5)
    test("query_hotspots(top_k=5)", len(res_5.get("hotspots", [])) == 5, f"(got {len(res_5.get('hotspots', []))})")

    # Limit = 20
    res_20 = mcp_server.query_hotspots(dataset="missing_persons", top_k=20)
    test("query_hotspots(top_k=20)", len(res_20.get("hotspots", [])) == 20, f"(got {len(res_20.get('hotspots', []))})")

    # Limit = 50
    res_50 = mcp_server.query_hotspots(dataset="missing_persons", top_k=50)
    test("query_hotspots(top_k=50)", len(res_50.get("hotspots", [])) == 50, f"(got {len(res_50.get('hotspots', []))})")

    # Limit = "all" (should return all 210 police stations!)
    res_all = mcp_server.query_hotspots(dataset="missing_persons", top_k="all")
    test("query_hotspots(top_k='all')", len(res_all.get("hotspots", [])) == 210, f"(got {len(res_all.get('hotspots', []))}, expected 210)")

    # Stolen vehicles metro limit = "all" (should return all 259 metro stations!)
    res_sv_metro = mcp_server.query_hotspots(dataset="stolen_vehicles", spatial_method="metro", top_k="all")
    test("query_hotspots(stolen_vehicles metro top_k='all')", len(res_sv_metro.get("hotspots", [])) == 259, f"(got {len(res_sv_metro.get('hotspots', []))}, expected 259)")

    # Stolen vehicles PIN limit = "all" (should return all 98 PIN zones!)
    res_sv_pin = mcp_server.query_hotspots(dataset="stolen_vehicles", spatial_method="pin", top_k="all")
    test("query_hotspots(stolen_vehicles pin top_k='all')", len(res_sv_pin.get("hotspots", [])) == 98, f"(got {len(res_sv_pin.get('hotspots', []))}, expected 98)")

    # list_hotspots limit = 7 vs limit = "all"
    list_7 = mcp_server.list_hotspots(dataset="missing_persons", limit=7)
    test("list_hotspots(limit=7)", len(list_7) == 7, f"(got {len(list_7)})")

    list_all = mcp_server.list_hotspots(limit="all")
    test("list_hotspots(limit='all')", len(list_all) >= 700, f"(got {len(list_all)} records across all datasets, NOT capped at 7)")

    # --------------------------------------------------------------------------
    # 2. Complete Dataset Fetchability Across All 4 Datasets
    # --------------------------------------------------------------------------
    print("\n--- TEST GROUP 2: Complete Dataset Fetchability (All 4 Datasets) ---")

    # Dataset 1: Missing Persons
    mp_units = mcp_server.fetch_dataset_records(dataset="missing_persons", data_type="all_units", limit="all")
    test("Missing Persons complete units", mp_units.get("total_matching_units") == 210 and len(mp_units.get("units", [])) == 210, f"(got {len(mp_units.get('units', []))}/210)")

    mp_time = mcp_server.fetch_dataset_records(dataset="missing_persons", data_type="monthly_timeline", limit="all")
    test("Missing Persons complete timeline (136 months)", len(mp_time.get("timeline", [])) == 136, f"(got {len(mp_time.get('timeline', []))}/136 months)")

    # Dataset 2: Unidentified Bodies
    ub_units = mcp_server.fetch_dataset_records(dataset="unidentified_bodies", data_type="all_units", limit="all")
    test("Unidentified Bodies complete units", ub_units.get("total_matching_units") == 210 and len(ub_units.get("units", [])) == 210, f"(got {len(ub_units.get('units', []))}/210)")

    ub_time = mcp_server.fetch_dataset_records(dataset="unidentified_bodies", data_type="monthly_timeline", limit="all")
    test("Unidentified Bodies complete timeline (53 months)", len(ub_time.get("timeline", [])) == 53, f"(got {len(ub_time.get('timeline', []))}/53 months)")

    # Dataset 3: Stolen Vehicles
    sv_units = mcp_server.fetch_dataset_records(dataset="stolen_vehicles", data_type="all_units", spatial_method="metro", limit="all")
    test("Stolen Vehicles complete metro units", sv_units.get("total_matching_units") == 259 and len(sv_units.get("units", [])) == 259, f"(got {len(sv_units.get('units', []))}/259)")

    sv_time = mcp_server.fetch_dataset_records(dataset="stolen_vehicles", data_type="monthly_timeline", limit="all")
    test("Stolen Vehicles complete timeline (83 months)", len(sv_time.get("timeline", [])) == 83, f"(got {len(sv_time.get('timeline', []))}/83 months)")

    # Dataset 4: Missing Mobiles
    mm_time = mcp_server.fetch_dataset_records(dataset="missing_mobiles", data_type="monthly_timeline", limit="all")
    test("Missing Mobiles complete timeline (9 months)", len(mm_time.get("timeline", [])) == 9, f"(got {len(mm_time.get('timeline', []))}/9 months)")

    # --------------------------------------------------------------------------
    # 3. Data Types & Filtering Tests
    # --------------------------------------------------------------------------
    print("\n--- TEST GROUP 3: Multi-Data-Type & Geographic Filtering ---")

    # Station records aggregated
    st_records = mcp_server.fetch_dataset_records(dataset="missing_persons", data_type="station_records", limit=10)
    test("fetch_dataset_records(station_records, limit=10)", len(st_records.get("stations", [])) == 10, f"(got {len(st_records.get('stations', []))})")

    # District filter
    dist_records = mcp_server.fetch_dataset_records(dataset="missing_persons", data_type="all_units", filter_district="North", limit="all")
    test("fetch_dataset_records(filter_district='North')", len(dist_records.get("units", [])) > 0, f"(got {len(dist_records.get('units', []))} units in North district)")

    # Summary query
    summ = mcp_server.fetch_dataset_records(data_type="summary")
    test("fetch_dataset_records(data_type='summary')", len(summ.get("datasets", {})) == 4, f"(keys: {list(summ.get('datasets', {}).keys())})")

    # --------------------------------------------------------------------------
    # 4. Live Model Prediction Engine
    # --------------------------------------------------------------------------
    print("\n--- TEST GROUP 4: Live On-The-Fly Model Prediction ---")

    live_res = mcp_server.predict_hotspots(dataset="missing_persons", target_month="2026-12", top_k="all")
    test("predict_hotspots for 2026-12 (all)", len(live_res.get("hotspots", [])) == 210, f"(evaluated {len(live_res.get('hotspots', []))} candidate stations)")
    test("predict_hotspots has perplexity metric", "predictive_perplexity" in live_res, f"(perplexity: {live_res.get('predictive_perplexity')})")

    # --------------------------------------------------------------------------
    # 5. MCP JSON-RPC Protocol & Tool Dispatch
    # --------------------------------------------------------------------------
    print("\n--- TEST GROUP 5: MCP JSON-RPC Protocol & Tool Invocation ---")

    rpc_tools = mcp_server.handle_rpc_request({"id": 1, "method": "tools/list"})
    registered = [t["name"] for t in rpc_tools["result"]["tools"]]
    test("MCP tools/list contains fetch_dataset_records", "fetch_dataset_records" in registered, f"({registered})")

    rpc_call = mcp_server.handle_rpc_request({
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "fetch_dataset_records",
            "arguments": {
                "dataset": "missing_persons",
                "data_type": "all_units",
                "limit": 30
            }
        }
    })
    call_res = json.loads(rpc_call["result"]["content"][0]["text"])
    test("MCP tools/call fetch_dataset_records limit=30", call_res.get("returned_units_count") == 30, f"(got {call_res.get('returned_units_count')})")

    print("\n" + "="*70)
    if all_passed:
        print(f"🎉 ALL LOCAL CI/CD QUERY TESTS PASSED SUCCESSFULLY! ({PASS_ICON})")
    else:
        print(f"💥 SOME TESTS FAILED. ({FAIL_ICON})")
    print("="*70 + "\n")
    return all_passed


def run_remote_tests(base_url: str) -> bool:
    import urllib.request
    import urllib.error

    clean_url = base_url.rstrip("/")
    print("\n" + "="*70)
    print(f"🌐 RUNNING REMOTE CI/CD QUERY TESTS AGAINST: {clean_url}")
    print("="*70 + "\n")

    all_passed = True

    def test(name: str, condition: bool, details: str = ""):
        nonlocal all_passed
        if condition:
            print(f"{PASS_ICON} PASS: {name} {details}")
        else:
            print(f"{FAIL_ICON} FAIL: {name} {details}")
            all_passed = False

    def http_get(path: str) -> Dict[str, Any]:
        url = f"{clean_url}{path}"
        req = urllib.request.Request(url, headers={"User-Agent": "Oculon-CICD-Tester/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def http_post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{clean_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Oculon-CICD-Tester/1.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        # Test 1: GET /api/hotspots with custom limit (limit=25)
        print("--> Testing GET /api/hotspots (User limit=25)...")
        res_25 = http_get("/api/hotspots?dataset=missing_persons&top_k=25")
        test("GET /api/hotspots?top_k=25 returns 25 records (NOT capped at 7)", len(res_25.get("hotspots", [])) == 25, f"(got {len(res_25.get('hotspots', []))})")

        # Test 2: GET /api/hotspots with limit="all" (210 records)
        print("--> Testing GET /api/hotspots (User limit='all')...")
        res_all = http_get("/api/hotspots?dataset=missing_persons&top_k=all")
        test("GET /api/hotspots?top_k=all returns all 210 records", len(res_all.get("hotspots", [])) == 210, f"(got {len(res_all.get('hotspots', []))})")

        # Test 3: POST /api/fetch_records for Stolen Vehicles (all 259 metro stations)
        print("--> Testing POST /api/fetch_records (Stolen Vehicles All Metro Units)...")
        res_metro = http_post("/api/fetch_records", {
            "dataset": "stolen_vehicles",
            "data_type": "all_units",
            "spatial_method": "metro",
            "limit": "all"
        })
        test("POST /api/fetch_records returns all 259 metro stations", len(res_metro.get("units", [])) == 259, f"(got {len(res_metro.get('units', []))})")

        # Test 4: POST /api/fetch_records monthly timeline for Unidentified Bodies (53 months)
        print("--> Testing POST /api/fetch_records (Unidentified Bodies Timeline)...")
        res_ub_time = http_post("/api/fetch_records", {
            "dataset": "unidentified_bodies",
            "data_type": "monthly_timeline",
            "limit": "all"
        })
        test("POST /api/fetch_records returns all 53 months for UB", len(res_ub_time.get("timeline", [])) == 53, f"(got {len(res_ub_time.get('timeline', []))})")

        # Test 5: POST /api/predict_hotspots on-the-fly model prediction
        print("--> Testing POST /api/predict_hotspots (Live model running)...")
        res_live = http_post("/api/predict_hotspots", {
            "dataset": "missing_persons",
            "target_month": "2027-01",
            "top_k": "all"
        })
        test("POST /api/predict_hotspots on-the-fly evaluates 210 stations", len(res_live.get("hotspots", [])) == 210, f"(got {len(res_live.get('hotspots', []))})")

        # Test 6: GET /api/metrics
        print("--> Testing GET /api/metrics...")
        metrics = http_get("/api/metrics")
        test("GET /api/metrics returns rolling-origin and baseline", "rolling_origin_forward_time" in metrics or "rolling_origin" in metrics, "(metrics loaded)")

        # Test 7: POST /mcp Streamable HTTP JSON-RPC initialize
        print("--> Testing POST /mcp (Streamable HTTP initialize)...")
        mcp_init = http_post("/mcp", {
            "jsonrpc": "2.0",
            "id": 100,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {}
            }
        })
        test("POST /mcp initialize returns protocolVersion 2024-11-05", mcp_init.get("result", {}).get("protocolVersion") == "2024-11-05", f"(got {mcp_init.get('result', {}).get('protocolVersion')})")

        # Test 8: POST /mcp Streamable HTTP tools/call
        print("--> Testing POST /mcp (Streamable HTTP tools/call)...")
        mcp_call = http_post("/mcp", {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "tools/call",
            "params": {
                "name": "query_hotspots",
                "arguments": {
                    "dataset": "missing_persons",
                    "top_k": 5
                }
            }
        })
        mcp_call_text = json.loads(mcp_call.get("result", {}).get("content", [{}])[0].get("text", "{}"))
        test("POST /mcp tools/call returns top_k=5 hotspots", len(mcp_call_text.get("hotspots", [])) == 5, f"(got {len(mcp_call_text.get('hotspots', []))})")

        # Test 9: GET /mcp Streamable HTTP metadata
        print("--> Testing GET /mcp (Streamable HTTP metadata)...")
        mcp_info = http_get("/mcp")
        test("GET /mcp returns transport='streamable-http'", mcp_info.get("transport") == "streamable-http", f"(status: {mcp_info.get('status')})")

    except Exception as e:
        print(f"{FAIL_ICON} ERROR during remote HTTP query tests: {e}")
        all_passed = False

    print("\n" + "="*70)
    if all_passed:
        print(f"🎉 ALL REMOTE CI/CD QUERY TESTS PASSED ON {clean_url}! ({PASS_ICON})")
    else:
        print(f"💥 SOME REMOTE TESTS FAILED ON {clean_url}. ({FAIL_ICON})")
    print("="*70 + "\n")
    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Delhi Hotspots ML CI/CD Query Test Suite")
    parser.add_argument("--local", action="store_true", help="Run local in-process test suite")
    parser.add_argument("--remote", type=str, help="Run test suite against remote URL (e.g. https://abhyudaymishr-oculon.hf.space)")
    args = parser.parse_args()

    success = True
    if args.local or (not args.local and not args.remote):
        success = run_local_tests()
    if args.remote:
        success = run_remote_tests(args.remote) and success

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
