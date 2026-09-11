/**
 * ContractorPilot — AI Call Center CALL-E Live Stream & Waveform Controller
 * Drives the live autonomous call monitor, WebSocket events, canvas audio visualizer,
 * and realistic live simulation dialogue in English.
 */

class CalleCallCenter {
  constructor() {
    this.ws = null;
    this.currentProjectId = "proj-apt-f4";
    this.timerInterval = null;
    this.secondsElapsed = 0;
    this.audioCtx = null;
    this.canvas = null;
    this.ctx = null;
    this.animFrameId = null;
    this.wavePhase = 0;
    this.isCallActive = false;
  }

  init(projectId) {
    this.currentProjectId = projectId;
    this.setupCanvas();
    this.connectWebSocket();
  }

  setupCanvas() {
    this.canvas = document.getElementById("call-wave-canvas");
    if (this.canvas) {
      this.ctx = this.canvas.getContext("2d");
      this.drawIdleWave();
    }
  }

  connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/calls/${this.currentProjectId}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log("[CALL-E WS] Connected to live call stream.");
      };

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

  playSyntheticTone(freq = 440, type = "sine", duration = 0.15) {
    try {
      if (!this.audioCtx) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        this.audioCtx = new AudioContext();
      }
      if (this.audioCtx.state === "suspended") {
        this.audioCtx.resume();
      }
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, this.audioCtx.currentTime);
      gain.gain.setValueAtTime(0.08, this.audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + duration);
      osc.connect(gain);
      gain.connect(this.audioCtx.destination);
      osc.start();
      osc.stop(this.audioCtx.currentTime + duration);
    } catch (e) {
      // Browser autoplay policy
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

    // Dynamic gradient
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

  // ------------------ Live Demo Sequence ------------------

  simulateLiveDemoCall() {
    const stateText = document.getElementById("monitor-call-state-text");
    const durationTag = document.getElementById("monitor-call-duration");
    const targetName = document.getElementById("monitor-target-name");
    const targetDesc = document.getElementById("monitor-target-desc");
    const targetPhone = document.getElementById("monitor-target-phone");
    const targetAvatar = document.getElementById("monitor-target-avatar");
    const transcriptBox = document.getElementById("monitor-transcript-messages");
    const extBox = document.getElementById("monitor-extracted-box");

    // Contact info
    if (targetAvatar) targetAvatar.innerText = "🧱";
    if (targetName) targetName.innerText = "Apex Tile & Stone Direct";
    if (targetDesc) targetDesc.innerText = "Negotiating Porcelain Floor Tiles 24x24 (520 sq ft)";
    if (targetPhone) targetPhone.innerText = "+1-555-019-2831 (Metro Warehouse Direct)";
    if (stateText) stateText.innerText = "DIALING & RINGING...";
    if (transcriptBox) transcriptBox.innerHTML = "";
    if (extBox) extBox.style.display = "none";

    this.playSyntheticTone(440, "sine", 0.3);
    this.startWaveAnimation();

    this.secondsElapsed = 0;
    clearInterval(this.timerInterval);
    this.timerInterval = setInterval(() => {
      this.secondsElapsed++;
      const mins = String(Math.floor(this.secondsElapsed / 60)).padStart(2, "0");
      const secs = String(this.secondsElapsed % 60).padStart(2, "0");
      if (durationTag) durationTag.innerText = `${mins}:${secs}`;
    }, 1000);

    const dialogTurns = [
      {
        speaker: "contact",
        name: "Supplier (Brian)",
        text: "Apex Tile & Stone Direct, this is Brian, how can I help you today?",
        delay: 2000,
      },
      {
        speaker: "ai",
        name: "CALL-E (AI Agent)",
        text: "Hi Brian, I'm calling from ContractorPilot on behalf of a residential remodel jobsite. Do you have 520 sq ft of 24x24 Calacatta marble porcelain tiles in stock?",
        delay: 4500,
      },
      {
        speaker: "contact",
        name: "Supplier (Brian)",
        text: "Yes we do! We've got 650 sq ft available right now at our regional warehouse. List contractor pricing is $4.50 per sq ft.",
        delay: 7500,
      },
      {
        speaker: "ai",
        name: "CALL-E (AI Agent)",
        text: "What is your turnaround for direct freight delivery, and can you apply any volume discount for our project?",
        delay: 11000,
      },
      {
        speaker: "contact",
        name: "Supplier (Brian)",
        text: "We can deliver direct via flatbed within 3 business days. For 520 sq ft, I can lock in a 5% trade discount, bringing it to $4.25 per sq ft.",
        delay: 14500,
      },
      {
        speaker: "ai",
        name: "CALL-E (AI Agent)",
        text: "Confirmed: $4.25 per sq ft with a 5% volume discount, 650 sq ft in stock, delivery in 3 days. Thank you Brian!",
        delay: 18000,
      },
    ];

    dialogTurns.forEach((turn) => {
      setTimeout(() => {
        if (stateText) stateText.innerText = "IN CALL (LIVE VOICE STREAM)";
        if (transcriptBox) {
          const msg = document.createElement("div");
          msg.className = `transcript-msg ${turn.speaker}`;
          msg.innerHTML = `<strong>${turn.name}:</strong> ${turn.text}`;
          transcriptBox.appendChild(msg);
          transcriptBox.scrollTop = transcriptBox.scrollHeight;
        }
        this.playSyntheticTone(turn.speaker === "ai" ? 540 : 420, "sine", 0.08);
      }, turn.delay);
    });

    // Real-time structured extraction at 16s
    setTimeout(() => {
      if (extBox) extBox.style.display = "block";
      const p = document.getElementById("live-extract-price");
      const d = document.getElementById("live-extract-discount");
      const s = document.getElementById("live-extract-stock");
      const del = document.getElementById("live-extract-delay");

      if (p) p.innerText = "$4.25 / sq ft";
      if (d) d.innerText = "5 %";
      if (s) s.innerText = "In Stock (650 sq ft)";
      if (del) del.innerText = "3 business days";

      this.playSyntheticTone(880, "sine", 0.25);
      const app = window.contractorPilotApp || window.renovaiApp;
      if (app && app.showToast) {
        app.showToast("Volume trade discount negotiated: -5%!", "success");
      }
    }, 16000);

    // Call completed at 20.5s
    setTimeout(() => {
      clearInterval(this.timerInterval);
      this.stopWaveAnimation();
      if (stateText) stateText.innerText = "CALL COMPLETED (OFFER CAPTURED & SAVED)";
      this.playSyntheticTone(660, "triangle", 0.2);

      const app = window.contractorPilotApp || window.renovaiApp;
      if (app) {
        app.loadProjectDetails(this.currentProjectId);
        if (app.showToast) {
          app.showToast("Verified offer added to comparison matrix!", "success");
        }
      }
    }, 20500);
  }

  handleStreamEvent(event) {
    if (event.type === "project_updated") {
      const app = window.contractorPilotApp || window.renovaiApp;
      if (app) {
        app.loadProjectDetails(this.currentProjectId);
      }
    }
  }
}

window.calleCenter = new CalleCallCenter();
