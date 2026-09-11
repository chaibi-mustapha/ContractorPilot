import os
import sys
import uvicorn

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    port = int(os.environ.get("PORT", 8000))
    print("================================================================")
    print(" [*] Starting ContractorPilot (Autonomous CALL-E Voice Copilot)")
    print(f" [*] Web Dashboard: http://0.0.0.0:{port}")
    print("================================================================")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
