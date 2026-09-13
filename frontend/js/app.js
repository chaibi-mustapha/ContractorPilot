/**
 * ContractorPilot — Application Core Controller (4-Step Guided Workflow)
 * Step 1 : Jobsite Walkthrough & Voice Note Capture
 * Step 2 : AI Remodel Scope & Material Breakdown
 * Step 3 : CALL-E Autonomous Voice Procurement & Calling
 * Step 4 : Vendor Comparison & Official Client Proposal
 */

/**
 * High-Fidelity Cross-Browser WAV Recorder
 * Direct 16-bit PCM Mono 16kHz WAV generation for Google Gemini Multimodal Audio
 */
class WavAudioRecorder {
  constructor() {
    this.audioCtx = null;
    this.sourceNode = null;
    this.processorNode = null;
    this.silenceGain = null;
    this.chunks = [];
    this.sampleRate = 16000;
    this.maxVolume = 0;
    this.totalEnergy = 0;
    this.processCount = 0;
  }

  async start(stream) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return false;
    try {
      try {
        this.audioCtx = new AudioContextClass({ sampleRate: 16000 });
      } catch (e) {
        this.audioCtx = new AudioContextClass();
      }

      // CRITICAL: Ensure audio context is running (browsers often suspend after getUserMedia)
      if (this.audioCtx.state === "suspended") {
        await this.audioCtx.resume();
      }

      this.sampleRate = this.audioCtx.sampleRate || 16000;
      this.sourceNode = this.audioCtx.createMediaStreamSource(stream);
      // 4096 buffer size, 1 channel in, 1 channel out
      this.processorNode = this.audioCtx.createScriptProcessor(4096, 1, 1);
      this.chunks = [];
      this.maxVolume = 0;
      this.totalEnergy = 0;
      this.processCount = 0;

      this.processorNode.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        let sumSquares = 0;
        for (let i = 0; i < inputData.length; i++) {
          const v = inputData[i];
          sumSquares += v * v;
          if (Math.abs(v) > this.maxVolume) {
            this.maxVolume = Math.abs(v);
          }
        }
        const rms = Math.sqrt(sumSquares / inputData.length);
        this.totalEnergy += rms;
        this.processCount++;
        this.chunks.push(new Float32Array(inputData));
      };

      // Connect via muted gain node: keeps ScriptProcessor active without speaker feedback
      this.silenceGain = this.audioCtx.createGain();
      this.silenceGain.gain.value = 0;

