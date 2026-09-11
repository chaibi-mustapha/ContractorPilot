# ContractorPilot — Autonomous Voice Copilot: Jobsite Walkthrough to Signed Proposal with CALL-E 📞🏠

> **Devpost CALL-E Hackathon Submission** — *Your Code Is Calling*  
> **Pitch:** ContractorPilot empowers renovation general contractors to go from a jobsite walkthrough to a signed client proposal. The autonomous **CALL-E** voice agent directly telephones suppliers and trade subcontractors, negotiates contractor pricing, verifies live warehouse stock and lead times, compares bids with a weighted multi-criteria score, and generates a client-ready contract proposal.

---

## 💡 The Problem: The Contractor Phone Bottleneck

Every residential remodel starts with a walkthrough. But after measuring rooms and taking notes, contractors face hours of frustrating phone calls:
- Dialing 4 to 6 suppliers to compare prices, verify stock availability, and check delivery freight fees.
- Calling multiple subcontractors (tilers, painters, plumbers, electricians) to check schedule availability and day rates.
- Losing contracts because it takes 3 to 7 days to manually compile all numbers into a quote.

**ContractorPilot turns this multi-day nightmare into an autonomous, 3-minute workflow.**

---

## 🌟 Key Features

1. **🎙️ Voice Walkthrough Dictation (Step 1)**:
   - Dictate jobsite observations freely using the Web Speech API or preset recordings.
   - Captures room dimensions (e.g. Living Room 400 sq ft, Kitchen 180 sq ft, Master Bath 96 sq ft) and renovation scopes.

2. **📋 AI Scope Breakdown by Trade & Materials (Step 2)**:
   - Instantly categorizes walkthrough notes into trade labor tasks (Master Tiler, Finish Painter, Licensed Plumber, Master Electrician) and material bills of quantities (sq ft of porcelain tile, gallons of paint, recessed LED downlights, brass fixtures).

3. **📞 CALL-E Autonomous Voice Procurement (Step 3)**:
   - **Real Calling Mode**: Integrates the official `calle-ai` SDK (`CalleClient`) with custom task prompt engineering and structured JSON extraction schemas (`client.calls.create_and_wait`).
   - **Interactive Live Sandbox**: An interactive browser-based phone simulator with dynamic canvas audio waveforms, Web Audio synthetic telephony tones, progressive turn-by-turn dialogue transcripts, and live data extraction.

4. **⚖️ Multi-Criteria Offer Matrix & Scoring (Step 4)**:
   - Evaluates vendor and trade bids on a 100-point weighted score:
     - **40%** Net Price
     - **20%** Warehouse Stock Availability
     - **15%** Delivery Lead Time
     - **10%** Direct Jobsite Delivery
     - **10%** Vendor Reliability & Track Record
     - **5%** Volume Trade Discount
   - Automatically recommends the highest-value option.

5. **📑 Proposal Studio & Markup Slider (Step 4)**:
   - Interactive contractor gross markup slider (0% to 45%, standard 20%).
   - Generates official proposal **N° CP-2026-001** ready to print or export as PDF.
   - Single-click clipboard summary export.

---

## 🛠️ Technical Architecture

- **Backend**: FastAPI (Python 3.13), Uvicorn, WebSockets for live call streaming.
- **Voice Agent**: Official `calle-ai` Python SDK (`v0.7.0`).
- **Frontend**: Responsive Single-Page App with Vanilla HTML5/CSS3/JavaScript (Deep luxury dark theme, glassmorphism, Outfit/Inter typography, Web Audio API sound generator).
- **Data Persistence**: JSON/SQLite local datastore pre-seeded with *The Miller Residence* 1,300 sq ft luxury condo remodel.

---

## 🎬 3-Minute Video Demo Script (For Judges)

