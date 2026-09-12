"""
ContractorPilot - HD Screenshot Capture Engine
Uses Playwright (Microsoft Edge channel) to take pixel-perfect 1080p (1920x1080) screenshots
of every step and modal in the ContractorPilot application for video production.
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).parent / "video" / "ScreenShots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

URL = "http://localhost:8000"


def capture_all_screens():
    print("================================================================")
    print(" [*] Launching Playwright HD Screen Capture (1920x1080)...")
    print(f" [*] Destination Directory: {OUTPUT_DIR}")
    print("================================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1.0,
        )
        page = context.new_page()

        # 1. Intro & Hero Dashboard
        print(" -> Capturing 01_intro_hero.png...")
        page.goto(URL, wait_until="networkidle")
        time.sleep(1.5)
        page.screenshot(path=str(OUTPUT_DIR / "01_intro_hero.png"))

        # 2. Step 1 - Walkthrough Voice Dictation
        print(" -> Capturing 02_step1_walkthrough.png...")
        # Populate demo transcription text
        page.evaluate("""
            const t = document.getElementById('voice-transcript-input');
            if (t) {
                t.value = "Walkthrough notes for The Miller Residence, 1,300 sq ft luxury condo remodel. Living room 400 sq ft: porcelain tile, velvet paint, 24 recessed LED lights. Kitchen 180 sq ft: backsplash tile, brass faucet. Master bath 96 sq ft: curbless walk-in shower. Schedule master tiler 4 days, finish painter 3 days, master electrician 2 days, and licensed plumber 2 days.";
            }
        """)
        time.sleep(0.8)
        page.screenshot(path=str(OUTPUT_DIR / "02_step1_walkthrough.png"))

        # 3. Step 2 - Remodel Scopes & Material Takeoffs
        print(" -> Capturing 03_step2_scopes.png...")
        page.evaluate("window.contractorPilotApp.goToStep(2);")
        time.sleep(1.2)
        page.screenshot(path=str(OUTPUT_DIR / "03_step2_scopes.png"))

        # 4. Step 3 - CALL-E Autonomous Call Center Monitor
        print(" -> Capturing 04_step3_call_monitor.png...")
        page.evaluate("window.contractorPilotApp.goToStep(3);")
        time.sleep(1.2)
        page.screenshot(path=str(OUTPUT_DIR / "04_step3_call_monitor.png"))

        # 5. Step 3 - Live Call Connected with Real-Time Terms Extraction
        print(" -> Capturing 05_step3_call_connected.png...")
        page.evaluate("""
            if (window.calleCenter) {
                window.calleCenter.loadScenario('apex_tile');
                const tBox = document.getElementById('monitor-transcript-messages');
                if (tBox) {
                    tBox.innerHTML = `
                        <div class="transcript-msg contact"><strong>Sarah Jenkins (Supplier):</strong> Apex Tile and Stone, Sarah speaking. How can I help you today?</div>
                        <div class="transcript-msg ai"><strong>CALL-E (AI Agent):</strong> Hello Sarah! This is CALL-E, autonomous procurement copilot for ContractorPilot. We are sourcing 520 sq ft of 24x24 Calacatta porcelain floor tiles for an active condo remodel. Do you have that in stock, and what is your best contractor rate?</div>
                        <div class="transcript-msg contact"><strong>Sarah Jenkins (Supplier):</strong> Hi CALL-E! Yes, we have five pallets ready in our warehouse. For 520 sq ft, our wholesale rate is $4.20 per sq ft, down from $4.50. And we'll deliver it to the jobsite in 48 hours with no freight charge.</div>
                        <div class="transcript-msg ai"><strong>CALL-E (AI Agent):</strong> Confirmed: $4.20 per sq ft with free jobsite delivery. Offer captured. Thank you, Sarah!</div>
                    `;
                }
                const ext = document.getElementById('monitor-extracted-box');
                if (ext) {
                    ext.style.display = 'block';
                    document.getElementById('live-extract-price').innerText = '$4.20 / sq ft';
                    document.getElementById('live-extract-discount').innerText = '6.7 % ($4.20 vs $4.50)';
                    document.getElementById('live-extract-stock').innerText = 'In Stock (5 Pallets)';
                    document.getElementById('live-extract-delay').innerText = '2 business days (Free Freight)';
                }
                const state = document.getElementById('monitor-call-state-text');
                if (state) state.innerText = 'CALL COMPLETED (TERMS EXTRACTED)';
            }
        """)
        time.sleep(1.0)
        page.screenshot(path=str(OUTPUT_DIR / "05_step3_call_connected.png"))

        # 6. Neural Voice Studio Modal (14 Tracks)
        print(" -> Capturing 06_voice_studio_modal.png...")
        page.evaluate("""
            const modal = document.getElementById('modal-audio-studio');
            if (modal) modal.classList.add('active');
            if (window.contractorPilotApp) window.contractorPilotApp.loadAudioManifest();
        """)
        time.sleep(1.2)
        page.screenshot(path=str(OUTPUT_DIR / "06_voice_studio_modal.png"))

        # Close studio modal
        page.evaluate("""
            const modal = document.getElementById('modal-audio-studio');
            if (modal) modal.classList.remove('active');
        """)
        time.sleep(0.5)

        # 7. Step 4 - Proposal Studio & Vendor Comparison
        print(" -> Capturing 07_step4_proposal_studio.png...")
        page.evaluate("window.contractorPilotApp.goToStep(4);")
        time.sleep(1.2)
        page.screenshot(path=str(OUTPUT_DIR / "07_step4_proposal_studio.png"))

        # 8. Step 4 - Official Client Proposal Sheet - Header & Scopes (Image 1)
        print(" -> Capturing 08_step4_proposal_top.png...")
        page.evaluate("""
            const sheet = document.getElementById('printable-quote-document');
            if (sheet) sheet.scrollIntoView({ behavior: 'instant', block: 'start' });
        """)
        time.sleep(1.2)
        page.screenshot(path=str(OUTPUT_DIR / "08_step4_proposal_top.png"))

        # 9. Step 4 - Official Client Proposal Sheet - Total $9,696 & Signature Block (Image 2)
        print(" -> Capturing 09_step4_proposal_bottom.png...")
        page.evaluate("""
            const totalRow = document.querySelector('.tfoot-grand-total');
            if (totalRow) totalRow.scrollIntoView({ behavior: 'instant', block: 'center' });
        """)
        time.sleep(1.2)
        page.screenshot(path=str(OUTPUT_DIR / "09_step4_proposal_bottom.png"))

        browser.close()
        print("\n[+] ALL 9 HD SCREENSHOTS CAPTURED SUCCESSFULLY IN 1920x1080!")


if __name__ == "__main__":
    capture_all_screens()
