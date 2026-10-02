(() => {
  'use strict';

  let SCENARIO_ID = 'call_account_security_001';
  let scenarioList = [];
  const INITIAL_SCORE = 50;
  const IDLE_WARNING_MS = 65000;
  const IDLE_RESET_MS = 75000;

  const screen = document.getElementById('screen');
  const audioPlayer = document.getElementById('audioPlayer');

  let ambientPlayer = new Audio();
  ambientPlayer.loop = true;
  ambientPlayer.volume = 0.30;

  let callAudioManifest = null;
  let currentAmbientScene = null;

  async function loadCallAmbientManifest() {
    try {
      const response = await fetch("/api/call-audio-manifest", {cache:"no-store"});
      if (response.ok) {
        callAudioManifest = await response.json();
      }
    } catch(error) {
      console.warn("Ambient manifest unavailable", error);
    }
  }

  let callAnswered = false;

function playAmbientForNode(nodeId) {
    if (!callAnswered) {
        // ambient continues during call
        return;
    }
    if (!callAudioManifest) return;

    const scenarioAudio = callAudioManifest[SCENARIO_ID];
    if (!scenarioAudio) return;

    const scene =
      scenarioAudio.nodes[nodeId] ||
      scenarioAudio.default_scene;

    if (scene === currentAmbientScene) return;

    const sceneData = scenarioAudio.scenes[scene];
    if (!sceneData) return;

    currentAmbientScene = scene;
    ambientPlayer.src = sceneData.audio;
    ambientPlayer.play().catch(()=>{});
  }


  /* FRAUD_LAB_RING_START */

  const fraudLabRing = new Audio(
    '/static/audio/ui/incoming_call.mp3'
  );

  fraudLabRing.preload = 'auto';
  fraudLabRing.loop = true;
  fraudLabRing.volume = 1.0;

  let fraudLabRingTimeout = null;


  function fraudLabStopRing() {

    if (fraudLabRingTimeout) {
      window.clearTimeout(
        fraudLabRingTimeout
      );

      fraudLabRingTimeout = null;
    }

    try {
      fraudLabRing.pause();
      fraudLabRing.currentTime = 0;
    } catch (error) {
      console.warn(
        'Ring stop error:',
        error
      );
    }
  }


  function fraudLabStartRing() {

    fraudLabStopRing();

    try {

      fraudLabRing.currentTime = 0;

      const playback =
        fraudLabRing.play();

      if (
        playback &&
        typeof playback.catch === 'function'
      ) {

        playback.catch(error => {
          console.warn(
            'Ring playback blocked:',
            error
          );
        });

      }

      // Safety timeout:
      // never allow unattended ringing forever.
      fraudLabRingTimeout =
        window.setTimeout(
          fraudLabStopRing,
          30000
        );

    } catch (error) {

      console.warn(
        'Ring playback error:',
        error
      );

    }
  }

  /* FRAUD_LAB_RING_END */

  const homeBtn = document.getElementById('homeBtn');
  const assistBtn = document.getElementById('assistBtn');
  const timeoutModal = document.getElementById('timeoutModal');
  const continueBtn = document.getElementById('continueBtn');

  let scenario = null;
  let currentNodeId = null;
  let score = INITIAL_SCORE;
  let assisted = false;
  let policeVerifyAttempts = 0;
  let threatStarted = false;
  let threatVerifyAttempts = 0;
  let accidentVictim = false;
  let warningTimer = null;
  let resetTimer = null;

  const clampScore = (value) => Math.max(0, Math.min(100, value));

  function setCallMode(mode) {
    screen.dataset.callMode = mode;
  }

  function stopAudio() {
    audioPlayer.pause();
    audioPlayer.removeAttribute('src');
    audioPlayer.load();
  }

  function stopAllCallAudio() {
    try {
      ambientPlayer.pause();
      ambientPlayer.currentTime = 0;
    } catch(error) {}

    audioPlayer.pause();
    audioPlayer.removeAttribute('src');
    audioPlayer.load();
  }

  function clearSession() {
    sessionStorage.removeItem('fraudlab_call_state');
  }

  function saveSession() {
    sessionStorage.setItem('fraudlab_call_state', JSON.stringify({ currentNodeId, score, assisted, policeVerifyAttempts, threatStarted, threatVerifyAttempts, accidentVictim }));
  }


  function reactionStatus(node, value, victim, dangerStarted) {
    if (node?.id?.includes('unsafe_final')) {
      return '🔴 ΚΙΝΔΥΝΟΣ';
    }

    if (node?.id?.includes('safe_final')) {
      return '🟢 ΑΣΦΑΛΗΣ';
    }

    if (victim) {
      return '🔴 ΚΙΝΔΥΝΟΣ';
    }

    if (dangerStarted || value < 40) {
      return '🟡 ΠΡΟΣΟΧΗ';
    }

    return '🟢 ΑΣΦΑΛΗΣ';
  }


  function resetIdleTimers() {
    clearTimeout(warningTimer);
    clearTimeout(resetTimer);
    timeoutModal.hidden = true;

    warningTimer = window.setTimeout(() => {
      timeoutModal.hidden = false;
      continueBtn.focus();
    }, IDLE_WARNING_MS);

    resetTimer = window.setTimeout(() => {
      restartExperience();
    }, IDLE_RESET_MS);
  }

  function registerActivity() {
    resetIdleTimers();
  }

  function scoreLabel(value) {
    if (value >= 90) return 'Ισχυρή Αντίσταση στην Απάτη';
    if (value >= 70) return 'Καλή Αντίδραση — Μερικά σημεία χρειάζονται προσοχή';
    if (value >= 50) return 'Ορισμένες τεχνικές πίεσης σε επηρέασαν';
    return 'Δες ποια σημεία χρησιμοποίησε ο απατεώνας για να σε πιέσει';
  }

  function resultLabel(node, value) {
    if (node.id === "accident_unsafe_final") {
      return "ΔΥΣΤΥΧΩΣ ΠΙΘΑΝΟΝ ΕΠΕΣΕΣ ΘΥΜΑ ΑΠΑΤΗΣ";
    }
    if (node.id === "accident_safe_final") {
      return "ΜΠΡΑΒΟ! ΑΝΑΓΝΩΡΙΣΕΣ ΤΗΝ ΑΠΑΤΗ";
    }
    return scoreLabel(value);
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function showAttract() {
    setCallMode('intro');
    stopAudio();
    clearSession();
    currentNodeId = null;
    score = INITIAL_SCORE;
    screen.innerHTML = `
      <article class="experience-card">
        <div class="hero-panel">
          <div class="eyebrow">STATION 1 · ΤΗΛΕΦΩΝΙΚΗ ΚΛΗΣΗ</div>
          <h1>Μια απρόσμενη κλήση</h1>
          <p>Μια σύντομη τηλεφωνική προσομοίωση. Δεν ζητάμε ούτε αποθηκεύουμε πραγματικά προσωπικά ή οικονομικά στοιχεία.</p>
          <label for="scenarioSelect">Επιλογή Σεναρίου:</label>
          <div class="scenario-select-wrapper">
            <select id="scenarioSelect"></select>
          </div>
          <div><button id="startBtn" class="primary-button" type="button">ΕΝΑΡΞΗ ΠΡΟΣΟΜΟΙΩΣΗΣ</button></div>
        </div>
      </article>`;
    const selector = document.getElementById('scenarioSelect');

    if (selector && scenarioList.length) {
      selector.innerHTML = scenarioList.map(item =>
        `<option value="${item.scenario_id}">${item.title}</option>`
      ).join('');

      selector.value = SCENARIO_ID;

      selector.addEventListener('change', async () => {
        SCENARIO_ID = selector.value;

        const response = await fetch(`/api/scenarios/${SCENARIO_ID}`, { cache: 'no-store' });
        scenario = await response.json();

        currentNodeId = null;
        score = INITIAL_SCORE;
      });
    }

    document.getElementById('startBtn').addEventListener('click', () => {
      policeVerifyAttempts = 0;
      currentNodeId = scenario.start_node;
      saveSession();
      renderCurrentNode();
    });
    resetIdleTimers();
  }

  function playNodeAudio(node) {
    if (!node.audio) return;
    stopAudio();
    audioPlayer.src = node.audio;
    audioPlayer.play()
      .then(() => console.log("NODE AUDIO PLAY OK", node.audio))
      .catch((err) => console.error("NODE AUDIO PLAY ERROR", node.audio, err));
  }

  function renderCurrentNode() {
    const node = scenario.nodes[currentNodeId];
    playAmbientForNode(currentNodeId);

    if (currentNodeId === "escalation_threat") {
      threatStarted = true;
      threatVerifyAttempts = 0;
    }
    if (!node) {
      renderFatal('Το σενάριο δεν μπορεί να συνεχίσει. Χρησιμοποιήστε ΑΡΧΙΚΗ για άμεση επανεκκίνηση.');
      return;
    }

    if (node.terminal) {
      renderResult(node);
      return;
    }

    setCallMode('decision');
    const isIncoming = node.kind === 'incoming_call';

    if (isIncoming) {
      callAnswered = false;
      stopAllCallAudio();
      fraudLabStartRing();
    }

    const choices = node.choices.map((choice, index) => `
      <button class="choice-button" type="button" data-choice-index="${index}">
        ${escapeHtml(choice.label)}
      </button>`).join('');

    screen.innerHTML = `
      <article class="experience-card">
        <div class="phone-stage">
          <section class="phone-shell" aria-label="Προσομοίωση τηλεφώνου">
            <div class="phone-top">
              <div class="call-label">${isIncoming ? 'ΕΙΣΕΡΧΟΜΕΝΗ ΚΛΗΣΗ' : 'ΚΛΗΣΗ ΣΕ ΕΞΕΛΙΞΗ'}</div>
              <div class="caller-name">${node.display_name || "ΤΜΗΜΑ ΑΣΦΑΛΕΙΑΣ ΚΑΡΤΩΝ"}</div>
              <div class="caller-number">${isIncoming ? 'Εισερχόμενη κλήση' : 'Κλήση σε εξέλιξη'}</div>
              <div class="call-indicator ${isIncoming ? 'ringing' : ''}" aria-hidden="true">☎</div>
            </div>
            <div class="phone-footnote">ΠΡΟΣΟΜΟΙΩΣΗ ΚΛΗΣΗΣ</div>
          </section>

          <section class="dialogue-panel">
            <div class="step-kicker">${isIncoming ? 'Τι κάνεις;' : 'Ο καλών λέει:'}</div>
            <div class="dialogue-text">${escapeHtml(node.text)}</div>
            ${node.audio ? `
              <div class="audio-row">
                <button class="audio-button" id="replayAudio" type="button">🔊 ΑΚΟΥΣΕ ΞΑΝΑ</button>
              </div>
              <div class="transcript">${escapeHtml(node.text)}</div>` : ''}
            <div class="choice-grid">${choices}</div>
            <p class="helper-text">Επίλεξε τι θα έκανες στην πραγματική ζωή. Μπορείς να πάρεις τον χρόνο σου.</p>
          </section>
        </div>
      </article>`;

    if (node.audio) {
      document.getElementById('replayAudio').addEventListener('click', () => playNodeAudio(node));
      playNodeAudio(node);
    }

    document.querySelectorAll('[data-choice-index]').forEach((button) => {
      button.addEventListener('click', () => {
        callAnswered = true;
        const choice = node.choices[Number(button.dataset.choiceIndex)];

        if (choice.intent === "unsafe") {
          accidentVictim = true;
        }

        score = clampScore(score + (choice.score_delta || 0));

        const isPoliceChoice =
          choice.label === "Θα καλέσω εγώ την αστυνομία και θα επιβεβαιώσω τι έχει συμβεί.";

        if (isPoliceChoice) {

          if (!threatStarted) {

            if (node.id === "fake_police_call") {

              currentNodeId = choice.next_node;

            } else {

              policeVerifyAttempts++;

              if (policeVerifyAttempts >= 2) {
                currentNodeId = "escalation_threat";
                threatStarted = true;
                threatVerifyAttempts = 0;
              } else {
                currentNodeId = choice.next_node;
              }

            }

          } else {

            threatVerifyAttempts++;

            if (threatVerifyAttempts >= 2) {
              currentNodeId = "accident_unsafe_final";
            } else {
              currentNodeId = choice.next_node;
            }

          }

        } else {
          currentNodeId = choice.next_node;
        }

        saveSession();
        renderCurrentNode();
      });
    });

    resetIdleTimers();
  }

  function renderResult(node) {
    setCallMode('result');
    stopAllCallAudio();
    score = clampScore(score + (node.score_delta || 0));
    saveSession();

    const flags = (node.red_flags || []).map(flag => `<li>${escapeHtml(flag)}</li>`).join('');
    const unsafeHelpLayout = [
      "unsafe_help_reaction",
      "fake_police_analysis_result"
    ].includes(node.id);


    const unsafeResultNode = [
      "unsafe_code_end",
      "accident_unsafe_final"
    ].includes(node.id);


    const lesson = scenario.educational_message;
    const isUnsafeHelpReaction = unsafeHelpLayout;

    const victimBanner = (
      accidentVictim ||
      isUnsafeHelpReaction ||
      unsafeResultNode ||
      node.id === "fake_police_analysis_result"
    )
      ? '<div class="result-badge victim-alert">☹️ ΜΗ ΑΣΦΑΛΗΣ ΑΝΤΙΔΡΑΣΗ</div>'
      : '<div class="result-badge safe-result">✅ ΣΩΣΤΗ ΑΝΤΙΔΡΑΣΗ - ΑΝΑΓΝΩΡΙΣΕΣ ΤΑ ΣΗΜΑΔΙΑ ΑΠΑΤΗΣ</div>';


    screen.innerHTML = `
      <article class="experience-card result-card">
        ${victimBanner}
        

        ${unsafeHelpLayout
          ? `<div class="unsafe-help-hero">
              
<div class="unsafe-help-message">
  <div class="unsafe-help-line1">
    ΔΥΣΤΥΧΩΣ Ο ΑΠΑΤΕΩΝΑΣ ΚΑΤΑΦΕΡΕ ΝΑ ΣΕ ΧΕΙΡΑΓΩΓΗΣΕΙ
  </div>
  <div class="unsafe-help-line2">
    ΜΕ ΜΕΓΑΛΗ ΠΙΘΑΝΟΤΗΤΑ ΝΑ ΠΕΣΕΙΣ ΘΥΜΑ ΑΠΑΤΗΣ
  </div>
</div>
            </div>`
          : `<h1>${reactionStatus(node, score, accidentVictim, threatStarted)}</h1>`}

        ${unsafeHelpLayout ? "" : `<p>${escapeHtml(node.text)}</p>`}

        <div class="score-panel" aria-label="Βαθμολογία αντίδρασης">
          <div class="score-label">${reactionStatus(node, score, accidentVictim, threatStarted)}</div>
        </div>

        <div class="red-flags">
          <h2>Τι προσπάθησε να εκμεταλλευτεί ο απατεώνας</h2>
          <ul>${flags}</ul>
        </div>

        <div class="lesson-grid">
          <section class="lesson"><h2>1 · ΣΤΑΜΑΤΑ</h2><p>${escapeHtml(lesson.stop)}</p></section>
          <section class="lesson"><h2>2 · ΕΛΕΓΞΕ</h2><p>${escapeHtml(lesson.check)}</p></section>
          <section class="lesson"><h2>3 · ΕΠΙΒΕΒΑΙΩΣΕ</h2><p>${escapeHtml(lesson.verify)}</p></section>
        </div>

        <p><strong>Ασφαλέστερη ενέργεια:</strong> ${escapeHtml(node.safe_action)}</p>
        <div class="result-actions">
          <button id="retryBtn" class="primary-button" type="button">ΔΟΚΙΜΑΣΕ ΞΑΝΑ</button>
          <button id="finishBtn" class="audio-button" type="button">ΤΕΛΟΣ / ΑΡΧΙΚΗ</button>
        </div>
      </article>`;

    document.getElementById('retryBtn').addEventListener('click', () => {
      score = INITIAL_SCORE;
      policeVerifyAttempts = 0;
      accidentVictim = false;
      currentNodeId = scenario.start_node;
      saveSession();
      renderCurrentNode();

      if (typeof fraudLabStartRing === 'function') {
        fraudLabStartRing();
      }
    });
    document.getElementById('finishBtn').addEventListener('click', showAttract);
    resetIdleTimers();
  }

  function renderFatal(message) {
    setCallMode('error');
    stopAudio();
    screen.innerHTML = `
      <section class="status-error">
        <h1>Το station χρειάζεται επανεκκίνηση</h1>
        <p>${escapeHtml(message)}</p>
        <button class="primary-button" id="fatalHome" type="button">ΑΡΧΙΚΗ</button>
      </section>`;
    document.getElementById('fatalHome').addEventListener('click', showAttract);
  }

  function restartExperience() {
    timeoutModal.hidden = true;
    showAttract();
  }

  function toggleAssist() {
    assisted = !assisted;
    document.body.classList.toggle('assisted', assisted);
    assistBtn.setAttribute('aria-pressed', String(assisted));
    saveSession();
  }

  async function init() {
    await loadCallAmbientManifest();
    try {
      const response = await fetch(`/api/scenarios/${SCENARIO_ID}`, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      scenario = await response.json();

      const listResponse = await fetch('/api/scenarios', { cache: 'no-store' });
      scenarioList = await listResponse.json();

      showAttract();
    } catch (error) {
      renderFatal('Δεν φορτώθηκαν τα local δεδομένα του σεναρίου. Ελέγξτε ότι τρέχει το run_local.py.');
      console.error(error);
    }
  }

  homeBtn.addEventListener('click', () => {
    stopAudio();

    if (typeof fraudLabStopRing === 'function') {
      fraudLabStopRing();
    }

    window.location.href = '/';
  });
  assistBtn.addEventListener('click', toggleAssist);
  continueBtn.addEventListener('click', () => {
    timeoutModal.hidden = true;
    resetIdleTimers();
  });

  ['pointerdown', 'touchstart'].forEach(eventName => {
    document.addEventListener(eventName, registerActivity, { passive: true });
  });

  document.addEventListener('keydown', (event) => {
    registerActivity();
    if (!timeoutModal.hidden) {
      if (event.key === 'Enter' || event.key === ' ') continueBtn.click();
      return;
    }

    if (['1', '2', '3'].includes(event.key)) {
      const button = document.querySelector(`[data-choice-index=\"${Number(event.key) - 1}\"]`);
      if (button) button.click();
    } else if (event.key.toLowerCase() === 'h') {
      homeBtn.click();
    } else if (event.key.toLowerCase() === 'r') {
      const replay = document.getElementById('replayAudio');
      if (replay) replay.click();
    }
  });

  window.addEventListener('beforeunload', stopAudio);
  init();


  /* FRAUD_LAB_RING_START */

  document.addEventListener(
    'click',
    event => {

      const button =
        event.target.closest('button');

      if (!button) {
        return;
      }

      const label =
        (button.textContent || '')
          .trim()
          .toUpperCase();


      const isStartButton =
        button.id === 'startBtn' ||
        label.includes(
          'ΕΝΑΡΞΗ ΠΡΟΣΟΜΟΙΩΣΗΣ'
        );


      if (isStartButton) {

        fraudLabStartRing();
        return;

      }


      // Once the phone is ringing,
      // any subsequent visitor action
      // ends the incoming-call sound.
      if (!fraudLabRing.paused) {

        fraudLabStopRing();

      }

    },
    true
  );


  window.addEventListener(
    'beforeunload',
    fraudLabStopRing
  );

  /* FRAUD_LAB_RING_END */


})();

