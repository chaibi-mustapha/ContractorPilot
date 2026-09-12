/**
 * ContractorPilot — AI Call Center CALL-E Live Stream & Audio Controller
 * Drives the live autonomous call monitor, WebSocket events, canvas audio visualizer,
 * and authentic human neural voice playback (Sarah Jenkins, Marcus Reed, Mark Stevens, Elena Rodriguez)
 * in perfect sync with live call transcripts.
 */

class CalleCallCenter {
  constructor() {
    this.ws = null;
    this.currentProjectId = "proj-apt-f4";
    this.timerInterval = null;
    this.secondsElapsed = 0;
    this.canvas = null;
    this.ctx = null;
    this.animFrameId = null;
    this.wavePhase = 0;
    this.isCallActive = false;

    // Audio Playback Engine
    this.currentAudio = null;
    this.activeAudioTrack = "audio/dialog_calle_and_apex_tile.mp3";
    this.isPlayingAudio = false;

    // Available Live Demo Scenarios
    this.scenarios = {
      apex_tile: {
        id: "apex_tile",
        audioSrc: "audio/dialog_calle_and_apex_tile.mp3",
        avatar: "🧱",
        targetName: "Apex Tile & Stone Direct (Sarah Jenkins)",
        targetDesc: "Sourcing 520 sq ft Calacatta Porcelain Tiles 24x24",
        targetPhone: "+1-555-019-2831 (Sarah Jenkins, Pro Desk)",
        trackBadge: "🎙️ 2-Way Call: Sarah Jenkins (Apex Tile)",
        turns: [
          { speaker: "contact", name: "Sarah Jenkins (Supplier)", text: "Apex Tile and Stone, Sarah speaking. How can I help you today?", startTime: 0.0, endTime: 5.45 },
          { speaker: "ai", name: "CALL-E (AI Agent)", text: "Hello Sarah! This is CALL-E, autonomous procurement copilot for ContractorPilot. We are sourcing 520 sq ft of 24x24 Calacatta porcelain floor tiles for an active condo remodel in Metro Area. Do you have that in stock, and what is your best contractor rate?", startTime: 5.45, endTime: 23.35 },
          { speaker: "contact", name: "Sarah Jenkins (Supplier)", text: "Hi CALL-E! Yes, we have five pallets ready in our warehouse. For 520 sq ft, our wholesale rate is $4.20 per sq ft, down from $4.50. And we'll deliver it to the jobsite in 48 hours with no freight charge.", startTime: 23.35, endTime: 41.52 },
          { speaker: "ai", name: "CALL-E (AI Agent)", text: "That's fantastic. $4.20 per sq ft with free jobsite delivery confirmed. I have captured your quote and added it to our master project proposal. Thank you, Sarah!", startTime: 41.52, endTime: 52.97 },
          { speaker: "contact", name: "Sarah Jenkins (Supplier)", text: "You got it! I've reserved the lot for ContractorPilot. Have a great day!", startTime: 52.97, endTime: 59.64 }
        ],
        extracted: { price: "$4.20 / sq ft", discount: "6.7 % ($4.20 vs $4.50)", stock: "In Stock (5 Pallets)", delay: "2 business days (Free Freight)" }
      },
      marcus_tiler: {
        id: "marcus_tiler",
        audioSrc: "audio/dialog_calle_and_marcus_tiler.mp3",
        avatar: "🔨",
        targetName: "Marcus Reed (Master Tile Setter)",
        targetDesc: "Labor: 520 sq ft Porcelain & Curbless Shower Pan",
        targetPhone: "+1-555-018-1122 (Marcus Reed, Master Tiler)",
        trackBadge: "🎙️ 2-Way Call: Marcus Reed (Master Tiler)",
        turns: [
          { speaker: "contact", name: "Marcus Reed (Tiler)", text: "Marcus Reed here. What project do you have for me?", startTime: 0.0, endTime: 4.63 },
          { speaker: "ai", name: "CALL-E (AI Agent)", text: "Hi Marcus! CALL-E calling on behalf of ContractorPilot. We have a 520 sq ft porcelain tile scope for the Miller Residence remodel, including kitchen floors and a curbless master shower. What is your current day rate and estimated duration?", startTime: 4.63, endTime: 19.92 },
          { speaker: "contact", name: "Marcus Reed (Tiler)", text: "Sounds like a solid job. My day rate is $425. For that layout with the shower pan slope and leveling, I'll need four days. I can start next Tuesday.", startTime: 19.92, endTime: 33.58 },
          { speaker: "ai", name: "CALL-E (AI Agent)", text: "Perfect. 4 days at $425 per day, starting next Tuesday. I've logged your terms into the project schedule and cost sheet. Thanks Marcus!", startTime: 33.58, endTime: 43.49 },
          { speaker: "contact", name: "Marcus Reed (Tiler)", text: "Awesome. Text me the jobsite address and lockbox code on Monday. Catch you later!", startTime: 43.49, endTime: 51.07 }
        ],
        extracted: { price: "$425 / day", discount: "Confirmed Rate", stock: "Available next Tuesday", delay: "4 working days" }
      },
      sherwin_paint: {
        id: "sherwin_paint",
        audioSrc: "audio/dialog_calle_and_sherwin_paint.mp3",
        avatar: "🎨",
        targetName: "Sherwin ProFinish Coatings (Mark Stevens)",
        targetDesc: "Sourcing 10 gal Ultra Durable Velvet Matte (Alabaster)",
        targetPhone: "+1-555-019-5566 (Mark Stevens, Commercial)",
        trackBadge: "🎙️ 2-Way Call: Mark Stevens (Sherwin Paint)",
        turns: [
          { speaker: "contact", name: "Mark Stevens (Supplier)", text: "Sherwin ProFinish, Mark speaking at the contractor desk.", startTime: 0.0, endTime: 4.13 },
          { speaker: "ai", name: "CALL-E (AI Agent)", text: "Hello Mark, CALL-E here from ContractorPilot. We need 10 gallons of Ultra Durable velvet matte interior paint in Alabaster tone for an interior remodel. Can you confirm stock and your wholesale contractor price?", startTime: 4.13, endTime: 17.59 },
          { speaker: "contact", name: "Mark Stevens (Supplier)", text: "Hey CALL-E! Yep, plenty in stock. On your pro account, that's $58 a gallon, saving you about $7 a gallon. I can have all 10 gallons tinted and ready for will-call pickup by 2 PM today, or courier delivery tomorrow morning.", startTime: 17.59, endTime: 34.68 },
          { speaker: "ai", name: "CALL-E (AI Agent)", text: "Confirmed at $58 per gallon for 10 gallons. I have logged this offer in our procurement system. Thank you Mark!", startTime: 34.68, endTime: 41.69 },
          { speaker: "contact", name: "Mark Stevens (Supplier)", text: "Anytime! It'll be labeled under ContractorPilot at the counter. Have a good one!", startTime: 41.69, endTime: 48.96 }
        ],
        extracted: { price: "$58 / gal", discount: "-10.7% ($7 off list)", stock: "In Stock (Will-Call ready)", delay: "Same day / Next day" }
      },
      elena_artisan: {
        id: "elena_artisan",
        audioSrc: "audio/dialog_calle_and_elena_artisan.mp3",
        avatar: "🚿",
        targetName: "Elena Rodriguez (Tile & Waterproofing)",
        targetDesc: "Labor: Master Bath Waterproof Membrane & Curbless Shower",
        targetPhone: "+1-555-018-9900 (Elena Rodriguez, Finishes)",
        trackBadge: "🎙️ 2-Way Call: Elena Rodriguez (Waterproofing)",
        turns: [
          { speaker: "contact", name: "Elena Rodriguez (Artisan)", text: "Elena Rodriguez Tile and Waterproofing, how can I help?", startTime: 0.0, endTime: 4.22 },
          { speaker: "ai", name: "CALL-E (AI Agent)", text: "Hi Elena! This is CALL-E from ContractorPilot. We have a master bathroom remodel requiring full waterproof membrane and curbless shower prep. What is your day rate and availability?", startTime: 4.22, endTime: 15.28 },
          { speaker: "contact", name: "Elena Rodriguez (Artisan)", text: "Hi! For curbless waterproofing and walls, my rate is $400 a day. It's a three-day scope, and I provide a 10-year moisture warranty. I can start next Thursday.", startTime: 15.28, endTime: 27.42 },
          { speaker: "ai", name: "CALL-E (AI Agent)", text: "Noted: 3 days at $400 a day with 10-year warranty, starting next Thursday. Terms captured and scored in our proposal builder. Thank you, Elena!", startTime: 27.42, endTime: 37.24 },
          { speaker: "contact", name: "Elena Rodriguez (Artisan)", text: "Perfect! Looking forward to working with ContractorPilot. Bye!", startTime: 37.24, endTime: 42.14 }
        ],
        extracted: { price: "$400 / day", discount: "10-Yr Moisture Warranty", stock: "Starts next Thursday", delay: "3 working days" }
      }
    };

    this.currentScenarioKey = "apex_tile";
  }