### Scene 1: The Problem & Introduction (0:00 - 0:35)
- Open on the **ContractorPilot** dashboard.
- Explain: *"Contractors spend 10+ hours every week calling suppliers and trade subs just to price a single jobsite quote. ContractorPilot automates this entire phone loop using CALL-E autonomous voice agents."*

### Scene 2: Step 1 — Jobsite Walkthrough (0:35 - 1:05)
- Click the microphone or load the **Full Remodel 1,300 sq ft** preset.
- Show the live transcription describing living room paint, LED downlights, kitchen and master bath Calacatta porcelain tiles, and plumbing trims.
- Click **"Analyze Walkthrough & Generate Remodel Scopes ➔"**.

### Scene 3: Step 2 — Scope Breakdown (1:05 - 1:35)
- Show the clean separation: Trade Subcontractor tasks (tiler, painter, electrician, plumber) on the left, Material items to procure on the right.
- Highlight the pre-negotiation estimate.
- Click **"Launch CALL-E Autonomous Sourcing Calls ➔"**.

### Scene 4: Step 3 — Autonomous Calling in Action (1:35 - 2:20)
- Watch the live CALL-E phone monitor:
  - Status transitions: Dialing ➔ Ringing ➔ Connected.
  - Interactive audio soundwave reacts to the conversation.
  - Dialogue streams turn-by-turn: CALL-E introduces itself, inquires about 520 sq ft of 24x24 Calacatta tiles, checks stock, and negotiates a 5% trade discount.
  - Live extraction cards populate in real time (Unit price $4.25, 5% discount, 650 sq ft in stock, 3-day freight delivery).

### Scene 5: Step 4 — Multi-Criteria Comparison & Proposal (2:20 - 2:50)
- Navigate to Step 4.
- Display the multi-criteria ranking cards highlighting the top recommended offers.
- Demonstrate the contractor gross markup slider adjusting in real time (e.g., from 15% to 20%).
- Show the final contract total updating dynamically.

### Scene 6: Printable Proposal & Conclusion (2:50 - 3:00)
- Show the official **CP-2026-001** client proposal document with line items, milestone draw terms, and client signature block.
- Conclude: *"From walkthrough note to signed contract in minutes, powered by CALL-E."*

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Modern web browser (Chrome, Edge, Firefox, Safari)

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/chaibi-mustapha/ContractorPilot.git
cd ContractorPilot
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
If you want to place real phone calls to your own phone number:
```bash
cp .env.example .env
# Edit .env and set your CALLE_API_KEY
```
*(Without an API key, ContractorPilot automatically runs in interactive sandbox demo mode).*

### 3. Launch Server
```bash
python run_server.py
```
Open your browser at:  
👉 **`http://localhost:8000`**

---

## 🌐 Cloud Deployment & Publishing

### Option A: 1-Click Full-Stack Deployment on Render (Recommended)
ContractorPilot includes a turnkey [`render.yaml`](render.yaml) blueprint:
1. Go to [Render Dashboard](https://dashboard.render.com/) and click **New > Blueprint** (or **New > Web Service**).
2. Connect this repository: `chaibi-mustapha/ContractorPilot`.
3. Render automatically installs `requirements.txt` and starts `python run_server.py`.
4. Your complete full-stack app (FastAPI backend + Live WebSockets + Responsive Dashboard) is instantly live with free SSL.

### Option B: GitHub Pages (Instant Frontend Showcase)
A pre-configured GitHub Actions workflow [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml) is included:
1. In your GitHub repository, go to **Settings** > **Pages**.
2. Under **Build and deployment** > **Source**, select **GitHub Actions**.
3. Any push to `main` automatically builds and publishes the web application to:  
   👉 `https://chaibi-mustapha.github.io/ContractorPilot/`

### Option C: Docker Container
A production-ready [`Dockerfile`](Dockerfile) is provided:
```bash
docker build -t contractorpilot .
docker run -p 8000:8000 contractorpilot
```

---

## 👥 Authors
Built for the **Devpost CALL-E Hackathon** (September 2026).

