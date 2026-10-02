(() => {
  'use strict';

  const screen = document.getElementById('screen');
  const assistBtn = document.getElementById('assistBtn');
  const homeBtn = document.getElementById('homeBtn');
  const timeoutModal = document.getElementById('timeoutModal');

  const IDLE_WARNING_MS = 65000;
  const IDLE_RESET_MS = 75000;
  const MAX_RECORDING_MS = 15000;

  let sessionId = null;
  let scenario = null;
  let assisted = false;
  let busy = false;
  let warningTimer = null;
  let resetTimer = null;
  let transcript = [];

  let sttInfo = {
    available: false,
    provider: 'whisper_cpp',
    language: 'el',
    model: null,
    detail: 'Local voice recognition is not configured.',
    max_recording_ms: MAX_RECORDING_MS,
  };

  let mediaRecorder = null;
  let mediaStream = null;
  let audioChunks = [];
  let recordingStartedAt = 0;
  let recordingTimer = null;
  let discardRecording = false;
  let voiceBusy = false;

  let ttsInfo = { available: false, provider: 'mac_say', voice: null, detail: 'Local Greek TTS unavailable.', media_type: 'audio/wav', max_chars: 600 };
  let currentSpeech = null;
  let currentSpeechUrl = null;
  let speechMuted = false;
  let speechBusy = false;
  let lastAssistantText = '';


  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  async function api(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
  }

  function setMode(mode) {
    screen.dataset.aiMode = mode;
  }

  function clearIdleTimers() {
    clearTimeout(warningTimer);
    clearTimeout(resetTimer);
  }

  function armIdleTimers() {
    clearIdleTimers();
    timeoutModal.hidden = true;
    warningTimer = setTimeout(() => {
      timeoutModal.hidden = false;
    }, IDLE_WARNING_MS);
    resetTimer = setTimeout(() => {
      void resetExperience();
    }, IDLE_RESET_MS);
  }

  async function loadTtsStatus() {
    try {
      ttsInfo = await api('/api/ai/tts/status');
    } catch (_) {
      ttsInfo = { available: false, provider: 'mac_say', voice: null, detail: 'Η τοπική σύνθεση φωνής δεν είναι διαθέσιμη.', media_type: 'audio/wav', max_chars: 600 };
    }
  }

  function releaseSpeechUrl() {
    if (currentSpeechUrl) {
      URL.revokeObjectURL(currentSpeechUrl);
      currentSpeechUrl = null;
    }
  }

  function cancelSpeech() {
    if (currentSpeech) {
      try { currentSpeech.pause(); currentSpeech.currentTime = 0; } catch (_) {}
      currentSpeech = null;
    }
    releaseSpeechUrl();
    speechBusy = false;
  }

  function updateSpeechControls() {
    const replay = document.getElementById('replayAiBtn');
    const mute = document.getElementById('muteAiBtn');
    if (replay) {
      replay.disabled = !ttsInfo.available || speechBusy || !lastAssistantText;
      replay.textContent = speechBusy ? 'ΦΟΡΤΩΣΗ ΦΩΝΗΣ…' : 'ΕΠΑΝΑΛΗΨΗ ΦΩΝΗΣ';
    }
    if (mute) {
      mute.disabled = !ttsInfo.available;
      mute.setAttribute('aria-pressed', String(speechMuted));
      mute.textContent = speechMuted ? 'ΗΧΟΣ' : 'ΣΙΓΑΣΗ';
    }
  }

  async function speakAssistant(text, { force = false } = {}) {
    const clean = String(text || '').trim();
    lastAssistantText = clean;
    updateSpeechControls();
    if (!clean || !ttsInfo.available || (speechMuted && !force)) return;

    cancelSpeech();
    speechBusy = true;
    updateSpeechControls();

    try {
      const response = await fetch('/api/ai/tts/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: clean }),
        cache: 'no-store',
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const blob = await response.blob();
      if (!blob.size) throw new Error('Empty TTS audio');
      currentSpeechUrl = URL.createObjectURL(blob);
      currentSpeech = new Audio(currentSpeechUrl);

      currentSpeech.addEventListener('ended', () => {
        currentSpeech = null;
        releaseSpeechUrl();
        speechBusy = false;
        updateSpeechControls();
      }, { once: true });

      currentSpeech.addEventListener('error', () => {
        cancelSpeech();
        updateSpeechControls();
      }, { once: true });

      await currentSpeech.play();
    } catch (_) {
      cancelSpeech();
      updateSpeechControls();
    }
  }

  function toggleSpeechMute() {
    speechMuted = !speechMuted;
    if (speechMuted) cancelSpeech();
    updateSpeechControls();
    armIdleTimers();
  }

  async function loadSttStatus() {
    try {
      sttInfo = await api('/api/ai/stt/status');
    } catch (_) {
      sttInfo = {
        available: false,
        provider: 'whisper_cpp',
        language: 'el',
        model: null,
        detail: 'Η τοπική αναγνώριση φωνής δεν είναι διαθέσιμη.',
        max_recording_ms: MAX_RECORDING_MS,
      };
    }
  }

  function stopMediaTracks() {
    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop());
      mediaStream = null;
    }
  }

  function cancelVoiceCapture() {
    clearTimeout(recordingTimer);
    recordingTimer = null;
    discardRecording = true;
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      try {
        mediaRecorder.stop();
      } catch (_) {
        // Best-effort shutdown.
      }
    }
    mediaRecorder = null;
    audioChunks = [];
    voiceBusy = false;
    stopMediaTracks();
  }

  async function endBackendSession() {
    if (!sessionId) return;
    const old = sessionId;
    sessionId = null;
    try {
      await fetch(`/api/ai/session/${encodeURIComponent(old)}`, { method: 'DELETE' });
    } catch (_) {
      // Best-effort cleanup only; server sessions also expire automatically.
    }
  }

  async function resetExperience() {
    clearIdleTimers();
    timeoutModal.hidden = true;
    cancelVoiceCapture();
    cancelSpeech();
    lastAssistantText = '';
    await endBackendSession();
    transcript = [];
    scenario = null;
    busy = false;
    await showIntro();
    armIdleTimers();
  }

  async function showIntro() {
    setMode('intro');
    try {
      const info = await api('/api/ai/scenario');
      scenario = info;
      screen.innerHTML = `
        <article class="ai-card ai-intro">
          <div class="ai-eyebrow">${escapeHtml(info.station_label)}</div>
          <h1>${escapeHtml(info.intro_title)}</h1>
          <p>${escapeHtml(info.intro_body)}</p>
          <p class="ai-privacy">${escapeHtml(info.privacy_note)}</p>
          <button id="startAiBtn" class="primary-button ai-start" type="button">ΕΝΑΡΞΗ ΣΥΝΟΜΙΛΙΑΣ</button>
        </article>
      `;
      document.getElementById('startAiBtn').addEventListener('click', startSession);
    } catch (error) {
      renderError('Δεν ήταν δυνατή η φόρτωση του Station 4.');
    }
  }

  async function startSession() {
    if (busy) return;
    busy = true;
    try {
      const [payload] = await Promise.all([
        api('/api/ai/session/start', {
          method: 'POST',
          body: JSON.stringify({}),
        }),
        loadSttStatus(),
        loadTtsStatus(),
      ]);
      sessionId = payload.session_id;
      scenario = payload.scenario;
      transcript = [{ role: 'caller', text: payload.assistant_text }];
      lastAssistantText = payload.assistant_text;
      renderConversation();
      armIdleTimers();
      void speakAssistant(payload.assistant_text);
    } catch (error) {
      renderError('Δεν ήταν δυνατή η έναρξη της συνομιλίας.');
    } finally {
      busy = false;
    }
  }

  function transcriptHtml() {
    return transcript.map(item => `
      <div class="ai-bubble ${item.role === 'visitor' ? 'visitor' : 'caller'}">
        <small>${item.role === 'visitor' ? 'ΕΣΥ' : escapeHtml(scenario.speaker_label)}</small>
        ${escapeHtml(item.text)}
      </div>
    `).join('');
  }

  function voiceBadgeText() {
    if (sttInfo.available && ttsInfo.available) return 'LOCAL VOICE · STT + TTS';
    if (sttInfo.available) return 'LOCAL VOICE · STT';
    if (ttsInfo.available) return 'LOCAL VOICE · TTS';
    return 'TEXT · VOICE OPTIONAL';
  }

  function voiceHelperText() {
    if (sttInfo.available) {
      return 'Μίλησε ή γράψε την απάντησή σου. Έλεγξε το κείμενο πριν το στείλεις.';
    }
    return 'Γράψε την απάντησή σου. Η τοπική αναγνώριση φωνής δεν είναι ακόμη ενεργή.';
  }

  function renderConversation() {
    setMode('conversation');
    const micDisabled = sttInfo.available ? '' : 'disabled';
    const micTitle = sttInfo.available
      ? 'Πάτησε για να μιλήσεις'
      : escapeHtml(sttInfo.detail || 'Η τοπική αναγνώριση φωνής δεν είναι διαθέσιμη.');

    screen.innerHTML = `
      <article class="ai-card ai-conversation">
        <aside class="ai-context">
          <div class="ai-context-label">ΣΥΝΟΜΙΛΙΑ</div>
          <div class="ai-caller">${escapeHtml(scenario.speaker_label)}</div>
          <div class="ai-live-badge">${voiceBadgeText()}</div>
          <div class="ai-audio-controls" aria-label="Έλεγχος συνθετικής φωνής">
            <button id="replayAiBtn" class="ai-audio-button" type="button">ΕΠΑΝΑΛΗΨΗ ΦΩΝΗΣ</button>
            <button id="muteAiBtn" class="ai-audio-button" type="button" aria-pressed="${String(speechMuted)}">${speechMuted ? 'ΗΧΟΣ' : 'ΣΙΓΑΣΗ'}</button>
          </div>
          <p>${escapeHtml(scenario.privacy_note)}</p>
        </aside>

        <section class="ai-dialogue">
          <div id="aiTranscript" class="ai-transcript" aria-label="Ιστορικό συνομιλίας">
            ${transcriptHtml()}
          </div>

          <form id="aiCompose" class="ai-compose">
            <label for="visitorText">Τι θα έλεγες τώρα;</label>
            <div class="ai-compose-row">
              <textarea id="visitorText" maxlength="280" required autocomplete="off" placeholder="Μίλησε ή γράψε όπως θα απαντούσες στην πραγματικότητα..."></textarea>
              <div class="ai-compose-actions">
                <button
                  id="micAiBtn"
                  class="ai-mic-button"
                  type="button"
                  aria-pressed="false"
                  title="${micTitle}"
                  ${micDisabled}
                >
                  <span class="ai-mic-indicator" aria-hidden="true"></span>
                  <span id="micAiLabel">ΜΙΛΗΣΕ</span>
                </button>
                <button id="sendAiBtn" class="primary-button ai-send" type="submit">ΑΠΟΣΤΟΛΗ</button>
              </div>
            </div>
            <p class="ai-helper">${escapeHtml(voiceHelperText())}</p>
            <div id="aiStatus" class="ai-status" aria-live="polite"></div>
          </form>
        </section>
      </article>
    `;

    document.getElementById('aiCompose').addEventListener('submit', submitTurn);
    const micButton = document.getElementById('micAiBtn');
    if (micButton && sttInfo.available) {
      micButton.addEventListener('click', toggleRecording);
    }

    const replayButton = document.getElementById('replayAiBtn');
    if (replayButton) {
      replayButton.addEventListener('click', () => {
        void speakAssistant(lastAssistantText, { force: true });
        armIdleTimers();
      });
    }
    const muteButton = document.getElementById('muteAiBtn');
    if (muteButton) muteButton.addEventListener('click', toggleSpeechMute);

    updateSpeechControls();
    document.getElementById('visitorText').focus();
    scrollTranscript();
  }

  function scrollTranscript() {
    const box = document.getElementById('aiTranscript');
    if (box) box.scrollTop = box.scrollHeight;
  }

  function setVoiceUi(state, message = '') {
    const mic = document.getElementById('micAiBtn');
    const label = document.getElementById('micAiLabel');
    const send = document.getElementById('sendAiBtn');
    const status = document.getElementById('aiStatus');
    if (!mic || !label || !send || !status) return;

    mic.classList.toggle('is-recording', state === 'recording');
    mic.classList.toggle('is-processing', state === 'processing');
    mic.setAttribute('aria-pressed', String(state === 'recording'));
    mic.disabled = state === 'processing' || !sttInfo.available;
    send.disabled = state === 'recording' || state === 'processing' || busy;

    if (state === 'recording') label.textContent = 'ΣΤΑΜΑΤΑ';
    else if (state === 'processing') label.textContent = 'ΑΝΑΓΝΩΡΙΣΗ…';
    else label.textContent = 'ΜΙΛΗΣΕ';

    status.textContent = message;
  }

  function selectRecordingMimeType() {
    if (!window.MediaRecorder || typeof MediaRecorder.isTypeSupported !== 'function') return '';
    const candidates = [
      'audio/webm;codecs=opus',
      'audio/mp4',
      'audio/webm',
      'audio/ogg;codecs=opus',
    ];
    return candidates.find(type => MediaRecorder.isTypeSupported(type)) || '';
  }

  async function toggleRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.stop();
      return;
    }
    if (voiceBusy || busy || !sttInfo.available) return;
    await startRecording();
  }

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setVoiceUi('idle', 'Το πρόγραμμα περιήγησης δεν υποστηρίζει εγγραφή μικροφώνου.');
      return;
    }

    try {
      discardRecording = false;
      audioChunks = [];
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });

      const mimeType = selectRecordingMimeType();
      mediaRecorder = mimeType
        ? new MediaRecorder(mediaStream, { mimeType })
        : new MediaRecorder(mediaStream);

      mediaRecorder.addEventListener('dataavailable', event => {
        if (event.data && event.data.size > 0) audioChunks.push(event.data);
      });

      mediaRecorder.addEventListener('stop', handleRecordingStopped, { once: true });
      mediaRecorder.start();
      recordingStartedAt = performance.now();
      voiceBusy = true;
      setVoiceUi('recording', 'Ακούω… πάτησε ξανά όταν τελειώσεις.');
      armIdleTimers();

      const limit = Math.min(
        Number(sttInfo.max_recording_ms) || MAX_RECORDING_MS,
        MAX_RECORDING_MS,
      );
      recordingTimer = setTimeout(() => {
        if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();
      }, limit);
    } catch (error) {
      voiceBusy = false;
      stopMediaTracks();
      const denied = error?.name === 'NotAllowedError' || error?.name === 'SecurityError';
      setVoiceUi(
        'idle',
        denied
          ? 'Δεν δόθηκε άδεια μικροφώνου. Μπορείς να συνεχίσεις γράφοντας.'
          : 'Δεν ήταν δυνατή η πρόσβαση στο μικρόφωνο.',
      );
    }
  }

  async function handleRecordingStopped() {
    clearTimeout(recordingTimer);
    recordingTimer = null;
    const durationMs = Math.max(0, Math.round(performance.now() - recordingStartedAt));
    const mimeType = mediaRecorder?.mimeType || audioChunks[0]?.type || 'application/octet-stream';
    const chunks = audioChunks.slice();
    mediaRecorder = null;
    audioChunks = [];
    stopMediaTracks();

    if (discardRecording) {
      discardRecording = false;
      voiceBusy = false;
      return;
    }

    if (!chunks.length) {
      voiceBusy = false;
      setVoiceUi('idle', 'Δεν καταγράφηκε ήχος. Δοκίμασε ξανά.');
      return;
    }

    const blob = new Blob(chunks, { type: mimeType });
    await transcribeRecording(blob, durationMs);
  }

  async function transcribeRecording(blob, durationMs) {
    setVoiceUi('processing', 'Μετατροπή φωνής σε κείμενο…');
    try {
      const response = await fetch('/api/ai/stt/transcribe', {
        method: 'POST',
        headers: {
          'Content-Type': blob.type || 'application/octet-stream',
          'X-Audio-Duration-Ms': String(durationMs),
        },
        body: blob,
      });

      let payload = null;
      try {
        payload = await response.json();
      } catch (_) {
        payload = null;
      }

      if (!response.ok) {
        const detail = payload?.detail || `HTTP ${response.status}`;
        throw new Error(detail);
      }

      const input = document.getElementById('visitorText');
      if (!input) return;
      input.value = String(payload.text || '').slice(0, 280);
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
      setVoiceUi('idle', 'Η φωνή μετατράπηκε σε κείμενο. Έλεγξέ το και πάτησε ΑΠΟΣΤΟΛΗ.');
      armIdleTimers();
    } catch (error) {
      setVoiceUi('idle', `Η αναγνώριση φωνής απέτυχε. ${error?.message || ''}`.trim());
    } finally {
      voiceBusy = false;
    }
  }

  async function submitTurn(event) {
    event.preventDefault();
    if (busy || voiceBusy || !sessionId) return;

    const input = document.getElementById('visitorText');
    const text = input.value.trim();
    if (!text) return;

    busy = true;
    input.disabled = true;
    const send = document.getElementById('sendAiBtn');
    if (send) send.disabled = true;
    transcript.push({ role: 'visitor', text });
    renderConversation();

    try {
      const payload = await api(`/api/ai/session/${encodeURIComponent(sessionId)}/turn`, {
        method: 'POST',
        body: JSON.stringify({ text }),
      });

      transcript.push({ role: 'caller', text: payload.assistant_text });
      lastAssistantText = payload.assistant_text;
      if (payload.terminal) {
        sessionId = null;
        renderResult(payload);
        void speakAssistant(payload.assistant_text);
      } else {
        renderConversation();
        void speakAssistant(payload.assistant_text);
      }
      armIdleTimers();
    } catch (error) {
      renderError('Η συνομιλία διακόπηκε. Ξεκίνα ξανά την εμπειρία.');
    } finally {
      busy = false;
    }
  }

  function renderResult(payload) {
    cancelVoiceCapture();
    setMode('result');
    const outcome = payload.outcome;
    screen.innerHTML = `
      <article class="ai-card ai-result">
        <div class="ai-eyebrow">ΑΝΑΛΥΣΗ ΣΥΝΟΜΙΛΙΑΣ</div>
        <h1>${escapeHtml(outcome.title)}</h1>
        <div class="ai-result-grid">
          <section class="ai-score">
            <div>ΑΠΟΤΕΛΕΣΜΑ</div>
            <strong>${escapeHtml(payload.score)}/100</strong>
            <p>Η βαθμολογία αφορά μόνο αυτή την προσομοίωση.</p>
          </section>
          <section class="ai-feedback">
            <h2>Τι συνέβη</h2>
            <p>${escapeHtml(outcome.summary)}</p>
            <h2>Σημάδια πίεσης</h2>
            <ul>${outcome.red_flags.map(flag => `<li>${escapeHtml(flag)}</li>`).join('')}</ul>
            <p class="ai-takeaway"><strong>ΣΤΑΜΑΤΑ → ΕΛΕΓΞΕ → ΕΠΙΒΕΒΑΙΩΣΕ</strong><br>${escapeHtml(outcome.takeaway)}</p>
          </section>
        </div>
        <div class="ai-result-actions">
          <button id="againBtn" class="primary-button" type="button">ΔΟΚΙΜΑΣΕ ΞΑΝΑ</button>
          <button id="resultHomeBtn" class="ghost-button" type="button">ΑΡΧΙΚΗ</button>
        </div>
      </article>
    `;
    document.getElementById('againBtn').addEventListener('click', resetExperience);
    document.getElementById('resultHomeBtn').addEventListener('click', () => { window.location.href = '/'; });
  }

  function renderError(message) {
    cancelVoiceCapture();
    cancelSpeech();
    setMode('error');
    screen.innerHTML = `
      <section class="ai-error">
        <h1>Station 4</h1>
        <p>${escapeHtml(message)}</p>
        <button id="retryBtn" class="primary-button" type="button">ΕΠΑΝΑΛΗΨΗ</button>
      </section>
    `;
    document.getElementById('retryBtn').addEventListener('click', resetExperience);
  }

  assistBtn.addEventListener('click', () => {
    assisted = !assisted;
    document.body.classList.toggle('assisted', assisted);
    assistBtn.setAttribute('aria-pressed', String(assisted));
    armIdleTimers();
  });

  homeBtn.addEventListener('click', async () => {
    cancelVoiceCapture();
    cancelSpeech();
    await endBackendSession();
    window.location.href = '/';
  });

  ['pointerdown', 'keydown', 'touchstart'].forEach(eventName => {
    document.addEventListener(eventName, armIdleTimers, { passive: true });
  });

  window.addEventListener('pagehide', () => {
    cancelVoiceCapture();
    cancelSpeech();
    if (sessionId) {
      fetch(`/api/ai/session/${encodeURIComponent(sessionId)}`, {
        method: 'DELETE',
        keepalive: true,
      }).catch(() => {});
    }
  });

  void showIntro();
  armIdleTimers();
})();
