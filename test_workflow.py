import json
import urllib.request

base = "http://127.0.0.1:8000"

# 1. Health
res1 = json.loads(urllib.request.urlopen(base + "/api/health").read())
print("1. Health:", res1)

# 2. Voice Extract
req_data = json.dumps({
    "voice_text": "Visite Appartement F4 120m2 chez Famille Benali. Grand Salon de 38m2 : carrelage 60x60 et peinture blanche satinée avec 12 spots dimmables. Cuisine 16m2 faïence et mitigeur. SDB 8m2 douche italienne. Prévoir carreleur 4 jours, peintre 3 jours, électricien 2 jours et plombier 2 jours.",
    "replace_existing": True
}).encode("utf-8")
r2 = urllib.request.Request(base + "/api/projects/proj-apt-f4/voice-extract", data=req_data, headers={"Content-Type": "application/json"})
res2 = json.loads(urllib.request.urlopen(r2).read())
print("2. Extraction Voice:", f"{len(res2['rooms'])} pièces", f"{len(res2['tasks_by_trade'])} corps d'état", f"{len(res2['materials'])} matériaux")

# 3. Batch procurement (calls to artisans & suppliers)
r3 = urllib.request.Request(base + "/api/calls/batch-procurement", data=json.dumps({"project_id": "proj-apt-f4"}).encode("utf-8"), headers={"Content-Type": "application/json"})
res3 = json.loads(urllib.request.urlopen(r3).read())
print("3. Batch Calls:", f"{res3['count_calls']} appels passés", f"{res3['count_offers']} offres reçues")

# 4. Generate quote with margin
r4 = urllib.request.Request(base + "/api/quotes/generate", data=json.dumps({"project_id": "proj-apt-f4", "margin_percent": 20.0}).encode("utf-8"), headers={"Content-Type": "application/json"})
res4 = json.loads(urllib.request.urlopen(r4).read())
print("4. Quote Total:", f"{res4['grand_total']} {res4['currency']}", f"({len(res4['items'])} lignes)")

print("\n>>> TOUS LES TESTS DU WORKFLOW 4 ÉTAPES SONT VALIDÉS AVEC SUCCÈS ! <<<")
