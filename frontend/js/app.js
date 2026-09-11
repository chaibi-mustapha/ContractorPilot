/**
 * ContractorPilot — Application Core Controller (4-Step Guided Workflow)
 * Step 1 : Jobsite Walkthrough & Voice Note Capture
 * Step 2 : AI Remodel Scope & Material Breakdown
 * Step 3 : CALL-E Autonomous Voice Procurement & Calling
 * Step 4 : Vendor Comparison & Official Client Proposal
 */

class ContractorPilotApp {
  constructor() {
    this.currentProjectId = "proj-apt-f4";
    this.projectData = null;
    this.currentStep = 1;
    this.suppliers = [];
    this.tradespeople = [];
    this.marginPercent = 20.0;
    this.currency = "$";
    this.currentNeedsFilter = "all";

    // Speech Recognition
    this.isRecording = false;
    this.recognition = null;
    this.recordTimerInterval = null;
    this.recordSeconds = 0;
  }

  showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast-item ${type}`;
    let icon = "ℹ️";
    if (type === "success") icon = "✅";
    else if (type === "error") icon = "⚠️";
    toast.innerHTML = `<span>${icon}</span> <div>${message}</div>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.add("fade-out");
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  }

  formatMoney(amount) {
    const num = Math.round(Number(amount) || 0);
    return `$${num.toLocaleString("en-US")}`;
  }

  async init() {
    this.setupStepper();
    this.setupSpeechRecognition();
    this.setupEventListeners();
    await this.checkSettings();
    await this.loadProjectDetails(this.currentProjectId);
    if (window.calleCenter) {
      window.calleCenter.init(this.currentProjectId);
    }
  }

  // ------------------ Stepper Navigation ------------------

  setupStepper() {
    document.querySelectorAll(".step-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const step = parseInt(btn.getAttribute("data-step"), 10);
        this.goToStep(step);
      });
    });
  }

  goToStep(stepNumber) {
    if (stepNumber < 1 || stepNumber > 4) return;
    this.currentStep = stepNumber;

    // Update Step buttons
    document.querySelectorAll(".step-btn").forEach((btn) => {
      const step = parseInt(btn.getAttribute("data-step"), 10);
      btn.classList.toggle("active", step === stepNumber);
      btn.classList.toggle("completed", step < stepNumber);
    });

    // Update Step panes
    document.querySelectorAll(".step-pane").forEach((pane) => {
      pane.classList.remove("active");
    });
    const activePane = document.getElementById(`pane-step-${stepNumber}`);
    if (activePane) {
      activePane.classList.add("active");
    }

    // Contextual refresh
    if (stepNumber === 2) {
      this.renderNeedsLists();
    } else if (stepNumber === 3) {
      this.renderSessionCalls();
    } else if (stepNumber === 4) {
      this.refreshQuote();
      this.renderOffersRanking();
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // ------------------ Speech Recognition (Web Speech API) ------------------

  setupSpeechRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRec) {
      this.recognition = new SpeechRec();
      this.recognition.lang = "en-US";
      this.recognition.continuous = true;
      this.recognition.interimResults = true;

      this.recognition.onresult = (event) => {
        let currentTranscript = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          currentTranscript += event.results[i][0].transcript;
        }
        const textarea = document.getElementById("voice-transcription-input");
        if (textarea) {
          textarea.value = (textarea.value ? textarea.value + " " : "") + currentTranscript;
          this.updateWordCount();
        }
      };

      this.recognition.onerror = (event) => {
        console.warn("[SpeechRecognition] Error:", event.error);
        this.stopVoiceRecording();
      };

      this.recognition.onend = () => {
        if (this.isRecording) {
          this.stopVoiceRecording();
        }
      };
    }
  }

  toggleVoiceRecording() {
    if (this.isRecording) {
      this.stopVoiceRecording();
    } else {
      this.startVoiceRecording();
    }
  }

  startVoiceRecording() {
    this.isRecording = true;
    const btnMic = document.getElementById("btn-toggle-mic");
    const statusText = document.getElementById("mic-status-text");
    if (btnMic) btnMic.classList.add("recording");
    if (statusText) statusText.innerText = "🔴 Recording in progress... Describe your jobsite & tasks";

    this.recordSeconds = 0;
    this.updateRecordTimer();
    this.recordTimerInterval = setInterval(() => {
      this.recordSeconds++;
      this.updateRecordTimer();
    }, 1000);

    if (this.recognition) {
      try {
        this.recognition.start();
      } catch (e) {
        console.warn(e);
      }
    }
  }

  stopVoiceRecording() {
    this.isRecording = false;
    const btnMic = document.getElementById("btn-toggle-mic");
    const statusText = document.getElementById("mic-status-text");
    if (btnMic) btnMic.classList.remove("recording");
    if (statusText) statusText.innerText = "Dictation finished. You can review or edit below.";

    if (this.recordTimerInterval) {
      clearInterval(this.recordTimerInterval);
      this.recordTimerInterval = null;
    }

    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (e) {
        console.warn(e);
      }
    }
  }

  updateRecordTimer() {
    const timerDisplay = document.getElementById("mic-timer-display");
    if (timerDisplay) {
      const mins = String(Math.floor(this.recordSeconds / 60)).padStart(2, "0");
      const secs = String(this.recordSeconds % 60).padStart(2, "0");
      timerDisplay.innerText = `${mins}:${secs}`;
    }
  }

  updateWordCount() {
    const textarea = document.getElementById("voice-transcription-input");
    const counter = document.getElementById("transcription-word-count");
    if (textarea && counter) {
      const words = textarea.value.trim().split(/\s+/).filter(Boolean);
      counter.innerText = `${words.length} word${words.length > 1 ? "s" : ""}`;
    }
  }

  // ------------------ Event Listeners Setup ------------------

  setupEventListeners() {
    // Microphone button
    const btnMic = document.getElementById("btn-toggle-mic");
    if (btnMic) {
      btnMic.addEventListener("click", () => this.toggleVoiceRecording());
    }

    // Textarea input
    const textarea = document.getElementById("voice-transcription-input");
    if (textarea) {
      textarea.addEventListener("input", () => this.updateWordCount());
    }

    // Clear transcript button
    const btnClear = document.getElementById("btn-clear-transcript");
    if (btnClear) {
      btnClear.addEventListener("click", () => {
        if (textarea) {
          textarea.value = "";
          this.updateWordCount();
        }
      });
    }

    // Demo Prompts
    const btnDemoComplete = document.getElementById("btn-demo-prompt-complete");
    if (btnDemoComplete) {
      btnDemoComplete.addEventListener("click", () => {
        if (textarea) {
          textarea.value = "Walkthrough notes for The Miller Residence, 1,300 sq ft luxury condo remodel. Living and dining room (400 sq ft): prep walls, apply 2 coats of washable velvet matte paint in warm alabaster, install 24 recessed dimmable LED downlights on smart dimmers. Kitchen (180 sq ft) and Master Bath (96 sq ft): install 520 sq ft of 24x24 Calacatta marble porcelain floor tiles with precision mitered cuts. In the master bath: full waterproof membrane for curbless shower, double vanity, and designer brushed brass thermostatic fixtures. For subcontractor labor, schedule master tiler for 4 days, finish painter for 3 days, licensed plumber for 2 days, and master electrician for 2 days.";
          this.updateWordCount();
          this.showToast("Full Remodel Demo Walkthrough loaded!", "info");
        }
      });
    }

    const btnDemoLight = document.getElementById("btn-demo-prompt-light");
    if (btnDemoLight) {
      btnDemoLight.addEventListener("click", () => {
        if (textarea) {
          textarea.value = "Walkthrough scope: lighting and paint package. Living room and bedrooms: patch drywall, 10 gallons of premium washable matte paint, supply and install 24 recessed LED downlights on dimmers. Schedule master electrician for 2 days and finish painter for 3 days.";
          this.updateWordCount();
          this.showToast("Lighting & Paint preset loaded!", "info");
        }
      });
    }

    const btnDemoBath = document.getElementById("btn-demo-prompt-bath");
    if (btnDemoBath) {
      btnDemoBath.addEventListener("click", () => {
        if (textarea) {
          textarea.value = "Master bathroom suite remodel (96 sq ft). Demo old tile, apply complete waterproofing membrane for curbless walk-in shower, install 120 sq ft wall tile, brushed brass thermostatic mixer valve, and dual undermount vanity connections. Schedule licensed plumber for 2 days and master tiler for 2 days.";
          this.updateWordCount();
          this.showToast("Bathroom Suite preset loaded!", "info");
        }
      });
    }

    // Step 2 Filter Tabs
    ["all", "labor", "material"].forEach((filter) => {
      const tabBtn = document.getElementById(`filter-tab-${filter}`);
      if (tabBtn) {
        tabBtn.addEventListener("click", () => {
          this.currentNeedsFilter = filter;
          document.querySelectorAll(".filter-tab").forEach((b) => b.classList.remove("active"));
          tabBtn.classList.add("active");
          this.applyNeedsFilter();
        });
      }
    });

    // Analyze Voice Button (Step 1 -> Step 2)
    const btnExtract = document.getElementById("btn-extract-voice");
    if (btnExtract) {
      btnExtract.addEventListener("click", () => this.extractVoiceNeeds());
    }

    // Step 2 Action Buttons
    const btnStartCalls2 = document.getElementById("btn-start-consultation-step2");
    if (btnStartCalls2) {
      btnStartCalls2.addEventListener("click", () => this.launchBatchConsultation());
    }

    const btnStartCallsBottom = document.getElementById("btn-consult-all-bottom");
    if (btnStartCallsBottom) {
      btnStartCallsBottom.addEventListener("click", () => this.launchBatchConsultation());
    }

    // Step 3 Action Button
    const btnRelaunch = document.getElementById("btn-relaunch-batch-calls");
    if (btnRelaunch) {
      btnRelaunch.addEventListener("click", () => this.launchBatchConsultation());
    }

    // Step 4 Margin slider
    const marginSlider = document.getElementById("margin-slider");
    const marginVal = document.getElementById("margin-val-display");
    if (marginSlider && marginVal) {
      marginSlider.addEventListener("input", (e) => {
        this.marginPercent = parseFloat(e.target.value);
        marginVal.innerText = `${this.marginPercent}%`;
        this.updateMarginPresetButtons(this.marginPercent);
        this.refreshQuote();
      });
    }

    // Step 4 Margin preset buttons
    document.querySelectorAll(".btn-margin-preset").forEach((btn) => {
      btn.addEventListener("click", () => {
        const val = parseFloat(btn.getAttribute("data-margin"));
        this.marginPercent = val;
        if (marginSlider) marginSlider.value = val;
        if (marginVal) marginVal.innerText = `${val}%`;
        this.updateMarginPresetButtons(val);
        this.refreshQuote();
        this.showToast(`Contractor markup set to ${val}%`, "info");
      });
    });

    // Copy Quote Summary Button
    const btnCopySummary = document.getElementById("btn-copy-quote-summary");
    if (btnCopySummary) {
      btnCopySummary.addEventListener("click", () => this.copyQuoteSummary());
    }

    // Print Quote
    const btnPrint = document.getElementById("btn-print-quote");
    if (btnPrint) {
      btnPrint.addEventListener("click", () => window.print());
    }

    // Manual requirement modal
    this.setupManualRequirementModal();

    // Settings modal
    this.setupSettingsModal();
  }

  // ------------------ API Calls & Data Handling ------------------

  async loadProjectDetails(projectId) {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/projects/${projectId}`);
      if (!res.ok) return;
      this.projectData = await res.json();

      this.renderNeedsLists();
      this.renderSessionCalls();
      this.renderOffersRanking();
    } catch (e) {
      console.error("[loadProjectDetails] Error:", e);
    }
  }

  async extractVoiceNeeds() {
    const textarea = document.getElementById("voice-transcription-input");
    const text = textarea ? textarea.value.trim() : "";
    if (!text) {
      alert("Please dictate or enter your jobsite walkthrough notes first.");
      return;
    }

    const btnExtract = document.getElementById("btn-extract-voice");
    const originalText = btnExtract ? btnExtract.innerHTML : "";
    if (btnExtract) {
      btnExtract.disabled = true;
      btnExtract.innerHTML = "⏳ AI Analyzing Walkthrough...";
    }

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/projects/${this.currentProjectId}/voice-extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ voice_text: text, replace_existing: true }),
      });

      if (!res.ok) {
        throw new Error("Error extracting remodel requirements.");
      }

      await this.loadProjectDetails(this.currentProjectId);
      this.goToStep(2);
      this.showToast("Walkthrough converted into materials & trade scopes!", "success");
    } catch (err) {
      alert(err.message);
    } finally {
      if (btnExtract) {
        btnExtract.disabled = false;
        btnExtract.innerHTML = originalText;
      }
    }
  }

  renderNeedsLists() {
    if (!this.projectData) return;

    // 1. Detected Rooms Chips
    const roomsContainer = document.getElementById("detected-rooms-container");
    if (roomsContainer) {
      roomsContainer.innerHTML = "";
      (this.projectData.rooms || []).forEach((room) => {
        const chip = document.createElement("div");
        chip.className = "room-chip";
        chip.innerHTML = `📍 <span>${room.name}</span>: <strong>${room.surface} sq ft</strong>`;
        roomsContainer.appendChild(chip);
      });
      if (!this.projectData.rooms || this.projectData.rooms.length === 0) {
        roomsContainer.innerHTML = `<span style="color: var(--text-dim); font-size: 0.85rem;">No rooms measured yet</span>`;
      }
    }

    // Split requirements: Labor (Trades) vs Materials
    const requirements = this.projectData.requirements || [];
    const trades = requirements.filter(
      (r) => r.item_type === "labor" || r.category === "Labor" || ["Tiler", "Painter", "Electrician", "Plumber", "Carpenter", "Carreleur", "Peintre", "Électricien", "Plombier"].includes(r.category)
    );
    const materials = requirements.filter(
      (r) => r.item_type === "material" && !["Labor", "Tiler", "Painter", "Electrician", "Plumber", "Carpenter", "Carreleur", "Peintre", "Électricien", "Plombier"].includes(r.category)
    );

    // Indicative Pre-Negotiation Total
    let totalEstimate = 0;
    requirements.forEach((r) => {
      totalEstimate += (parseFloat(r.quantity) || 1) * (parseFloat(r.estimated_unit_price) || 0);
    });
    const preEstimateEl = document.getElementById("pre-estimate-val");
    if (preEstimateEl) {
      preEstimateEl.innerText = this.formatMoney(totalEstimate);
    }

    // Filter tab counts
    const countAll = document.getElementById("filter-count-all");
    const countLabor = document.getElementById("filter-count-labor");
    const countMat = document.getElementById("filter-count-material");
    if (countAll) countAll.innerText = requirements.length;
    if (countLabor) countLabor.innerText = trades.length;
    if (countMat) countMat.innerText = materials.length;

    // Update Counts Labels
    const tradesCountLabel = document.getElementById("trades-count-label");
    const matCountLabel = document.getElementById("materials-count-label");
    if (tradesCountLabel) tradesCountLabel.innerText = `${trades.length} trade subcontract scopes required`;
    if (matCountLabel) matCountLabel.innerText = `${materials.length} material lines to source`;

    // 2. Render Trades List
    const tradesList = document.getElementById("trades-tasks-list");
    if (tradesList) {
      tradesList.innerHTML = "";
      trades.forEach((item) => {
        const row = document.createElement("div");
        row.className = "need-item-card";

        let badgeClass = "badge-carreleur";
        if (item.category.includes("Paint") || item.category.includes("Peintre")) badgeClass = "badge-peintre";
        else if (item.category.includes("Elec")) badgeClass = "badge-electricien";
        else if (item.category.includes("Plumb") || item.category.includes("Plomb")) badgeClass = "badge-plombier";

        row.innerHTML = `
          <div class="need-item-main">
            <span class="need-badge-trade ${badgeClass}">🔨 ${item.category}</span>
            <div class="need-item-title">${item.item_name}</div>
            <div class="need-item-meta">
              <span>Duration: <strong>${item.quantity} ${item.unit}</strong></span> | 
              <span>Target Rate: <strong>${this.formatMoney(item.estimated_unit_price)}/${item.unit}</strong></span>
            </div>
          </div>
          <div class="need-item-actions">
            <button class="btn-delete-need" onclick="window.contractorPilotApp.deleteRequirement('${item.id}')" title="Delete">
              🗑️
            </button>
          </div>
        `;
        tradesList.appendChild(row);
      });

      if (trades.length === 0) {
        tradesList.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem;">No trade scopes detected. You can add one manually.</div>`;
      }
    }

    // 3. Render Materials List
    const materialsList = document.getElementById("materials-items-list");
    if (materialsList) {
      materialsList.innerHTML = "";
      materials.forEach((item) => {
        const row = document.createElement("div");
        row.className = "need-item-card";
        row.innerHTML = `
          <div class="need-item-main">
            <span class="need-badge-trade badge-material">🧱 ${item.category}</span>
            <div class="need-item-title">${item.item_name}</div>
            <div class="need-item-meta">
              <span>Quantity: <strong>${item.quantity} ${item.unit}</strong></span> | 
              <span>Est. Unit Cost: <strong>${this.formatMoney(item.estimated_unit_price)}</strong></span>
            </div>
          </div>
          <div class="need-item-actions">
            <button class="btn-delete-need" onclick="window.contractorPilotApp.deleteRequirement('${item.id}')" title="Delete">
              🗑️
            </button>
          </div>
        `;
        materialsList.appendChild(row);
      });

      if (materials.length === 0) {
        materialsList.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem;">No materials listed yet. You can add one manually.</div>`;
      }
    }

    this.applyNeedsFilter();
  }

  applyNeedsFilter() {
    const grid = document.getElementById("needs-split-grid-container");
    const cols = document.querySelectorAll(".needs-column-card");
    if (cols.length < 2) return;
    const laborCol = cols[0];
    const matCol = cols[1];

    if (this.currentNeedsFilter === "all") {
      laborCol.style.display = "flex";
      matCol.style.display = "flex";
      if (grid) grid.style.gridTemplateColumns = "";
    } else if (this.currentNeedsFilter === "labor") {
      laborCol.style.display = "flex";
      matCol.style.display = "none";
      if (grid) grid.style.gridTemplateColumns = "1fr";
    } else if (this.currentNeedsFilter === "material") {
      laborCol.style.display = "none";
      matCol.style.display = "flex";
      if (grid) grid.style.gridTemplateColumns = "1fr";
    }
  }

  updateMarginPresetButtons(marginVal) {
    document.querySelectorAll(".btn-margin-preset").forEach((btn) => {
      const val = parseFloat(btn.getAttribute("data-margin"));
      btn.classList.toggle("active", Math.abs(val - marginVal) < 0.1);
    });
  }

  copyQuoteSummary() {
    if (!this.projectData) return;
    const client = "The Miller Residence (1,300 sq ft Luxury Remodel)";
    const total = document.getElementById("fin-grand-total") ? document.getElementById("fin-grand-total").innerText : "$0";
    const mat = document.getElementById("fin-materials-cost") ? document.getElementById("fin-materials-cost").innerText : "$0";
    const lab = document.getElementById("fin-labor-cost") ? document.getElementById("fin-labor-cost").innerText : "$0";
    const margin = document.getElementById("fin-margin-val") ? document.getElementById("fin-margin-val").innerText : "$0";

    const summaryText = `🏗️ OFFICIAL CONTRACTOR PROPOSAL — CONTRACTORPILOT\nClient: ${client}\nProposal #: CP-2026-001\nMaterials & Supplies: ${mat}\nSubcontractor Labor: ${lab}\nContractor Markup (${this.marginPercent}%): ${margin}\n-----------------------------------\nTOTAL CONTRACT SUM: ${total}\nPrices and lead times verified via autonomous CALL-E voice agents.`;

    if (navigator.clipboard) {
      navigator.clipboard.writeText(summaryText).then(() => {
        this.showToast("Proposal summary copied to clipboard!", "success");
      });
    } else {
      this.showToast("Proposal summary ready!", "info");
    }
  }

  async deleteRequirement(reqId) {
    if (!confirm("Are you sure you want to remove this item?")) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/projects/${this.currentProjectId}/requirements/${reqId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        await this.loadProjectDetails(this.currentProjectId);
        this.showToast("Item deleted", "info");
      }
    } catch (e) {
      console.error(e);
    }
  }

  // ------------------ Step 3 : Procurement & Calls ------------------

  async launchBatchConsultation() {
    this.goToStep(3);

    const stateText = document.getElementById("monitor-call-state-text");
    if (stateText) stateText.innerText = "PROCUREMENT AGENTS ACTIVE...";

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/calls/batch-procurement`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: this.currentProjectId, is_live: false }),
      });

      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Error initiating calls");
        return;
      }

      await this.loadProjectDetails(this.currentProjectId);

      // Animate showcase live call in monitor
      if (window.calleCenter) {
        window.calleCenter.simulateLiveDemoCall();
      }
    } catch (e) {
      console.error(e);
    }
  }

  renderSessionCalls() {
    if (!this.projectData) return;
    const calls = this.projectData.call_records || [];
    const container = document.getElementById("session-call-history-list");
    const badge = document.getElementById("badge-calls-count");

    if (badge) badge.innerText = `${calls.length} call${calls.length > 1 ? "s" : ""}`;
    const statCalls = document.getElementById("stat-calls-count");
    if (statCalls) statCalls.innerText = calls.length;

    if (container) {
      container.innerHTML = "";
      calls.slice(-8).reverse().forEach((call) => {
        const item = document.createElement("div");
        item.className = "call-history-item";
        item.innerHTML = `
          <div>
            <strong>${call.target_name}</strong> (${call.requirement_name})
            <div style="font-size: 0.75rem; color: var(--text-muted);">${call.target_phone} • ${call.duration_seconds}s</div>
          </div>
          <span style="color: var(--accent-emerald); font-weight: 600; font-size: 0.82rem;">✓ Negotiated</span>
        `;
        container.appendChild(item);
      });

      if (calls.length === 0) {
        container.innerHTML = `<div style="color: var(--text-dim); font-size: 0.85rem; padding: 0.75rem;">Completed voice calls will appear here.</div>`;
      }
    }
  }

  // ------------------ Step 4 : Proposal & Comparison ------------------

  async refreshQuote() {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/quotes/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: this.currentProjectId,
          margin_percent: this.marginPercent,
          expenses_amount: 0.0,
          tax_percent: 0.0,
          currency: this.currency,
        }),
      });

      if (!res.ok) return;
      const quote = await res.json();
      this.displayQuote(quote);
    } catch (e) {
      console.error("[refreshQuote] Error:", e);
    }
  }

  displayQuote(quote) {
    // Financial Cards
    const matCost = document.getElementById("fin-materials-cost");
    const labCost = document.getElementById("fin-labor-cost");
    const marginVal = document.getElementById("fin-margin-val");
    const grandTotal = document.getElementById("fin-grand-total");
    const marginSub = document.getElementById("fin-margin-percent-sub");

    if (matCost) matCost.innerText = this.formatMoney(quote.materials_subtotal);
    if (labCost) labCost.innerText = this.formatMoney(quote.labor_subtotal);
    if (marginVal) marginVal.innerText = this.formatMoney(quote.margin_amount);
    if (grandTotal) grandTotal.innerText = this.formatMoney(quote.grand_total);
    if (marginSub) marginSub.innerText = `Gross markup applied (${quote.margin_percent}%)`;

    // Printable Quote Sheet
    const subMat = document.getElementById("quote-subtotal-materials");
    const subLab = document.getElementById("quote-subtotal-labor");
    const totalDisplay = document.getElementById("quote-grand-total-display");

    if (subMat) subMat.innerText = this.formatMoney(quote.materials_subtotal);
    if (subLab) subLab.innerText = this.formatMoney(quote.labor_subtotal);
    if (totalDisplay) totalDisplay.innerText = this.formatMoney(quote.grand_total);

    // Table body
    const tbody = document.getElementById("quote-table-body");
    if (tbody) {
      tbody.innerHTML = "";
      (quote.items || []).forEach((item) => {
        const tr = document.createElement("tr");
        const typeLabel = item.item_type === "labor" ? "Subcontractor" : "Material";
        tr.innerHTML = `
          <td>
            <strong>${item.description}</strong>
            <div style="font-size: 0.75rem; color: #64748B;">Source: ${item.supplier_or_trade}</div>
          </td>
          <td><span class="badge" style="background: rgba(100,116,139,0.15); color: #475569;">${typeLabel}</span></td>
          <td style="text-align: right;">${item.quantity} ${item.unit}</td>
          <td style="text-align: right;">${this.formatMoney(item.unit_price)}</td>
          <td style="text-align: right; font-weight: 700;">${this.formatMoney(item.total_price)}</td>
        `;
        tbody.appendChild(tr);
      });
    }
  }

  renderOffersRanking() {
    if (!this.projectData) return;
    const offers = this.projectData.offers || [];
    const container = document.getElementById("offers-ranking-container");
    if (!container) return;

    container.innerHTML = "";

    // Group offers by requirement_name
    const grouped = {};
    offers.forEach((o) => {
      if (!grouped[o.requirement_name]) grouped[o.requirement_name] = [];
      grouped[o.requirement_name].push(o);
    });

    Object.keys(grouped).forEach((reqName) => {
      const reqOffers = grouped[reqName];
      const bestOffer = reqOffers.find((o) => o.is_selected) || reqOffers[0];

      const card = document.createElement("div");
      card.className = `offer-rank-card ${bestOffer.is_recommended ? "recommended" : ""}`;
      
      const badgeHtml = bestOffer.is_recommended
        ? `<span class="offer-rank-badge" style="background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.35);">🥇 Top Recommended</span>`
        : `<span class="offer-rank-badge" style="background: rgba(99, 102, 241, 0.15); color: #818CF8; border: 1px solid rgba(99, 102, 241, 0.35);">Alternative Offer</span>`;

      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            ${badgeHtml}
            <h4 style="font-family: var(--font-display); font-size: 1.05rem; margin-top: 0.35rem; color: var(--text-main); font-weight: 700;">${reqName}</h4>
          </div>
          <div style="font-family: var(--font-mono); font-weight: 700; color: var(--accent-emerald); font-size: 1.15rem;">
            ${this.formatMoney(bestOffer.unit_price)}
          </div>
        </div>
        <div style="font-size: 0.85rem; color: var(--text-muted);">
          Vendor / Trade: <strong style="color: var(--text-main);">${bestOffer.target_name}</strong>
        </div>
        <div style="display: flex; gap: 0.8rem; font-size: 0.8rem; color: var(--text-muted); background: rgba(0,0,0,0.25); padding: 0.45rem 0.75rem; border-radius: var(--radius-sm); border: 1px solid rgba(255,255,255,0.05);">
          <span>AI Score: <strong style="color: var(--accent-cyan);">${bestOffer.calculated_score}/100</strong></span>
          <span>Lead Time: <strong>${bestOffer.delivery_days} days</strong></span>
          ${bestOffer.discount_percent > 0 ? `<span>Discount: <strong style="color: var(--accent-emerald);">-${bestOffer.discount_percent}%</strong></span>` : ""}
        </div>
      `;
      container.appendChild(card);
    });

    if (offers.length === 0) {
      container.innerHTML = `<div style="color: var(--text-dim); font-size: 0.9rem; padding: 1.5rem; text-align: center; grid-column: 1/-1;">Trigger CALL-E procurement in Step 3 to build the verified comparison matrix.</div>`;
    }
  }

  // ------------------ Modals ------------------

  setupManualRequirementModal() {
    const modal = document.getElementById("modal-add-requirement");
    const btnLabor = document.getElementById("btn-add-labor-manual");
    const btnMat = document.getElementById("btn-add-material-manual");
    const btnClose = document.getElementById("btn-close-req-modal");
    const btnCancel = document.getElementById("btn-cancel-req-modal");
    const form = document.getElementById("form-add-requirement");
    const typeSelect = document.getElementById("req-modal-type");
    const catSelect = document.getElementById("req-modal-category");
    const unitSelect = document.getElementById("req-modal-unit");

    const openModal = (defaultType) => {
      if (typeSelect) typeSelect.value = defaultType;
      if (defaultType === "labor") {
        if (catSelect) catSelect.value = "Tiler";
        if (unitSelect) unitSelect.value = "days";
      } else {
        if (catSelect) catSelect.value = "Flooring";
        if (unitSelect) unitSelect.value = "sq ft";
      }
      if (modal) modal.classList.add("active");
    };

    if (btnLabor) btnLabor.addEventListener("click", () => openModal("labor"));
    if (btnMat) btnMat.addEventListener("click", () => openModal("material"));
    if (btnClose) btnClose.addEventListener("click", () => modal.classList.remove("active"));
    if (btnCancel) btnCancel.addEventListener("click", () => modal.classList.remove("active"));

    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
          room_name: "Jobsite Wide",
          category: document.getElementById("req-modal-category").value,
          item_name: document.getElementById("req-modal-name").value,
          quantity: parseFloat(document.getElementById("req-modal-qty").value) || 1.0,
          unit: document.getElementById("req-modal-unit").value,
          item_type: document.getElementById("req-modal-type").value,
          estimated_unit_price: parseFloat(document.getElementById("req-modal-price").value) || 0.0,
          notes: "Added manually by general contractor",
        };

        try {
          const res = await fetch(`http://127.0.0.1:8000/api/projects/${this.currentProjectId}/requirements`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (res.ok) {
            modal.classList.remove("active");
            form.reset();
            await this.loadProjectDetails(this.currentProjectId);
            this.showToast("New item added to scope!", "success");
          }
        } catch (err) {
          console.error(err);
        }
      });
    }
  }

  setupSettingsModal() {
    const btnOpen = document.getElementById("btn-open-settings");
    const modal = document.getElementById("modal-settings");
    const btnClose1 = document.getElementById("btn-close-settings");
    const btnClose2 = document.getElementById("btn-close-settings-2");
    const btnSave = document.getElementById("btn-save-calle-key");
    const inputKey = document.getElementById("input-calle-key");

    if (btnOpen && modal) {
      btnOpen.addEventListener("click", () => modal.classList.add("active"));
    }
    const close = () => modal && modal.classList.remove("active");
    if (btnClose1) btnClose1.addEventListener("click", close);
    if (btnClose2) btnClose2.addEventListener("click", close);

    if (btnSave && inputKey) {
      btnSave.addEventListener("click", async () => {
        const key = inputKey.value.trim();
        try {
          const res = await fetch("http://127.0.0.1:8000/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ calle_api_key: key }),
          });
          if (res.ok) {
            this.showToast("CALL-E API key saved successfully!", "success");
            close();
            this.checkSettings();
          }
        } catch (e) {
          console.error(e);
        }
      });
    }
  }

  async checkSettings() {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/settings");
      if (!res.ok) return;
      const data = await res.json();
      const statusText = document.getElementById("calle-status-text");
      const badge = document.getElementById("header-calle-status");

      if (data.calle_ready) {
        if (statusText) statusText.innerText = "CALL-E: Live SDK Active";
        if (badge) badge.style.borderColor = "rgba(16, 185, 129, 0.4)";
      } else {
        if (statusText) statusText.innerText = "CALL-E: Interactive Sandbox Mode";
      }
    } catch (e) {
      console.warn(e);
    }
  }
}

// Instantiate and start
window.addEventListener("DOMContentLoaded", () => {
  window.contractorPilotApp = new ContractorPilotApp();
  window.renovaiApp = window.contractorPilotApp; // Alias for backward compatibility
  window.contractorPilotApp.init();
});
