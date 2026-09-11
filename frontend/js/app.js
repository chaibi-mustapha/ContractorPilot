/**
 * ContractorPilot — Application Core Controller (4-Step Guided Workflow)
 * Étape 1 : Visite de Chantier & Dictée Vocale
 * Étape 2 : Vérification des Travaux par Métier & Matériaux
 * Étape 3 : Consultation & Appels Vocaux Autonomes CALL-E
 * Étape 4 : Bilan Comparatif & Devis Client Pro
 */

class ContractorPilotApp {
  constructor() {
    this.currentProjectId = "proj-apt-f4";
    this.projectData = null;
    this.currentStep = 1;
    this.suppliers = [];
    this.tradespeople = [];
    this.marginPercent = 20.0;
    this.currency = "DA";
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

  async init() {
    this.setupStepper();
    this.setupSpeechRecognition();
    this.setupEventListeners();
    await this.checkSettings();
    await this.loadProjectDetails(this.currentProjectId);
    window.calleCenter.init(this.currentProjectId);
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
      this.recognition.lang = "fr-FR";
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
    if (statusText) statusText.innerText = "🔴 Enregistrement en cours... Parlez de votre chantier";

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
    if (statusText) statusText.innerText = "Dictée terminée. Vous pouvez vérifier le texte ci-dessous.";

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
      counter.innerText = `${words.length} mot${words.length > 1 ? "s" : ""}`;
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
          textarea.value = "Visite de chantier Appartement F4 120m2 chez Famille Benali. Grand Salon de 38m² : déposer l'ancien carrelage, poser du carrelage grès cérame 60x60 effet marbre avec plinthes assorties, refaire la peinture de tous les murs en blanc satiné lavable, et prévoir l'installation de 12 spots LED au plafond avec variateur. Cuisine ouverte de 16m² : faïence murale crédence métro, remplacement robinetterie par mitigeur avec douchette, et peinture anti-humidité au plafond. Salle de bain principale de 8m² : étanchéité douche à l'italienne, meuble vasque et mitigeur noir mat, carrelage antidérapant. Côté artisans, prévoir carreleur 4 jours, peintre 3 jours, électricien 2 jours et plombier 2 jours.";
          this.updateWordCount();
        }
      });
    }

    const btnDemoLight = document.getElementById("btn-demo-prompt-light");
    if (btnDemoLight) {
      btnDemoLight.addEventListener("click", () => {
        if (textarea) {
          textarea.value = "Visite rénovation électrique et peinture. Salon et chambres : reprise de tous les murs avec enduit et peinture blanche satinée 35 Litres, fourniture et pose de 18 spots encastrés LED dimmables. Prévoir électricien 2 jours et peintre 3 jours.";
          this.updateWordCount();
          this.showToast("Preset Électricité & Peinture chargé !", "info");
        }
      });
    }

    const btnDemoBath = document.getElementById("btn-demo-prompt-bath");
    if (btnDemoBath) {
      btnDemoBath.addEventListener("click", () => {
        if (textarea) {
          textarea.value = "Visite rénovation salle de bain 8m² et sanitaires. Dépose ancien carrelage mural, étanchéité complète sous carrelage douche italienne, pose faïence murale 10m², fourniture et pose mitigeur thermostatique noir mat et meuble vasque céramique 80cm. Prévoir plombier 2 jours et carreleur 2 jours.";
          this.updateWordCount();
          this.showToast("Preset Salle de Bain & Sanitaires chargé !", "info");
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
        this.showToast(`Marge fixée à ${val}%`, "info");
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

      // Start with empty clean slate for new site visit notes
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
      alert("Veuillez d'abord dicter ou saisir vos remarques de visite de chantier.");
      return;
    }

    const btnExtract = document.getElementById("btn-extract-voice");
    const originalText = btnExtract ? btnExtract.innerHTML : "";
    if (btnExtract) {
      btnExtract.disabled = true;
      btnExtract.innerHTML = "⏳ Analyse IA en cours...";
    }

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/projects/${this.currentProjectId}/voice-extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ voice_text: text, replace_existing: true }),
      });

      if (!res.ok) {
        throw new Error("Erreur lors de l'extraction des besoins.");
      }

      const result = await res.json();
      await this.loadProjectDetails(this.currentProjectId);
      this.goToStep(2);
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
        chip.innerHTML = `📍 <span>${room.name}</span> : <strong>${room.surface} m²</strong>`;
        roomsContainer.appendChild(chip);
      });
      if (!this.projectData.rooms || this.projectData.rooms.length === 0) {
        roomsContainer.innerHTML = `<span style="color: var(--text-dim); font-size: 0.85rem;">Aucune pièce enregistrée</span>`;
      }
    }

    // Split requirements: Labor (Trades) vs Materials
    const requirements = this.projectData.requirements || [];
    const trades = requirements.filter(
      (r) => r.item_type === "labor" || r.category === "Main-d'œuvre" || ["Carreleur", "Peintre", "Électricien", "Plombier", "Menuisier"].includes(r.category)
    );
    const materials = requirements.filter(
      (r) => r.item_type === "material" && !["Main-d'œuvre", "Carreleur", "Peintre", "Électricien", "Plombier", "Menuisier"].includes(r.category)
    );

    // Calcul du Total Estimatif Indicatif Pré-Négociation
    let totalEstimate = 0;
    requirements.forEach((r) => {
      totalEstimate += (parseFloat(r.quantity) || 1) * (parseFloat(r.estimated_unit_price) || 0);
    });
    const preEstimateEl = document.getElementById("pre-estimate-val");
    if (preEstimateEl) {
      preEstimateEl.innerText = `${Math.round(totalEstimate).toLocaleString()} DA`;
    }

    // Compteurs des Onglets de Filtres
    const countAll = document.getElementById("filter-count-all");
    const countLabor = document.getElementById("filter-count-labor");
    const countMat = document.getElementById("filter-count-material");
    if (countAll) countAll.innerText = requirements.length;
    if (countLabor) countLabor.innerText = trades.length;
    if (countMat) countMat.innerText = materials.length;

    // Update Counts Labels
    const tradesCountLabel = document.getElementById("trades-count-label");
    const matCountLabel = document.getElementById("materials-count-label");
    if (tradesCountLabel) tradesCountLabel.innerText = `${trades.length} corps d'état qualifiés requis`;
    if (matCountLabel) matCountLabel.innerText = `${materials.length} références à approvisionner`;

    // 2. Render Trades List
    const tradesList = document.getElementById("trades-tasks-list");
    if (tradesList) {
      tradesList.innerHTML = "";
      trades.forEach((item) => {
        const row = document.createElement("div");
        row.className = "need-item-card";

        let badgeClass = "badge-carreleur";
        if (item.category.includes("Peintre")) badgeClass = "badge-peintre";
        else if (item.category.includes("Électricien")) badgeClass = "badge-electricien";
        else if (item.category.includes("Plombier")) badgeClass = "badge-plombier";

        row.innerHTML = `
          <div class="need-item-main">
            <span class="need-badge-trade ${badgeClass}">🔨 ${item.category}</span>
            <div class="need-item-title">${item.item_name}</div>
            <div class="need-item-meta">
              <span>Durée : <strong>${item.quantity} ${item.unit}</strong></span> | 
              <span>Taux indicatif : <strong>${Number(item.estimated_unit_price).toLocaleString()} DA/${item.unit}</strong></span>
            </div>
          </div>
          <div class="need-item-actions">
            <button class="btn-delete-need" onclick="window.renovaiApp.deleteRequirement('${item.id}')" title="Supprimer">
              🗑️
            </button>
          </div>
        `;
        tradesList.appendChild(row);
      });

      if (trades.length === 0) {
        tradesList.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem;">Aucun corps de métier détecté. Vous pouvez en ajouter un manuellement.</div>`;
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
              <span>Quantité : <strong>${item.quantity} ${item.unit}</strong></span> | 
              <span>P.U. estimé : <strong>${Number(item.estimated_unit_price).toLocaleString()} DA</strong></span>
            </div>
          </div>
          <div class="need-item-actions">
            <button class="btn-delete-need" onclick="window.renovaiApp.deleteRequirement('${item.id}')" title="Supprimer">
              🗑️
            </button>
          </div>
        `;
        materialsList.appendChild(row);
      });

      if (materials.length === 0) {
        materialsList.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem;">Aucun matériau listé. Vous pouvez en ajouter un manuellement.</div>`;
      }
    }

    // Appliquer le filtre courant
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
    const client = "Famille Benali (Appartement F4 — 120 m²)";
    const total = document.getElementById("fin-grand-total") ? document.getElementById("fin-grand-total").innerText : "0 DA";
    const mat = document.getElementById("fin-materials-cost") ? document.getElementById("fin-materials-cost").innerText : "0 DA";
    const lab = document.getElementById("fin-labor-cost") ? document.getElementById("fin-labor-cost").innerText : "0 DA";
    const margin = document.getElementById("fin-margin-val") ? document.getElementById("fin-margin-val").innerText : "0 DA";

    const summaryText = `🏗️ DEVIS CONTRACTORPILOT PRO — RÉNOVATION D'INTÉRIEUR\nClient: ${client}\nN° Devis: CP-2026-001\nFournitures Matériaux: ${mat}\nMain-d'œuvre & Pose: ${lab}\nMarge Commerciale (${this.marginPercent}%): ${margin}\n-----------------------------------\nTOTAL GÉNÉRAL NET: ${total}\nDevis certifié, négocié et validé via l'Agent Vocal CALL-E.`;

    if (navigator.clipboard) {
      navigator.clipboard.writeText(summaryText).then(() => {
        this.showToast("Synthèse du devis copiée dans le presse-papier !", "success");
      });
    } else {
      this.showToast("Synthèse du devis prête !", "info");
    }
  }

  async deleteRequirement(reqId) {
    if (!confirm("Voulez-vous supprimer ce besoin ?")) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/projects/${this.currentProjectId}/requirements/${reqId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        await this.loadProjectDetails(this.currentProjectId);
      }
    } catch (e) {
      console.error(e);
    }
  }

  // ------------------ Étape 3 : Consultation & Appels ------------------

  async launchBatchConsultation() {
    this.goToStep(3);

    const badgeStatus = document.getElementById("monitor-badge-status");
    const stateText = document.getElementById("monitor-call-state-text");
    if (stateText) stateText.innerText = "CONSULTATION EN COURS...";

    try {
      // 1. Call backend batch-procurement
      const res = await fetch(`http://127.0.0.1:8000/api/calls/batch-procurement`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: this.currentProjectId, is_live: false }),
      });

      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Erreur lors du lancement des appels");
        return;
      }

      await this.loadProjectDetails(this.currentProjectId);

      // 2. Animer un appel phare en direct pour la démo
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

    if (badge) badge.innerText = `${calls.length} appel${calls.length > 1 ? "s" : ""}`;
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
          <span style="color: var(--accent-emerald); font-weight: 600; font-size: 0.82rem;">✓ Négocié</span>
        `;
        container.appendChild(item);
      });

      if (calls.length === 0) {
        container.innerHTML = `<div style="color: var(--text-dim); font-size: 0.85rem; padding: 0.75rem;">Les appels passés apparaîtront ici.</div>`;
      }
    }
  }

  // ------------------ Étape 4 : Devis & Bilan ------------------

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

    if (matCost) matCost.innerText = `${Math.round(quote.materials_subtotal).toLocaleString()} DA`;
    if (labCost) labCost.innerText = `${Math.round(quote.labor_subtotal).toLocaleString()} DA`;
    if (marginVal) marginVal.innerText = `${Math.round(quote.margin_amount).toLocaleString()} DA`;
    if (grandTotal) grandTotal.innerText = `${Math.round(quote.grand_total).toLocaleString()} DA`;
    if (marginSub) marginSub.innerText = `Marge brute appliquée (${quote.margin_percent}%)`;

    // Printable Quote Sheet
    const subMat = document.getElementById("quote-subtotal-materials");
    const subLab = document.getElementById("quote-subtotal-labor");
    const totalDisplay = document.getElementById("quote-grand-total-display");

    if (subMat) subMat.innerText = `${Math.round(quote.materials_subtotal).toLocaleString()} DA`;
    if (subLab) subLab.innerText = `${Math.round(quote.labor_subtotal).toLocaleString()} DA`;
    if (totalDisplay) totalDisplay.innerText = `${Math.round(quote.grand_total).toLocaleString()} DA`;

    // Table body
    const tbody = document.getElementById("quote-table-body");
    if (tbody) {
      tbody.innerHTML = "";
      (quote.items || []).forEach((item) => {
        const tr = document.createElement("tr");
        const typeLabel = item.item_type === "labor" ? "Main-d'œuvre" : "Fourniture";
        tr.innerHTML = `
          <td>
            <strong>${item.description}</strong>
            <div style="font-size: 0.75rem; color: #64748B;">Source : ${item.supplier_or_trade}</div>
          </td>
          <td><span class="badge" style="background: rgba(100,116,139,0.15); color: #475569;">${typeLabel}</span></td>
          <td style="text-align: right;">${item.quantity} ${item.unit}</td>
          <td style="text-align: right;">${Number(item.unit_price).toLocaleString()} DA</td>
          <td style="text-align: right; font-weight: 700;">${Number(item.total_price).toLocaleString()} DA</td>
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

    // Group offers by requirement_id
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
        ? `<span class="offer-rank-badge" style="background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.35);">🥇 1er Choix Retenu</span>`
        : `<span class="offer-rank-badge" style="background: rgba(99, 102, 241, 0.15); color: #818CF8; border: 1px solid rgba(99, 102, 241, 0.35);">Offre Alternative</span>`;

      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            ${badgeHtml}
            <h4 style="font-family: var(--font-display); font-size: 1.05rem; margin-top: 0.35rem; color: var(--text-main); font-weight: 700;">${reqName}</h4>
          </div>
          <div style="font-family: var(--font-mono); font-weight: 700; color: var(--accent-emerald); font-size: 1.15rem;">
            ${Number(bestOffer.unit_price).toLocaleString()} DA
          </div>
        </div>
        <div style="font-size: 0.85rem; color: var(--text-muted);">
          Interlocuteur : <strong style="color: var(--text-main);">${bestOffer.target_name}</strong>
        </div>
        <div style="display: flex; gap: 0.8rem; font-size: 0.8rem; color: var(--text-muted); background: rgba(0,0,0,0.25); padding: 0.45rem 0.75rem; border-radius: var(--radius-sm); border: 1px solid rgba(255,255,255,0.05);">
          <span>Score IA : <strong style="color: var(--accent-cyan);">${bestOffer.calculated_score}/100</strong></span>
          <span>Délai : <strong>${bestOffer.delivery_days} j</strong></span>
          ${bestOffer.discount_percent > 0 ? `<span>Remise : <strong style="color: var(--accent-emerald);">-${bestOffer.discount_percent}%</strong></span>` : ""}
        </div>
      `;
      container.appendChild(card);
    });

    if (offers.length === 0) {
      container.innerHTML = `<div style="color: var(--text-dim); font-size: 0.9rem; padding: 1.5rem; text-align: center; grid-column: 1/-1;">Lancez la consultation CALL-E à l'étape 3 pour générer le bilan comparatif des offres.</div>`;
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
        if (catSelect) catSelect.value = "Carreleur";
        if (unitSelect) unitSelect.value = "jours";
      } else {
        if (catSelect) catSelect.value = "Sol / Carrelage";
        if (unitSelect) unitSelect.value = "m²";
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
          room_name: "Chantier Général",
          category: document.getElementById("req-modal-category").value,
          item_name: document.getElementById("req-modal-name").value,
          quantity: parseFloat(document.getElementById("req-modal-qty").value) || 1.0,
          unit: document.getElementById("req-modal-unit").value,
          item_type: document.getElementById("req-modal-type").value,
          estimated_unit_price: parseFloat(document.getElementById("req-modal-price").value) || 0.0,
          notes: "Ajouté manuellement par l'entrepreneur",
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
            alert("Clé API CALL-E mise à jour !");
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
        if (statusText) statusText.innerText = "CALL-E : Connecté (Live SDK)";
        if (badge) badge.style.borderColor = "rgba(16, 185, 129, 0.4)";
      } else {
        if (statusText) statusText.innerText = "CALL-E : Mode Démo Interactif";
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