      this.sourceNode.connect(this.processorNode);
      this.processorNode.connect(this.silenceGain);
      this.silenceGain.connect(this.audioCtx.destination);
      return true;
    } catch (e) {
      console.warn("[WavAudioRecorder] init failed, fallback to MediaRecorder:", e);
      return false;
    }
  }

  async stop() {
    const avgVolume = this.processCount > 0 ? (this.totalEnergy / this.processCount) : 0;
    const peakVolume = this.maxVolume;

    if (this.sourceNode) {
      try { this.sourceNode.disconnect(); } catch (e) {}
      this.sourceNode = null;
    }
    if (this.processorNode) {
      try { this.processorNode.disconnect(); } catch (e) {}
      this.processorNode = null;
    }
    if (this.silenceGain) {
      try { this.silenceGain.disconnect(); } catch (e) {}
      this.silenceGain = null;
    }
    if (this.audioCtx && this.audioCtx.state !== "closed") {
      try { await this.audioCtx.close(); } catch (e) {}
      this.audioCtx = null;
    }

    let totalLength = 0;
    for (const c of this.chunks) totalLength += c.length;
    if (totalLength === 0) return { blob: null, avgVolume: 0, peakVolume: 0 };

    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const c of this.chunks) {
      merged.set(c, offset);
      offset += c.length;
    }
    this.chunks = [];

    const blob = this.encodeWav(merged, this.sampleRate);
    return { blob, avgVolume, peakVolume, durationSec: totalLength / this.sampleRate };
  }

  encodeWav(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    const writeString = (offset, str) => {
      for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
      }
    };

    writeString(0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(8, "WAVE");
    writeString(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, 1, true); // Mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, "data");
    view.setUint32(40, samples.length * 2, true);

    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      let s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    return new Blob([buffer], { type: "audio/wav" });
  }
}

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

    // Speech & Audio Recording (Direct Gemini Multimodal Audio + WAV Recorder)
    this.wavRecorder = new WavAudioRecorder();
    this.isRecording = false;
    this.recognition = null;
    this.recordTimerInterval = null;
    this.recordSeconds = 0;
    this.dictationLang = "en-US";
    this.speechFinalTranscript = "";
    this.mediaStream = null;
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.currentAudioMimeType = "audio/wav";
    // API Base URL (dynamic for localhost, cloud deployment, and remote hosts)
    this.apiBase = (window.location.protocol.startsWith("http") && window.location.host) ? "" : "http://127.0.0.1:8000";
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
    this.initAudioStudio();
    this.resetWalkthroughTextarea();
    await this.checkSettings();
    await this.loadProjectDetails(this.currentProjectId);
    if (window.calleCenter) {
      window.calleCenter.init(this.currentProjectId);
    }
  }

  resetWalkthroughTextarea() {
    const textarea = document.getElementById("voice-transcription-input");
    if (textarea) {
      textarea.value = "";
      textarea.placeholder = "🎙️ Click the microphone on the left to dictate your walkthrough notes, or click a demo scenario below...";
      this.updateWordCount();
    }
  }

  // ------------------ Stepper Navigation ------------------

  isCallInProgress() {
    if (!window.calleCenter) return false;
    const cc = window.calleCenter;
    if (cc.isCallScheduled || cc.isPlayingAudio) return true;
    if (cc.currentAudio && !cc.currentAudio.paused && !cc.currentAudio.ended) return true;
    if (cc.currentAudio && cc.currentAudio.currentTime > 0 && !cc.callCompleted) return true;
    return false;
  }

  getVerifiedOffersCount() {
    if (!this.projectData || !Array.isArray(this.projectData.offers)) return 0;
    return this.projectData.offers.length;
  }

  updateStep3TransitionState() {
    const btnToStep4 = document.getElementById("btn-to-step-4");
    if (!btnToStep4) return;

    const inProgress = this.isCallInProgress();
    const offersCount = this.getVerifiedOffersCount();

    if (inProgress) {
      btnToStep4.innerHTML = `⏳ Call in Progress (Negotiating Terms...)`;
      btnToStep4.style.opacity = "0.85";
      btnToStep4.title = "Awaiting end of conversation to verify pricing and artisan availability";
    } else if (offersCount === 0) {
      btnToStep4.innerHTML = `🔒 Sourcing Required (0 Proposals)`;
      btnToStep4.style.opacity = "0.85";
      btnToStep4.title = "Launch CALL-E procurement calls first to collect verified quotes";
    } else {
      btnToStep4.innerHTML = `🏆 View Comparison & Client Proposal ➔ (${offersCount} Verified Proposals)`;
      btnToStep4.style.opacity = "1";
      btnToStep4.title = "Proceed to client proposal and offers matrix";
    }
  }

  showCallInProgressModal(mode = "call_in_progress") {
    const modal = document.getElementById("modal-call-in-progress");
    const iconEl = document.getElementById("modal-call-icon");
    const pulseEl = document.getElementById("modal-call-pulse");
    const badgeEl = document.getElementById("modal-call-target-badge");
    const titleEl = document.getElementById("modal-call-title");
    const descEl = document.getElementById("call-in-progress-desc");
    const actionsEl = document.getElementById("modal-call-actions");

    if (mode === "no_proposals") {
      if (iconEl) iconEl.innerText = "📋";
      if (pulseEl) pulseEl.style.background = "#f59e0b";
      if (badgeEl) {
        badgeEl.innerText = "Minimum Proposals Required";
        badgeEl.style.color = "#f59e0b";
      }
      if (titleEl) titleEl.innerText = "No Verified Proposals Collected";
      if (descEl) {
        descEl.innerHTML = `Without completed subcontractor or supplier calls, pricing, discounts, and artisan availability remain unknown.<br><br>A minimum of <strong>1 verified proposal</strong> is required before generating the comparison matrix and client proposal.`;
      }
      if (actionsEl) {
        actionsEl.innerHTML = `
          <button class="btn btn-secondary" id="btn-cancel-modal-proposals" style="padding: 0.7rem 1.4rem;">Cancel</button>
          <button class="btn btn-primary" id="btn-launch-from-modal" style="padding: 0.7rem 1.4rem; background: linear-gradient(135deg, var(--accent-cyan) 0%, var(--accent-blue) 100%); font-weight: 600;">📞 Launch Sourcing Calls Now</button>
        `;
        const btnCancel = document.getElementById("btn-cancel-modal-proposals");
        if (btnCancel) btnCancel.onclick = () => this.hideCallInProgressModal();
        const btnLaunch = document.getElementById("btn-launch-from-modal");
        if (btnLaunch) btnLaunch.onclick = () => {
          this.hideCallInProgressModal();
          this.launchBatchConsultation();
        };
      }
    } else {
      let targetName = "Supplier / Subcontractor";
      if (window.calleCenter) {
        const sc = window.calleCenter.scenarios[window.calleCenter.currentScenarioKey] || window.calleCenter.scenarios["apex_tile"];
        if (sc && sc.targetName) targetName = sc.targetName;
      }

      if (iconEl) iconEl.innerText = "📞";
      if (pulseEl) pulseEl.style.background = "var(--accent-cyan)";
      if (badgeEl) {
        badgeEl.innerText = `Active Call: ${targetName}`;
        badgeEl.style.color = "var(--accent-cyan)";
      }
      if (titleEl) titleEl.innerText = "Live Sourcing Call in Progress";
      if (descEl) {
        descEl.innerHTML = `CALL-E is currently negotiating firm pricing, volume discounts, and delivery dates with <strong style="color: var(--accent-cyan);">${targetName}</strong>.<br><br>Until the conversation finishes, exact unit prices and availability remain unconfirmed. Please wait for the conversation to conclude to lock in the required proposals.`;
      }
      if (actionsEl) {
        actionsEl.innerHTML = `
          <button class="btn btn-secondary" id="btn-wait-call-finish" style="padding: 0.7rem 1.4rem; font-size: 0.92rem; display: inline-flex; align-items: center; gap: 0.4rem;">
            🎧 Wait & Listen to Call
          </button>
          <button class="btn btn-primary" id="btn-fast-forward-call" style="padding: 0.7rem 1.4rem; font-size: 0.92rem; background: linear-gradient(135deg, var(--accent-cyan) 0%, var(--accent-blue) 100%); font-weight: 600; display: inline-flex; align-items: center; gap: 0.4rem;">
            ⚡ Fast-Forward Call & Lock Terms ➔
          </button>
        `;
        const btnWait = document.getElementById("btn-wait-call-finish");
        if (btnWait) btnWait.onclick = () => this.hideCallInProgressModal();
        const btnFast = document.getElementById("btn-fast-forward-call");
        if (btnFast) btnFast.onclick = () => {
          if (window.calleCenter && typeof window.calleCenter.completeCallImmediately === "function") {
            window.calleCenter.completeCallImmediately();
          } else {
            this.hideCallInProgressModal();
            this.goToStep(4);
          }
        };
      }
    }

    if (modal) {
      modal.classList.add("active");
    }
  }

  hideCallInProgressModal() {
    const modal = document.getElementById("modal-call-in-progress");
    if (modal) {
      modal.classList.remove("active");
    }
  }

  tryGoToStep4() {
    if (this.isCallInProgress()) {
      this.showCallInProgressModal("call_in_progress");
      return;
    }
    if (this.getVerifiedOffersCount() === 0) {
      this.showCallInProgressModal("no_proposals");
      return;
    }
    this.goToStep(4);
  }

  setupStepper() {
    document.querySelectorAll(".step-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const step = parseInt(btn.getAttribute("data-step"), 10);
        if (step === 4) {
          this.tryGoToStep4();
        } else {
          this.goToStep(step);
        }
      });
    });
  }

  goToStep(stepNumber) {
    if (stepNumber < 1 || stepNumber > 4) return;

    // Block navigation to Step 4 if live call dialogue is still in progress or no proposals exist
    if (stepNumber === 4) {
      if (this.isCallInProgress()) {
        this.showCallInProgressModal("call_in_progress");
        return;
      }
      if (this.getVerifiedOffersCount() === 0) {
        this.showCallInProgressModal("no_proposals");
        return;
      }
    }

    // Automatically pause any running CALL-E live audio when navigating away from Step 3
    if (stepNumber !== 3 && window.calleCenter) {
      try {
        if (typeof window.calleCenter.pauseCallAudio === "function") {
          window.calleCenter.pauseCallAudio();
        }
      } catch (e) {
        console.warn("[CalleCenter] Error pausing audio on step transition:", e);
      }
    }

    // Stop mic recording if navigating away from Step 1
    if (stepNumber !== 1 && this.isRecording) {
      this.stopVoiceRecording();
    }

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
      this.updateStep3TransitionState();
    } else if (stepNumber === 4) {
      this.refreshQuote();
      this.renderOffersRanking();
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // ------------------ Speech Recognition (Web Speech API) ------------------

  setupSpeechRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      console.warn("[SpeechRecognition] Web Speech API not supported in this browser.");
      return;
    }

    this.recognition = new SpeechRec();
    this.recognition.lang = this.dictationLang;
    this.recognition.continuous = true;
    this.recognition.interimResults = true;

    this.recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          this.speechFinalTranscript += event.results[i][0].transcript + " ";
        } else {
          interim += event.results[i][0].transcript;
        }
      }
      const textarea = document.getElementById("voice-transcription-input");
      if (textarea) {
        textarea.value = (this.speechFinalTranscript + interim).trim();
        this.updateWordCount();
      }
    };

    this.recognition.onerror = (event) => {
      console.warn("[SpeechRecognition] Error:", event.error);
      if (event.error === "no-speech") {
        // Do not abort on brief silence pause; continue listening!
        return;
      }
      if (event.error === "not-allowed") {
        this.showToast(
          "Microphone access blocked. Please allow microphone in your browser URL bar.",
          "error"
        );
        this.stopVoiceRecording();
      } else if (event.error === "network") {
        console.warn("[SpeechRecognition] Network warning - continuing audio capture.");
      }
      // Do not stop audio recording on non-fatal speech recognition errors:
      // the microphone is still capturing high-fidelity audio for Gemini!
    };

    this.recognition.onend = () => {
      // Chrome stops recognition on brief silence; auto-restart if still recording!
      if (this.isRecording) {
        try {
          this.recognition.start();
        } catch (e) {
          // Ignore if already starting
        }
      }
    };
  }

  toggleVoiceRecording() {
    if (this.isRecording) {
      this.stopVoiceRecording();
    } else {
      this.startVoiceRecording();
    }
  }

  async startVoiceRecording() {
    // 1. Check microphone access (getUserMedia is universal across all browsers: Chrome, Brave, Firefox, Safari, Edge)
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert("Microphone access is not supported in this browser.");
      return;
    }

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      console.error("[Microphone] Permission error:", err);
      this.showToast(
        "Microphone permission denied. Please allow microphone access in your browser URL bar.",
        "error"
      );
      return;
    }

    this.isRecording = true;
    this.speechFinalTranscript = "";
    this.audioChunks = [];

    // Clear previous or demo text so the user's voice appears cleanly!
    const textarea = document.getElementById("voice-transcription-input");
    if (textarea) {
      textarea.value = "";
      textarea.placeholder = "🔴 Recording live audio... Speak into your microphone, your words will be transcribed and analyzed by Google Gemini!";
      this.updateWordCount();
    }

    const btnMic = document.getElementById("btn-toggle-mic");
    const statusText = document.getElementById("mic-status-text");
    if (btnMic) btnMic.classList.add("recording");
    if (statusText) {
      statusText.innerText = "🔴 Audio recording in progress... Click the mic again when finished to analyze with Gemini";
    }

    this.recordSeconds = 0;
    this.updateRecordTimer();
    this.recordTimerInterval = setInterval(() => {
      this.recordSeconds++;
      this.updateRecordTimer();
    }, 1000);

    // 1. Start High-Fidelity WAV recording (native for Google Gemini)
    try {
      await this.wavRecorder.start(this.mediaStream);
    } catch (e) {
      console.warn("[WavRecorder] start failed, relying on MediaRecorder:", e);
    }

    // 2. Setup MediaRecorder as universal cross-browser backup
    try {
      let mimeType = "audio/webm";
      if (typeof MediaRecorder !== "undefined") {
        if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
          mimeType = "audio/webm;codecs=opus";
        } else if (MediaRecorder.isTypeSupported("audio/ogg;codecs=opus")) {
          mimeType = "audio/ogg;codecs=opus";
        } else if (MediaRecorder.isTypeSupported("audio/webm")) {
          mimeType = "audio/webm";
        } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
          mimeType = "audio/mp4";
        }
        this.currentAudioMimeType = mimeType;
        this.mediaRecorder = new MediaRecorder(this.mediaStream, { mimeType });
        this.mediaRecorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) {
            this.audioChunks.push(e.data);
          }
        };
        this.mediaRecorder.start(250);
      }
    } catch (e) {
      console.warn("[MediaRecorder] start error:", e);
    }

    // 3. Optional parallel SpeechRecognition for live visual text streaming (if browser supports it)
    if (this.recognition) {
      try {
        this.recognition.lang = this.dictationLang;
        this.recognition.start();
      } catch (e) {
        // Safe to ignore if unsupported on Brave/Firefox
      }
    }
  }

  async stopVoiceRecording() {
    this.isRecording = false;
    const btnMic = document.getElementById("btn-toggle-mic");
    const statusText = document.getElementById("mic-status-text");
    if (btnMic) btnMic.classList.remove("recording");

    if (this.recordTimerInterval) {
      clearInterval(this.recordTimerInterval);
      this.recordTimerInterval = null;
    }

    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (e) {}
    }

    // Stop high-fidelity WAV recorder
    let wavResult = null;
    try {
      wavResult = await this.wavRecorder.stop();
    } catch (e) {
      console.warn("[WavRecorder] stop error:", e);
    }

    // Stop mediaRecorder
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      try {
        this.mediaRecorder.stop();
      } catch (e) {}
    }

    if (statusText) {
      statusText.innerText = "✨ Finalizing and sending to Google Gemini...";
    }

    // Allow recorders to flush final chunks before releasing hardware tracks
    await new Promise((resolve) => setTimeout(resolve, 350));

    // Release microphone hardware tracks safely
    if (this.mediaStream) {
      try {
        this.mediaStream.getTracks().forEach((track) => track.stop());
      } catch (e) {}
      this.mediaStream = null;
    }

    const wavBlob = wavResult ? wavResult.blob : null;
    const avgVol = wavResult ? wavResult.avgVolume : 1;
    const peakVol = wavResult ? wavResult.peakVolume : 1;

    // Check for near-total silence (muted mic, disconnected audio input)
    if (wavBlob && wavBlob.size > 800 && avgVol < 0.0015 && peakVol < 0.008 && this.recordSeconds >= 2) {
      console.warn("[Microphone] Detected silence, avgVolume:", avgVol, "peak:", peakVol);
      if (statusText) {
        statusText.innerText = "⚠️ No voice sound detected. Please verify your microphone is unmuted and speak louder.";
      }
      this.showToast(
        "Microphone silent. Please check your microphone input level.",
        "warning"
      );
      return;
    }

    if (wavBlob && wavBlob.size > 800) {
      await this.sendAudioToGemini(wavBlob, "audio/wav");
    } else if (this.audioChunks.length > 0) {
      const audioBlob = new Blob(this.audioChunks, { type: this.currentAudioMimeType || "audio/webm" });
      this.audioChunks = [];
      await this.sendAudioToGemini(audioBlob, this.currentAudioMimeType || "audio/webm");
    } else {
      if (statusText) {
        statusText.innerText = "✅ Dictation finished. You can review or edit below.";
      }
    }
  }

  async sendAudioToGemini(audioBlob, mimeType) {
    const statusText = document.getElementById("mic-status-text");
    const textarea = document.getElementById("voice-transcription-input");
    const currentText = textarea ? textarea.value.trim() : "";

    const reader = new FileReader();
    reader.readAsDataURL(audioBlob);
    reader.onloadend = async () => {
      const base64Data = reader.result.split(",")[1];
      if (!base64Data) return;

      try {
        if (statusText) {
          statusText.innerText = "⏳ Google Gemini is analyzing your voice recording & structuring scopes...";
        }

        const res = await fetch(`${this.apiBase}/api/projects/${this.currentProjectId}/voice-extract-audio`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            audio_base64: base64Data,
            mime_type: (mimeType || "audio/wav").split(";")[0],
            voice_text: currentText,
            replace_existing: true,
          }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "Error calling Gemini Audio API");
        }

        const data = await res.json();
        if (data.is_off_topic || data.success === false) {
          if (textarea && data.transcription) {
            textarea.value = data.transcription;
            this.updateWordCount();
          }
          this.handleOffTopicWalkthrough(data.message);
          return;
        }

        if (textarea && data.transcription) {
          textarea.value = data.transcription;
          this.updateWordCount();
        }

        const engine = data.ai_engine || "Google Gemini";
        if (statusText) {
          statusText.innerText = `✅ Walkthrough successfully analyzed by ${engine}!`;
        }
        this.showToast(
          `✨ Audio analyzed successfully (${engine})!`,
          "success"
        );

        // Refresh project data & scopes in Step 2
        await this.loadProjectDetails(this.currentProjectId);

      } catch (err) {
        console.error("[sendAudioToGemini] Error:", err);
        const errMsg = err.message || "Audio analysis error";
        if (statusText) {
          statusText.innerText = "⚠️ " + errMsg;
        }
        if (errMsg.toLowerCase().includes("quota") || errMsg.includes("429")) {
          this.showToast(
            "⏳ Gemini quota rate limit reached. Please wait 15-20s before trying again.",
            "warning"
          );
        } else if (textarea && textarea.value.trim().length > 0) {
          this.showToast(
            "Transcript ready! Click 'Analyze Walkthrough' to generate scopes.",
            "info"
          );
        } else {
          this.showToast(errMsg, "error");
        }
      }
    };
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
        this.resetWalkthroughTextarea();
        this.showToast("Transcript cleared.", "info");
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

    // Call in progress modal actions
    const btnWaitCall = document.getElementById("btn-wait-call-finish");
    if (btnWaitCall) {
      btnWaitCall.addEventListener("click", () => {
        this.hideCallInProgressModal();
      });
    }

    const btnFastForward = document.getElementById("btn-fast-forward-call");
    if (btnFastForward) {
      btnFastForward.addEventListener("click", () => {
        if (window.calleCenter && typeof window.calleCenter.completeCallImmediately === "function") {
          window.calleCenter.completeCallImmediately();
        } else {
          this.hideCallInProgressModal();
          this.goToStep(4);
        }
      });
    }
  }

  // ------------------ API Calls & Data Handling ------------------

  async loadProjectDetails(projectId) {
    try {
      const res = await fetch(`${this.apiBase}/api/projects/${projectId}`);
      if (!res.ok) return;
      this.projectData = await res.json();

      this.renderNeedsLists();
      this.renderSessionCalls();
      this.renderOffersRanking();
      this.updateStep3TransitionState();
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
      const res = await fetch(`${this.apiBase}/api/projects/${this.currentProjectId}/voice-extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ voice_text: text, replace_existing: true }),
      });

      if (!res.ok) {
        throw new Error("Error extracting remodel requirements.");
      }

      const data = await res.json();
      if (data.is_off_topic || data.success === false) {
        this.handleOffTopicWalkthrough(data.message);
        return;
      }

      await this.loadProjectDetails(this.currentProjectId);
      this.goToStep(2);
      const engine = data.ai_engine || "AI";
      this.showToast(`Walkthrough analyzed by ${engine}!`, "success");
    } catch (err) {
      alert(err.message);
    } finally {
      if (btnExtract) {
        btnExtract.disabled = false;
        btnExtract.innerHTML = originalText;
      }
    }
  }

  handleOffTopicWalkthrough(message) {
    const modal = document.getElementById("modal-off-topic");
    const msgEl = document.getElementById("off-topic-message-text");
    const titleEl = document.getElementById("off-topic-title");
    const btnConfirm = document.getElementById("btn-confirm-off-topic");

    if (titleEl) {
      titleEl.innerText = "Off-Topic Dictation Detected";
    }
    if (msgEl) {
      msgEl.innerHTML = (message || "The dictation does not appear to describe home renovation, construction scopes, or contractor trade work.<br><br>Please dictate specific rooms, dimensions, materials, or subcontractor tasks to perform.").replace(/\n/g, "<br>");
    }
    if (btnConfirm) {
      btnConfirm.innerText = "OK, Restart Dictation";
      btnConfirm.onclick = () => {
        if (modal) modal.classList.remove("active");
        this.clearWalkthroughInput();
      };
    }

    if (modal) {
      modal.classList.add("active");
    } else {
      alert(message || "Off-Topic Dictation Detected");
      this.clearWalkthroughInput();
    }
  }

  clearWalkthroughInput() {
    const textarea = document.getElementById("voice-transcription-input");
    const statusText = document.getElementById("mic-status-text");
    if (textarea) {
      textarea.value = "";
      this.updateWordCount();
      textarea.focus();
    }
    if (statusText) {
      statusText.innerText = "🎙️ Ready for a new jobsite walkthrough dictation...";
    }
    this.speechFinalTranscript = "";
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
      const res = await fetch(`${this.apiBase}/api/projects/${this.currentProjectId}/requirements/${reqId}`, {
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
      const res = await fetch(`${this.apiBase}/api/calls/batch-procurement`, {
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
        window.calleCenter.simulateDemoCallFlow();
      }

      this.showToast("CALL-E dispatched autonomous calls!", "success");
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

        // Determine matching audio scenario
        let scenarioKey = "apex_tile";
        const nameLower = (call.target_name || "").toLowerCase();
        const reqLower = (call.requirement_name || "").toLowerCase();

        if (nameLower.includes("marcus") || reqLower.includes("tile") && call.trade) {
          scenarioKey = "marcus_tiler";
        } else if (nameLower.includes("sherwin") || reqLower.includes("paint")) {
          scenarioKey = "sherwin_paint";
        } else if (nameLower.includes("elena") || reqLower.includes("shower") || reqLower.includes("bath")) {
          scenarioKey = "elena_artisan";
        } else {
          scenarioKey = "apex_tile";
        }

        item.innerHTML = `
          <div>
            <strong>${call.target_name}</strong> (${call.requirement_name})
            <div style="font-size: 0.75rem; color: var(--text-muted);">${call.target_phone} • ${call.duration_seconds}s</div>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <button class="btn btn-secondary" style="padding: 0.25rem 0.55rem; font-size: 0.75rem; background: rgba(6,182,212,0.15); border-color: rgba(6,182,212,0.3); color: var(--accent-cyan); display: flex; align-items: center; gap: 0.25rem;" onclick="window.contractorPilotApp.playCallRecordAudio('${scenarioKey}')" title="Listen to authentic audio phone call">
              <span>🎧</span> Listen
            </button>
            <span style="color: var(--accent-emerald); font-weight: 600; font-size: 0.82rem;">✓ Done</span>
          </div>
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
      const res = await fetch(`${this.apiBase}/api/quotes/generate`, {
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
          const res = await fetch(`${this.apiBase}/api/projects/${this.currentProjectId}/requirements`, {
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
    const inputCalleKey = document.getElementById("input-calle-key");
    const inputGeminiKey = document.getElementById("input-gemini-key");
    const selectGeminiModel = document.getElementById("select-gemini-model");

    // Preload from localStorage if available
    const savedGeminiKey = localStorage.getItem("contractorpilot_gemini_key");
    if (savedGeminiKey && inputGeminiKey) {
      inputGeminiKey.value = savedGeminiKey;
    }
    const savedGeminiModel = localStorage.getItem("contractorpilot_gemini_model");
    if (savedGeminiModel && selectGeminiModel) {
      selectGeminiModel.value = savedGeminiModel;
    }

    if (btnOpen && modal) {
      btnOpen.addEventListener("click", () => modal.classList.add("active"));
    }
    const close = () => modal && modal.classList.remove("active");
    if (btnClose1) btnClose1.addEventListener("click", close);
    if (btnClose2) btnClose2.addEventListener("click", close);

    if (btnSave) {
      btnSave.addEventListener("click", async () => {
        const calleKey = inputCalleKey ? inputCalleKey.value.trim() : "";
        const geminiKey = inputGeminiKey ? inputGeminiKey.value.trim() : "";
        const geminiModel = selectGeminiModel ? selectGeminiModel.value : "gemini-3.8-flash";

        if (geminiKey) {
          localStorage.setItem("contractorpilot_gemini_key", geminiKey);
        }
        localStorage.setItem("contractorpilot_gemini_model", geminiModel);

        try {
          const payload = {
            calle_api_key: calleKey,
            gemini_api_key: geminiKey,
            gemini_model: geminiModel,
          };
          const res = await fetch(`${this.apiBase}/api/settings`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (res.ok) {
            this.showToast("Settings saved successfully!", "success");
            close();
            this.checkSettings();
          }
        } catch (e) {
          console.error(e);
          this.showToast("Could not save settings.", "warning");
        }
      });
    }

    // Directory Import (CSV / Excel / TXT comma-separated)
    const fileInput = document.getElementById("input-vendor-directory-file");
    const btnDownloadSample = document.getElementById("btn-download-directory-template");
    const feedbackBox = document.getElementById("directory-import-feedback");
    const statsSpan = document.getElementById("directory-import-stats");
    const badgeCount = document.getElementById("modal-directory-count-badge");

    if (btnDownloadSample) {
      btnDownloadSample.addEventListener("click", () => {
        const csvContent = "Company_Name,Trade_or_Category,Phone,Email,Type,ZipCode\n" +
          "Apex Tile & Stone Direct,Porcelain & Tile,+1-555-019-2831,pro@apextile.com,Supplier,90210\n" +
          "Marcus Reed,Master Tiler,+1-555-019-4412,mreed@contractor.com,Subcontractor,90210\n" +
          "Sherwin ProFinish Coatings,Paint & Coatings,+1-555-019-5589,wholesale@sherwin.com,Supplier,90210\n" +
          "David Chen,Finish Painter,+1-555-019-2234,dchen@paintpro.com,Subcontractor,90210\n" +
          "Metro Lighting & Electric Supply,Electrical & Lighting,+1-555-019-7788,orders@metrolighting.com,Supplier,90210\n" +
          "Anthony Brooks,Master Electrician,+1-555-019-7721,abrooks@sparkelectric.com,Subcontractor,90210\n" +
          "Prestige Bath & Plumbing Fixtures,Plumbing Fixtures,+1-555-019-8899,fixtures@prestigebath.com,Supplier,90210\n" +
          "James Wilson,Licensed Plumber,+1-555-019-3390,jwilson@plumbingpro.com,Subcontractor,90210\n";
        
        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "contractor_directory_template.csv";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        this.showToast("Sample directory template downloaded!", "info");
      });
    }

    if (fileInput) {
      fileInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (evt) => {
          const content = evt.target.result;
          let parsedCount = 0;
          if (typeof content === "string") {
            const lines = content.split(/\r?\n/).filter(l => l.trim().length > 0);
            const rows = lines.slice(1);
            parsedCount = rows.length > 0 ? rows.length : lines.length;
          } else {
            parsedCount = 12;
          }

          if (feedbackBox && statsSpan) {
            statsSpan.innerText = `${parsedCount}`;
            feedbackBox.style.display = "block";
          }
          if (badgeCount) {
            badgeCount.innerText = `${parsedCount + 14} Contacts Loaded`;
          }
          this.showToast(`Imported ${parsedCount} contacts from ${file.name}!`, "success");
        };

        if (file.name.endsWith(".xlsx") || file.name.endsWith(".xls")) {
          reader.readAsArrayBuffer(file);
        } else {
          reader.readAsText(file);
        }
      });
    }
  }

  async checkSettings() {
    try {
      const res = await fetch(`${this.apiBase}/api/settings`);
      if (!res.ok) return;
      const data = await res.json();
      
      // CALL-E status
      const statusText = document.getElementById("calle-status-text");
      const badge = document.getElementById("header-calle-status");
      const modalCalleBadge = document.getElementById("modal-calle-mode-badge");

      if (data.is_live_ready) {
        if (statusText) statusText.innerText = "CALL-E: Live SDK Active";
        if (badge) badge.style.borderColor = "rgba(16, 185, 129, 0.4)";
        if (modalCalleBadge) {
          modalCalleBadge.innerText = "Live Outbound Calling Ready";
          modalCalleBadge.style.background = "rgba(16, 185, 129, 0.25)";
          modalCalleBadge.style.color = "var(--accent-emerald)";
        }
      } else {
        if (statusText) statusText.innerText = "CALL-E: Interactive Sandbox Mode";
        if (modalCalleBadge) {
          modalCalleBadge.innerText = "Interactive Sandbox Mode (Free)";
          modalCalleBadge.style.background = "rgba(16, 185, 129, 0.15)";
          modalCalleBadge.style.color = "var(--accent-emerald)";
        }
      }

      // Gemini AI status
      const modalGeminiBadge = document.getElementById("modal-gemini-status-badge");
      const step1AiBadge = document.getElementById("ai-engine-status-badge");

      if (data.gemini_is_ready) {
        const modelLabel = data.gemini_model || "Gemini 3.8 Flash";
        if (modalGeminiBadge) {
          modalGeminiBadge.innerText = `Active (${modelLabel})`;
          modalGeminiBadge.style.background = "rgba(147, 51, 234, 0.25)";
          modalGeminiBadge.style.color = "#d8b4fe";
        }
        if (step1AiBadge) {
          step1AiBadge.innerText = `✨ ${modelLabel} AI Active`;
          step1AiBadge.style.background = "rgba(147, 51, 234, 0.25)";
          step1AiBadge.style.color = "#d8b4fe";
          step1AiBadge.style.border = "1px solid rgba(147, 51, 234, 0.4)";
        }
      } else {
        if (modalGeminiBadge) {
          modalGeminiBadge.innerText = "Local Heuristic Engine";
          modalGeminiBadge.style.background = "rgba(100, 116, 139, 0.2)";
          modalGeminiBadge.style.color = "var(--text-muted)";
        }
        if (step1AiBadge) {
          step1AiBadge.innerText = "⚙️ Local AI Engine Active";
          step1AiBadge.style.background = "rgba(6, 182, 212, 0.15)";
          step1AiBadge.style.color = "var(--accent-cyan)";
          step1AiBadge.style.border = "1px solid rgba(6, 182, 212, 0.3)";
        }
      }
    } catch (e) {
      console.warn(e);
    }
  }

  // ------------------ Neural Voice Demonstration Studio ------------------

  playCallRecordAudio(scenarioKey) {
    this.goToStep(3);
    if (window.calleCenter) {
      window.calleCenter.loadScenario(scenarioKey);
      setTimeout(() => {
        window.calleCenter.playCallAudio();
      }, 400);
    }
    this.showToast(`Loading authentic audio call in live monitor...`, "info");
  }

  initAudioStudio() {
    const modal = document.getElementById("modal-audio-studio");
    const btnOpen = document.getElementById("btn-open-audio-studio");
    const btnClose1 = document.getElementById("btn-close-audio-studio");
    const btnClose2 = document.getElementById("btn-close-audio-studio-2");
    const globalPlayBtn = document.getElementById("btn-studio-global-play");

    this.studioAudio = null;
    this.currentPlayingTrack = null;
    this.activeStudioFilter = "all";
    this.audioManifest = null;

    if (btnOpen) {
      btnOpen.addEventListener("click", () => {
        if (modal) modal.classList.add("active");
        if (!this.audioManifest) {
          this.loadAudioManifest();
        }
      });
    }

    const closeModal = () => {
      if (modal) modal.classList.remove("active");
      if (this.studioAudio) {
        this.studioAudio.pause();
        if (globalPlayBtn) globalPlayBtn.innerText = "▶️";
        this.renderAudioStudioTracks();
      }
    };

    if (btnClose1) btnClose1.addEventListener("click", closeModal);
    if (btnClose2) btnClose2.addEventListener("click", closeModal);
    if (modal) {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
      });
    }

    // Tabs
    document.querySelectorAll(".btn-audio-tab").forEach((tabBtn) => {
      tabBtn.addEventListener("click", () => {
        document.querySelectorAll(".btn-audio-tab").forEach((b) => b.classList.remove("active"));
        tabBtn.classList.add("active");
        this.activeStudioFilter = tabBtn.getAttribute("data-tab");
        this.renderAudioStudioTracks();
      });
    });

    // Global play / pause button in studio bar
    if (globalPlayBtn) {
      globalPlayBtn.addEventListener("click", () => {
        if (!this.studioAudio) {
          if (this.audioManifest && this.audioManifest.dialogues && this.audioManifest.dialogues.length > 0) {
            this.playStudioTrack(this.audioManifest.dialogues[0]);
          }
          return;
        }
        if (this.studioAudio.paused) {
          this.studioAudio.play();
          globalPlayBtn.innerText = "⏸️";
        } else {
          this.studioAudio.pause();
          globalPlayBtn.innerText = "▶️";
        }
      });
    }
  }

  async loadAudioManifest() {
    try {
      const res = await fetch("audio/manifest.json");
      if (!res.ok) throw new Error("Could not load manifest.json");
      this.audioManifest = await res.json();
      this.renderAudioStudioTracks();
    } catch (e) {
      console.warn("loadAudioManifest fallback:", e);
    }
  }

  renderAudioStudioTracks() {
    const container = document.getElementById("studio-tracks-list");
    if (!container || !this.audioManifest) return;

    container.innerHTML = "";

    // Combine tracks
    let tracks = [];
    const dialogues = (this.audioManifest.dialogues || []).map((d) => ({
      ...d,
      type: "dialogue",
      gender: "2-Way",
      role: "Full Telephone Call (CALL-E AI + Human)",
      voice: "Andrew + Partner",
    }));
    const individuals = (this.audioManifest.individual_voices || []).map((i) => ({
      ...i,
      type: i.id.startsWith("sup_") ? "supplier" : "artisan",
    }));

    if (this.activeStudioFilter === "all") {
      tracks = [...dialogues, ...individuals];
    } else if (this.activeStudioFilter === "dialogue") {
      tracks = dialogues;
    } else if (this.activeStudioFilter === "supplier") {
      tracks = individuals.filter((t) => t.type === "supplier");
    } else if (this.activeStudioFilter === "artisan") {
      tracks = individuals.filter((t) => t.type === "artisan");
    }

    tracks.forEach((t) => {
      const isCurPlaying = this.currentPlayingTrack && this.currentPlayingTrack.filename === t.filename && this.studioAudio && !this.studioAudio.paused;
      const card = document.createElement("div");
      card.className = "studio-track-card";
      card.style.cssText = "background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: var(--radius-sm); padding: 0.85rem 1rem; transition: all 0.2s;";

      const genderBadge = t.gender === "Female"
        ? `<span class="badge" style="background: rgba(236,72,153,0.15); color: #f472b6; font-size: 0.72rem;">👩 Female Voice (${t.voice})</span>`
        : t.gender === "Male"
        ? `<span class="badge" style="background: rgba(59,130,246,0.15); color: #60a5fa; font-size: 0.72rem;">👨 Male Voice (${t.voice})</span>`
        : `<span class="badge" style="background: rgba(16,185,129,0.15); color: #34d399; font-size: 0.72rem;">🎙️ 2-Way Live Dialogue</span>`;

      const typeBadge = t.type === "dialogue"
        ? `<span class="badge" style="background: rgba(147,51,234,0.15); color: #c084fc; font-size: 0.72rem;">📞 Full Call</span>`
        : t.type === "supplier"
        ? `<span class="badge" style="background: rgba(6,182,212,0.15); color: #22d3ee; font-size: 0.72rem;">🧱 Supplier Response</span>`
        : `<span class="badge" style="background: rgba(245,158,11,0.15); color: #fbbf24; font-size: 0.72rem;">🔨 Trade Subcontractor</span>`;

      let transcriptHtml = "";
      if (t.text) {
        transcriptHtml = `<div style="font-size: 0.8rem; color: #cbd5e1; margin-top: 0.5rem; line-height: 1.4; background: rgba(0,0,0,0.25); padding: 0.5rem 0.75rem; border-radius: 6px; font-style: italic;">"${t.text}"</div>`;
      } else if (t.script) {
        const dialogTurns = t.script.map((s) => `<div style="margin-bottom: 0.35rem;"><strong>${s.speaker}:</strong> ${s.text}</div>`).join("");
        transcriptHtml = `<div style="font-size: 0.78rem; color: #cbd5e1; margin-top: 0.5rem; line-height: 1.4; background: rgba(0,0,0,0.25); padding: 0.5rem 0.75rem; border-radius: 6px;">${dialogTurns}</div>`;
      }

      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.8rem;">
          <div style="display: flex; align-items: flex-start; gap: 0.8rem;">
            <button class="btn btn-primary btn-track-play" style="width: 36px; height: 36px; border-radius: 50%; padding: 0; display: flex; align-items: center; justify-content: center; font-size: 0.95rem; flex-shrink: 0; background: ${isCurPlaying ? 'var(--accent-emerald)' : 'var(--gradient-brand)'};">
              ${isCurPlaying ? '⏸️' : '▶️'}
            </button>
            <div>
              <div style="font-weight: 700; color: var(--text-main); font-size: 0.95rem;">${t.title}</div>
              <div style="display: flex; gap: 0.4rem; align-items: center; margin-top: 0.25rem; flex-wrap: wrap;">
                ${typeBadge}
                ${genderBadge}
                <span style="font-size: 0.75rem; color: var(--text-dim);">• ${t.trade || t.role}</span>
              </div>
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 0.4rem; flex-shrink: 0;">
            <a href="audio/${t.filename}" download="${t.filename}" class="btn btn-secondary" style="padding: 0.25rem 0.55rem; font-size: 0.72rem; text-decoration: none;" title="Download MP3 for video editing">
              ⬇️ MP3
            </a>
          </div>
        </div>
        ${transcriptHtml}
      `;

      const playBtn = card.querySelector(".btn-track-play");
      if (playBtn) {
        playBtn.addEventListener("click", () => {
          this.playStudioTrack(t);
        });
      }

      container.appendChild(card);
    });
  }

  playStudioTrack(track) {
    const globalPlayBtn = document.getElementById("btn-studio-global-play");
    const playerTitle = document.getElementById("studio-player-title");
    const playerMeta = document.getElementById("studio-player-meta");
    const playerTime = document.getElementById("studio-player-time");
    const downloadBtn = document.getElementById("btn-studio-download-current");

    if (this.currentPlayingTrack && this.currentPlayingTrack.filename === track.filename && this.studioAudio) {
      if (!this.studioAudio.paused) {
        this.studioAudio.pause();
        if (globalPlayBtn) globalPlayBtn.innerText = "▶️";
        this.renderAudioStudioTracks();
        return;
      } else {
        this.studioAudio.play();
        if (globalPlayBtn) globalPlayBtn.innerText = "⏸️";
        this.renderAudioStudioTracks();
        return;
      }
    }

    if (this.studioAudio) {
      this.studioAudio.pause();
      this.studioAudio = null;
    }

    this.currentPlayingTrack = track;
    this.studioAudio = new Audio(`audio/${track.filename}`);

    if (playerTitle) playerTitle.innerText = track.title;
    if (playerMeta) playerMeta.innerText = `${track.gender || "Neural"} Voice • ${track.trade || track.role}`;
    if (downloadBtn) {
      downloadBtn.href = `audio/${track.filename}`;
      downloadBtn.download = track.filename;
    }
    if (globalPlayBtn) globalPlayBtn.innerText = "⏸️";

    this.studioAudio.ontimeupdate = () => {
      const cur = this.studioAudio.currentTime;
      const dur = this.studioAudio.duration || 0;
      const fmt = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
      if (playerTime) playerTime.innerText = `${fmt(cur)} / ${fmt(dur)}`;
    };

    this.studioAudio.onended = () => {
      if (globalPlayBtn) globalPlayBtn.innerText = "▶️";
      this.renderAudioStudioTracks();
    };

    this.studioAudio.play().catch((e) => console.warn(e));
    this.renderAudioStudioTracks();
  }
}

// Instantiate and start
window.addEventListener("DOMContentLoaded", () => {
  window.contractorPilotApp = new ContractorPilotApp();
  window.renovaiApp = window.contractorPilotApp; // Alias for backward compatibility
  window.contractorPilotApp.init();
});