  init(projectId) {
    this.currentProjectId = projectId;
    this.setupCanvas();
    this.setupAudioControls();
    this.connectWebSocket();
  }

  setupCanvas() {
    this.canvas = document.getElementById("call-wave-canvas");
    if (this.canvas) {
      this.ctx = this.canvas.getContext("2d");
      this.drawIdleWave();
    }
  }

  setupAudioControls() {
    const playBtn = document.getElementById("btn-play-monitor-audio");
    if (playBtn) {
      playBtn.addEventListener("click", () => {
        this.togglePlayCallAudio();
      });
    }
  }

  connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/calls/${this.currentProjectId}`;

    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.onopen = () => console.log("[CALL-E WS] Connected to live call stream.");
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleStreamEvent(data);
        } catch (e) {
          console.error("Error parsing WS event:", e);
        }
      };
      this.ws.onclose = () => {
        setTimeout(() => this.connectWebSocket(), 3000);
      };
    } catch (e) {
      console.warn("WebSocket initialization:", e);
    }
  }

  // ------------------ Canvas Waveform Animation ------------------

  startWaveAnimation() {
    this.isCallActive = true;
    const render = () => {
      if (!this.isCallActive) return;
      this.drawActiveWave();
      this.wavePhase += 0.08;
      this.animFrameId = requestAnimationFrame(render);
    };
    render();
  }

  stopWaveAnimation() {
    this.isCallActive = false;
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    this.drawIdleWave();
  }

  drawIdleWave() {
    if (!this.ctx || !this.canvas) return;
    const w = this.canvas.width;
    const h = this.canvas.height;
    this.ctx.clearRect(0, 0, w, h);

    this.ctx.beginPath();
    this.ctx.moveTo(0, h / 2);
    this.ctx.lineTo(w, h / 2);
    this.ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
    this.ctx.lineWidth = 2;
    this.ctx.stroke();
  }

  drawActiveWave() {
    if (!this.ctx || !this.canvas) return;
    const w = this.canvas.width;
    const h = this.canvas.height;
    this.ctx.clearRect(0, 0, w, h);

    const grad = this.ctx.createLinearGradient(0, 0, w, 0);
    grad.addColorStop(0, "#06B6D4");
    grad.addColorStop(0.5, "#6366F1");
    grad.addColorStop(1, "#8B5CF6");

    this.ctx.beginPath();
    this.ctx.lineWidth = 3;
    this.ctx.strokeStyle = grad;

    for (let x = 0; x < w; x++) {
      const freq1 = 0.02;
      const freq2 = 0.04;
      const y = h / 2 +
        Math.sin(x * freq1 + this.wavePhase) * 18 * Math.sin(this.wavePhase * 0.7) +
        Math.cos(x * freq2 - this.wavePhase) * 10;
      if (x === 0) this.ctx.moveTo(x, y);
      else this.ctx.lineTo(x, y);
    }
    this.ctx.stroke();
  }

  // ------------------ Real Neural Audio Playback ------------------

  loadScenario(scenarioKey) {
    if (this.isPlayingAudio) {
      this.stopCurrentAudio();
    }
    this.currentScenarioKey = scenarioKey || "apex_tile";
    const sc = this.scenarios[this.currentScenarioKey] || this.scenarios["apex_tile"];

    const targetName = document.getElementById("monitor-target-name");
    const targetDesc = document.getElementById("monitor-target-desc");
    const targetPhone = document.getElementById("monitor-target-phone");
    const targetAvatar = document.getElementById("monitor-target-avatar");
    const trackName = document.getElementById("monitor-audio-track-name");
    const trackBadge = document.getElementById("monitor-audio-badge");

    if (targetName) targetName.innerText = sc.targetName;
    if (targetDesc) targetDesc.innerText = sc.targetDesc;
    if (targetPhone) targetPhone.innerText = sc.targetPhone;
    if (targetAvatar) targetAvatar.innerText = sc.avatar;
    if (trackName) trackName.innerText = sc.targetName;
    if (trackBadge) trackBadge.innerText = sc.trackBadge;

    const transcriptBox = document.getElementById("monitor-transcript-messages");
    if (transcriptBox) {
      transcriptBox.innerHTML = `
        <div class="transcript-placeholder">
          <span>Click "Play Audio Call" to listen to the live voice negotiation with ${sc.targetName}</span>
        </div>
      `;
    }

    const extBox = document.getElementById("monitor-extracted-box");
    if (extBox) extBox.style.display = "none";
  }

  togglePlayCallAudio() {
    if (this.isPlayingAudio) {
      this.pauseCallAudio();
    } else {
      this.playCallAudio();
    }
  }

  playCallAudio() {
    const sc = this.scenarios[this.currentScenarioKey] || this.scenarios["apex_tile"];
    if (!this.currentAudio || this.currentAudio.src.indexOf(sc.audioSrc) === -1) {
      if (this.currentAudio) {
        this.currentAudio.pause();
      }
      this.currentAudio = new Audio(sc.audioSrc);
    }

    const stateText = document.getElementById("monitor-call-state-text");
    const durationTag = document.getElementById("monitor-call-duration");
    const transcriptBox = document.getElementById("monitor-transcript-messages");
    const extBox = document.getElementById("monitor-extracted-box");
    const playIcon = document.getElementById("monitor-audio-play-icon");
    const playText = document.getElementById("monitor-audio-play-text");

    if (transcriptBox) transcriptBox.innerHTML = "";
    if (stateText) stateText.innerText = "IN CALL (LIVE NEURAL AUDIO)";
    if (playIcon) playIcon.innerText = "⏸️";
    if (playText) playText.innerText = "Pause Call Audio";

    this.startWaveAnimation();
    this.isPlayingAudio = true;

    // Time updates & synchronized dialogue streaming (turns appear strictly AFTER vocal ends)
    let displayedIndices = new Set();
    this.currentAudio.ontimeupdate = () => {
      const curTime = this.currentAudio.currentTime;
      const mins = String(Math.floor(curTime / 60)).padStart(2, "0");
      const secs = String(Math.floor(curTime % 60)).padStart(2, "0");
      if (durationTag) durationTag.innerText = `${mins}:${secs}`;

      // 1. Detect if a speaker is actively talking right now
      let activeSpeakingTurn = null;
      sc.turns.forEach((turn) => {
        if (curTime >= turn.startTime && curTime < turn.endTime) {
          activeSpeakingTurn = turn;
        }
      });

      // 2. Render turn text ONLY after that speaker has FINISHED speaking!
      sc.turns.forEach((turn, idx) => {
        if (curTime >= turn.endTime && !displayedIndices.has(idx)) {
          displayedIndices.add(idx);
          if (transcriptBox) {
            const liveInd = document.getElementById("live-speaking-indicator");
            if (liveInd) liveInd.remove();

            const msg = document.createElement("div");
            msg.className = `transcript-msg ${turn.speaker}`;
            msg.innerHTML = `<strong>${turn.name}:</strong> ${turn.text}`;
            transcriptBox.appendChild(msg);

            // Autoscroll strictly to bottom as messages fill or exceed card
            this.scrollTranscriptToBottom();
          }
        }
      });

      // 3. Live speaking indicator while vocal piece is playing
      if (transcriptBox && activeSpeakingTurn) {
        let liveInd = document.getElementById("live-speaking-indicator");
        if (!liveInd) {
          liveInd = document.createElement("div");
          liveInd.id = "live-speaking-indicator";
          transcriptBox.appendChild(liveInd);
        }
        liveInd.className = `transcript-msg ${activeSpeakingTurn.speaker} speaking-live`;
        liveInd.innerHTML = `<strong>${activeSpeakingTurn.name}:</strong> 🎙️ <em>Speaking...</em> <span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>`;
        this.scrollTranscriptToBottom();
      } else {
        const liveInd = document.getElementById("live-speaking-indicator");
        if (liveInd) liveInd.remove();
      }

      // Show extracted terms at 70% of call
      if (this.currentAudio.duration && curTime >= this.currentAudio.duration * 0.7) {
        if (extBox && extBox.style.display !== "block") {
          extBox.style.display = "block";
          const p = document.getElementById("live-extract-price");
          const d = document.getElementById("live-extract-discount");
          const s = document.getElementById("live-extract-stock");
          const del = document.getElementById("live-extract-delay");

          if (p) p.innerText = sc.extracted.price;
          if (d) d.innerText = sc.extracted.discount;
          if (s) s.innerText = sc.extracted.stock;
          if (del) del.innerText = sc.extracted.delay;

          const app = window.contractorPilotApp;
          if (app && app.showToast) {
            app.showToast(`Terms agreed with ${sc.targetName}!`, "success");
          }
          this.scrollTranscriptToBottom();
        }
      }
    };

    this.currentAudio.onended = () => {
      const liveInd = document.getElementById("live-speaking-indicator");
      if (liveInd) liveInd.remove();
      this.scrollTranscriptToBottom();

      this.isPlayingAudio = false;
      this.stopWaveAnimation();
      if (stateText) stateText.innerText = "CALL COMPLETED (OFFER SAVED)";
      if (playIcon) playIcon.innerText = "▶️";
      if (playText) playText.innerText = "Replay Call Audio";

      const app = window.contractorPilotApp;
      if (app) {
        app.loadProjectDetails(this.currentProjectId);
        if (app.showToast) {
          app.showToast("Verified offer saved to master comparison!", "success");
        }
      }
    };

    this.currentAudio.play().catch((e) => {
      console.warn("Audio autoplay policy:", e);
    });
  }

  pauseCallAudio() {
    if (this.currentAudio) {
      this.currentAudio.pause();
    }
    this.isPlayingAudio = false;
    this.stopWaveAnimation();

    const stateText = document.getElementById("monitor-call-state-text");
    const playIcon = document.getElementById("monitor-audio-play-icon");
    const playText = document.getElementById("monitor-audio-play-text");

    if (stateText) stateText.innerText = "CALL PAUSED";
    if (playIcon) playIcon.innerText = "▶️";
    if (playText) playText.innerText = "Resume Call Audio";
  }

  stopCurrentAudio() {
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.currentAudio = null;
    }
    this.isPlayingAudio = false;
    this.stopWaveAnimation();

    const playIcon = document.getElementById("monitor-audio-play-icon");
    const playText = document.getElementById("monitor-audio-play-text");
    if (playIcon) playIcon.innerText = "▶️";
    if (playText) playText.innerText = "Play Audio Call";
  }

  // Called automatically when user clicks batch procurement
  simulateDemoCallFlow() {
    this.loadScenario("apex_tile");
    // Play with small delay so user has seen the cards
    setTimeout(() => {
      this.playCallAudio();
    }, 800);
  }

  scrollTranscriptToBottom() {
    const transcriptBox = document.getElementById("monitor-transcript-messages");
    if (!transcriptBox) return;
    transcriptBox.scrollTo({
      top: transcriptBox.scrollHeight,
      behavior: "smooth"
    });
    // Ensure scroll reaches absolute bottom even with active animations
    setTimeout(() => {
      transcriptBox.scrollTop = transcriptBox.scrollHeight;
    }, 40);
  }

  handleStreamEvent(event) {
    if (event.type === "project_updated") {
      const app = window.contractorPilotApp;
      if (app) {
        app.loadProjectDetails(this.currentProjectId);
      }
    }
  }
}

window.calleCenter = new CalleCallCenter();
