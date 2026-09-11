"""
ContractorPilot - Automated End-to-End Workflow Verification Script
Tests:
1. API Health & Engine Status
2. AI Voice Walkthrough Extraction (US Units: sq ft, gal, days)
3. CALL-E Batch Procurement (Subcontractors & Materials in USD)
4. AI Proposal Generation (Margins & Line Items in USD $)
"""

import json
from starlette.testclient import TestClient
from backend.main import app

def run_test():
    client = TestClient(app)

    # 1. Health
    res1 = client.get("/api/health").json()
    print("1. Health Status:", res1)
    assert res1.get("app") == "ContractorPilot", f"Unexpected app name: {res1}"

    # 2. Voice Walkthrough Extraction
    payload = {
        "voice_text": "Walkthrough notes for The Miller Residence, 1,300 sq ft luxury condo remodel. Living room 400 sq ft: porcelain tile, velvet paint, 24 recessed LED lights. Kitchen 180 sq ft: backsplash tile, brass faucet. Master bath 96 sq ft: curbless walk-in shower. Schedule master tiler 4 days, finish painter 3 days, master electrician 2 days, and licensed plumber 2 days.",
        "replace_existing": True
    }
    r2 = client.post("/api/projects/proj-apt-f4/voice-extract", json=payload)
    assert r2.status_code == 200, f"Voice extract failed: {r2.text}"
    res2 = r2.json()
    print(f"2. Walkthrough Extraction: {len(res2['rooms'])} rooms, {len(res2['tasks_by_trade'])} trade scopes, {len(res2['materials'])} materials")

    # Verify US units in requirements
    reqs = res2.get("all_requirements", [])
    units_found = {r.get("unit") for r in reqs}
    print(f"   Units detected in takeoff: {units_found}")
    assert any(u in units_found for u in ["sq ft", "gal", "days", "units"]), f"Expected US units, got {units_found}"

    # 3. Batch procurement (calls to subcontractors & suppliers)
    r3 = client.post("/api/calls/batch-procurement", json={"project_id": "proj-apt-f4"})
    assert r3.status_code == 200, f"Batch procurement failed: {r3.text}"
    res3 = r3.json()
    print(f"3. Batch Calls Sourced: {res3['count_calls']} calls placed, {res3['count_offers']} offers captured")

    # 4. Generate quote with margin
    r4 = client.post("/api/quotes/generate", json={"project_id": "proj-apt-f4", "margin_percent": 20.0, "currency": "$"})
    assert r4.status_code == 200, f"Quote generation failed: {r4.text}"
    res4 = r4.json()
    print(f"4. Proposal Total: {res4['currency']}{res4['grand_total']:,.2f} ({len(res4['items'])} line items)")
    assert res4["currency"] == "$", f"Expected USD $, got {res4['currency']}"
    assert res4["grand_total"] > 0, "Expected non-zero total"

    print("\n>>> ALL 4-STEP WORKFLOW TESTS PASSED SUCCESSFULLY IN USD ($) & US CUSTOMARY UNITS! <<<")

if __name__ == "__main__":
    run_test()
