import sys
import uvicorn

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("================================================================")
    print(" [*] Demarrage de ContractorPilot (CALL-E AI Voice Sourcing & Quoting)")
    print(" [*] Acces Web : http://localhost:8000")
    print("================================================================")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)

