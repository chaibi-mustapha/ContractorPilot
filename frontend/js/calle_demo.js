/**
 * RenovAI — AI Call Center CALL-E Live Stream & Waveform Controller
 * Drives the live autonomous call monitor, WebSocket events, canvas audio visualizer,
 * and realistic live simulation dialogue.
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
    if (targetName) targetName.innerText = "Comptoir Céramique Moderne";
    if (targetDesc) targetDesc.innerText = "Négociation Carrelage 60x60 (48 m²) & Faïence";
    if (targetPhone) targetPhone.innerText = "+213 550 12 34 56 (Grossiste Alger)";
    if (stateText) stateText.innerText = "NUMÉROTATION & SONNERIE...";
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
        name: "Fournisseur",
        text: "Allô bonjour, Comptoir Céramique Moderne, à votre service.",
        delay: 2000,
      },
      {
        speaker: "ai",
        name: "CALL-E (Agent IA)",
        text: "Bonjour, je suis l'assistant vocal ContractorPilot pour un chantier à Sidi Yahia. Avez-vous en stock 48 m² de carrelage grès cérame 60x60 effet marbre ?",
        delay: 4500,
      },
      {
        speaker: "contact",
        name: "Fournisseur",
        text: "Oui tout à fait, premier choix rectifié en stock immédiat à notre dépôt d'Alger. Le prix est de 2 650 DA le m².",
        delay: 7500,
      },
      {
        speaker: "ai",
        name: "CALL-E (Agent IA)",
        text: "Quel est le délai de livraison sur chantier, et pouvez-vous accorder une remise pour une commande globale avec faïence ?",
        delay: 11000,
      },
      {
        speaker: "contact",
        name: "Fournisseur",
        text: "Livraison possible dès demain en camion plateau (1 jour). Pour ce volume, nous appliquons 5% de remise commerciale ferme.",
        delay: 14500,
      },
      {
        speaker: "ai",
        name: "CALL-E (Agent IA)",
        text: "Excellent, offre validée à 2 650 DA avec 5% de remise et livraison sous 24h. Merci !",
        delay: 18000,
      },
    ];

    dialogTurns.forEach((turn) => {
      setTimeout(() => {
        if (stateText) stateText.innerText = "EN COMMUNICATION (AUDIO LIVE)";
        if (transcriptBox) {
          const msg = document.createElement("div");
          msg.className = `transcript-msg ${turn.speaker}`;
          msg.innerHTML = `<strong>${turn.name} :</strong> ${turn.text}`;
          transcriptBox.appendChild(msg);
          transcriptBox.scrollTop = transcriptBox.scrollHeight;
        }
        this.playSyntheticTone(turn.speaker === "ai" ? 540 : 420, "sine", 0.08);
      }, turn.delay);
    });

    // Extraction en direct à la 15ème seconde
    setTimeout(() => {
      if (extBox) extBox.style.display = "block";
      const p = document.getElementById("live-extract-price");
      const d = document.getElementById("live-extract-discount");
      const s = document.getElementById("live-extract-stock");
      const del = document.getElementById("live-extract-delay");

      if (p) p.innerText = "2 650 DA / m²";
      if (d) d.innerText = "5 %";
      if (s) s.innerText = "Disponible (120 m²)";
      if (del) del.innerText = "1 jour ouvré";

      this.playSyntheticTone(880, "sine", 0.25);
      if (window.renovaiApp && window.renovaiApp.showToast) {
        window.renovaiApp.showToast("Remise commerciale ferme négociée : -5% !", "success");
      }
    }, 16000);

    // Fin de l'appel
    setTimeout(() => {
      clearInterval(this.timerInterval);
      this.stopWaveAnimation();
      if (stateText) stateText.innerText = "APPEL TERMINÉ (OFFRE ENREGISTRÉE)";
      this.playSyntheticTone(660, "triangle", 0.2);

      if (window.renovaiApp) {
        window.renovaiApp.loadProjectDetails(this.currentProjectId);
        if (window.renovaiApp.showToast) {
          window.renovaiApp.showToast("Offre confirmée et intégrée au comparateur !", "success");
        }
      }
    }, 20500);
  }

  handleStreamEvent(event) {
    if (event.type === "project_updated") {
      if (window.renovaiApp) {
        window.renovaiApp.loadProjectDetails(this.currentProjectId);
      }
    }
  }
}

window.calleCenter = new CalleCallCenter();
