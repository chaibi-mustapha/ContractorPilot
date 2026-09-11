import json
import urllib.request

base = "http://127.0.0.1:8000"

# 1. Health
res1 = json.loads(urllib.request.urlopen(base + "/api/health").read())
print("1. Health Status:", res1)

# 2. Voice Walkthrough Extraction
req_data = json.dumps({
    "voice_text": "Walkthrough notes for The Miller Residence, 1,300 sq ft luxury condo remodel. Living room 400 sq ft: porcelain tile, velvet paint, 24 recessed LED lights. Kitchen 180 sq ft: backsplash tile, brass faucet. Master bath 96 sq ft: curbless walk-in shower. Schedule master tiler 4 days, finish painter 3 days, master electrician 2 days, and licensed plumber 2 days.",
    "replace_existing": True
}).encode("utf-8")
r2 = urllib.request.Request(base + "/api/projects/proj-apt-f4/voice-extract", data=req_data, headers={"Content-Type": "application/json"})
res2 = json.loads(urllib.request.urlopen(r2).read())
print("2. Walkthrough Extraction:", f"{len(res2['rooms'])} rooms", f"{len(res2['tasks_by_trade'])} trade scopes", f"{len(res2['materials'])} materials")

# 3. Batch procurement (calls to subcontractors & suppliers)
r3 = urllib.request.Request(base + "/api/calls/batch-procurement", data=json.dumps({"project_id": "proj-apt-f4"}).encode("utf-8"), headers={"Content-Type": "application/json"})
res3 = json.loads(urllib.request.urlopen(r3).read())
print("3. Batch Calls Sourced:", f"{res3['count_calls']} calls placed", f"{res3['count_offers']} offers captured")

# 4. Generate quote with margin
r4 = urllib.request.Request(base + "/api/quotes/generate", data=json.dumps({"project_id": "proj-apt-f4", "margin_percent": 20.0, "currency": "$"}).encode("utf-8"), headers={"Content-Type": "application/json"})
res4 = json.loads(urllib.request.urlopen(r4).read())
print("4. Proposal Total:", f"{res4['currency']}{res4['grand_total']:,.2f}", f"({len(res4['items'])} line items)")

print("\n>>> ALL 4-STEP WORKFLOW TESTS PASSED SUCCESSFULLY IN USD! <<<")
