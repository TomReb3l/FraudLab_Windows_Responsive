(() => {
  'use strict';

  const screen = document.getElementById('screen');
  const homeBtn = document.getElementById('homeBtn');
  const assistBtn = document.getElementById('assistBtn');
  const timeoutModal = document.getElementById('timeoutModal');
  const continueBtn = document.getElementById('continueBtn');
  const qrSimulationOverlay = document.getElementById('qrSimulationOverlay');
  const qrSimulationViewport = document.getElementById('qrSimulationViewport');
  const qrSimulationFrame = document.getElementById('qrSimulationFrame');
  const qrSimulationTitle = document.getElementById('qrSimulationTitle');
  const closeQrSimulationBtn = document.getElementById('closeQrSimulationBtn');

  const IDLE_WARNING_MS = 65000;
  const IDLE_RESET_MS = 75000;

  let data = null;
  let currentIndex = 0;
  let score = 0;
  let answered = false;
  let assisted = false;
  let hadUnsafeChoice = false;

  const MAIL_AUDIO_SRC = '/static/audio/mail_notification.mp3';
  let mailAudio = null;

  function ensureMailAudio() {
    if (!mailAudio) {
      mailAudio = new Audio(MAIL_AUDIO_SRC);
      mailAudio.preload = 'auto';
      mailAudio.volume = 0.75;
    }
    return mailAudio;
  }

  function playMailNotification() {
    try {
      const audio = ensureMailAudio();
      audio.pause();
      audio.currentTime = 0;
      audio.play().catch(() => {});
    } catch (error) {
      console.warn('Mail notification audio unavailable:', error);
    }
  }
  let warningTimer = null;
  let resetTimer = null;
  let qrSimulationTimer = null;
  let qrSimulationReturnFocus = null;

  const QR_SIMULATION_MAX_MS = 180000;

  const escapeHtml = value =>
    String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');



  function reactionStatus(value, unsafe) {
    if (unsafe && value < 40) {
      return '🔴 ΚΙΝΔΥΝΟΣ';
    }

    if (unsafe) {
      return '🟡 ΠΡΟΣΟΧΗ';
    }

    return '🟢 ΑΣΦΑΛΗΣ';
  }


  function resetIdleTimers() {
    window.clearTimeout(warningTimer);
    window.clearTimeout(resetTimer);
    timeoutModal.hidden = true;

    warningTimer = window.setTimeout(() => {
      timeoutModal.hidden = false;
      continueBtn.focus();
    }, IDLE_WARNING_MS);

    resetTimer = window.setTimeout(() => {
      showIntro();
    }, IDLE_RESET_MS);
  }


  function registerActivity() {
    if (!qrSimulationOverlay.hidden) {
      return;
    }

    resetIdleTimers();
  }


  function closeQrSimulation({ restartIdle = true, restoreFocus = true } = {}) {
    window.clearTimeout(qrSimulationTimer);
    qrSimulationTimer = null;

    if (qrSimulationOverlay.hidden) {
      return;
    }

    qrSimulationOverlay.hidden = true;
    document.body.classList.remove('qr-simulation-open');
    qrSimulationFrame.src = 'about:blank';
    qrSimulationFrame.style.height = '100%';
    qrSimulationViewport.scrollTop = 0;

    const focusTarget = qrSimulationReturnFocus;
    qrSimulationReturnFocus = null;

    if (restartIdle) {
      resetIdleTimers();
    }

    if (restoreFocus && focusTarget && document.contains(focusTarget)) {
      focusTarget.focus();
    }
  }


  function openQrSimulation(item, triggerButton) {
    const url = String(item.simulation_url || '');

    if (!/^\/static\/qr_sites\/(traffic|parcel|account|invoice)\/index\.html$/.test(url)) {
      console.warn('Blocked invalid QR simulation URL:', url);
      return;
    }

    window.clearTimeout(warningTimer);
    window.clearTimeout(resetTimer);
    timeoutModal.hidden = true;

    qrSimulationReturnFocus = triggerButton;
    qrSimulationTitle.textContent = `ΠΡΟΣΟΜΟΙΩΣΗ · ${item.category}`;
    qrSimulationViewport.scrollTop = 0;
    qrSimulationFrame.style.height = '100%';
    qrSimulationFrame.src = `${url}?v=1`;
    qrSimulationOverlay.hidden = false;
    document.body.classList.add('qr-simulation-open');
    closeQrSimulationBtn.focus();

    window.clearTimeout(qrSimulationTimer);
    qrSimulationTimer = window.setTimeout(() => {
      closeQrSimulation({ restartIdle: false, restoreFocus: false });
      showIntro();
    }, QR_SIMULATION_MAX_MS);
  }


  function resetMobileViewport() {
    if (!window.matchMedia('(max-width: 768px)').matches) return;

    window.requestAnimationFrame(() => {
      window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
      screen.scrollTop = 0;
    });
  }


  function showIntro() {
    currentIndex = 0;
    score = 0;

    screen.innerHTML = `
      <article class="intro-card">

        <div class="eyebrow">EMAIL · QR · ΙΣΤΟΣΕΛΙΔΑ</div>
        <h1>Σκάναρες ένα QR. Πώς θα συνέχιζες;</h1>
        <p>
          Θα δεις τέσσερις περιπτώσεις. Το ζητούμενο δεν είναι να
          «μαντέψεις» αν το QR είναι κακό, αλλά να αποφασίσεις
          τι θα κάνεις όταν ο προορισμός ζητά χρήματα ή στοιχεία.
        </p>
        <button id="startBtn" class="primary-btn">ΕΝΑΡΞΗ</button>
      </article>
    `;

    document.getElementById('startBtn').addEventListener('click', renderItem);
    resetMobileViewport();
    resetIdleTimers();
  }


  function renderFakeForm(fakeForm) {
    if (fakeForm.mode === 'vehicle_lookup') {
      return `
        <div class="fake-form vehicle-lookup-form">
          <label for="vehiclePlateInput">${escapeHtml(fakeForm.field_1_label)}</label>
          <input
            id="vehiclePlateInput"
            class="fake-input fake-input-control"
            type="text"
            inputmode="text"
            autocomplete="off"
            autocapitalize="characters"
            spellcheck="false"
            maxlength="14"
            placeholder="${escapeHtml(fakeForm.field_1_placeholder || '')}"
          >

          <button id="vehicleLookupBtn" type="button">
            ${escapeHtml(fakeForm.lookup_button_text || 'ΑΝΑΖΗΤΗΣΗ')}
          </button>

          <p id="vehicleLookupError" class="fake-form-error" hidden>
            Πληκτρολόγησε έναν αριθμό κυκλοφορίας για να συνεχίσεις.
          </p>

          <section id="vehicleLookupResult" class="vehicle-lookup-result" hidden aria-live="polite">
            <div class="vehicle-lookup-status">
              ${escapeHtml(fakeForm.lookup_status || 'Βρέθηκε ανεξόφλητη παράβαση')}
            </div>

            <div class="vehicle-lookup-row">
              <span>${escapeHtml(fakeForm.plate_label || 'Αριθμός κυκλοφορίας')}</span>
              <strong id="vehiclePlateResult"></strong>
            </div>

            <div class="vehicle-lookup-row">
              <span>${escapeHtml(fakeForm.amount_label || 'Ποσό')}</span>
              <strong>${escapeHtml(fakeForm.lookup_amount || '')}</strong>
            </div>

            <button class="vehicle-pay-button" type="button" disabled>
              ${escapeHtml(fakeForm.button_text || 'ΕΞΟΦΛΗΣΗ ΠΑΡΑΒΑΣΗΣ')}
            </button>
          </section>
        </div>
      `;
    }

    return `
      <div class="fake-form">
        <label>${escapeHtml(fakeForm.field_1_label)}</label>
        <div class="fake-input">${escapeHtml(fakeForm.field_1_value)}</div>

        <label>${escapeHtml(fakeForm.field_2_label)}</label>
        <div class="fake-input">${escapeHtml(fakeForm.field_2_value)}</div>

        <button type="button" disabled>
          ${escapeHtml(fakeForm.button_text)}
        </button>
      </div>
    `;
  }


  function setupFakeFormInteraction(fakeForm) {
    if (fakeForm.mode !== 'vehicle_lookup') return;

    const input = document.getElementById('vehiclePlateInput');
    const lookupBtn = document.getElementById('vehicleLookupBtn');
    const result = document.getElementById('vehicleLookupResult');
    const plateResult = document.getElementById('vehiclePlateResult');
    const error = document.getElementById('vehicleLookupError');

    if (!input || !lookupBtn || !result || !plateResult || !error) return;

    const runLookup = () => {
      const normalized = input.value
        .trim()
        .toLocaleUpperCase('el-GR')
        .replace(/\s+/g, ' ')
        .slice(0, 14);

      if (!normalized) {
        error.hidden = false;
        result.hidden = true;
        input.setAttribute('aria-invalid', 'true');
        input.focus();
        return;
      }

      error.hidden = true;
      input.removeAttribute('aria-invalid');
      plateResult.textContent = normalized;
      result.hidden = false;
    };

    lookupBtn.addEventListener('click', runLookup);

    input.addEventListener('keydown', event => {
      if (event.key === 'Enter') {
        event.preventDefault();
        runLookup();
      }
    });
  }



  function renderItem() {
    answered = false;

    const item = data.items[currentIndex];

    const simulationButton = item.simulation_url
      ? `
        <button id="openQrSimulationBtn" class="qr-sim-trigger" type="button">
          ΠΑΤΗΣΤΕ ΕΔΩ
        </button>
        <p class="qr-sim-helper">Ή ΣΚΑΝΑΡΕΤΕ ΤΟ QR ΓΙΑ ΝΑ ΜΕΤΑΦΕΡΘΕΙΤΕ ΣΤΗ ΣΕΛΙΔΑ</p>
      `
      : '';

    const choices = item.choices.map((choice, i) => `
      <button class="choice-btn" data-choice="${i}">
        <span>${i + 1}</span>
        ${escapeHtml(choice.label)}
      </button>
    `).join('');

    const scenarioVisual = item.qr_image
      ? `
        <div class="mail-preview-visual" aria-label="Εκπαιδευτικό QR ή οπτικό σήμα">
          <img class="scenario-qr-image" src="${escapeHtml(item.qr_image)}" alt="QR code σεναρίου">
        </div>
      `
      : '';

    screen.innerHTML = `
      <article class="challenge-layout challenge-layout--mail">
        <section class="left-panel left-panel--mail">
          <div class="progress">
            <span>ΣΕΝΑΡΙΟ ${currentIndex + 1} ΑΠΟ ${data.items.length}</span>
            <span>SCORE ${score}/100</span>
          </div>

          <div class="poster-card poster-card--mail" aria-label="Μήνυμα ή ειδοποίηση σεναρίου">
            <div class="mail-preview-shell">
              <div class="mail-preview-toolbar">
                <div class="mail-preview-dots">● ● ●</div>
                <div class="mail-preview-address">${escapeHtml(item.url)}</div>
              </div>

              <div class="mail-preview-body">
                <div class="mail-preview-meta">
                  <div class="mail-preview-badge">${escapeHtml(item.category)}</div>
                  <div class="mail-preview-site">${escapeHtml(item.site_name)}</div>
                </div>

                <h2>${escapeHtml(item.poster_title)}</h2>
                <p class="mail-preview-copy">${escapeHtml(item.poster_text)}</p>

                <div class="mail-preview-content-row ${item.qr_image ? '' : 'no-visual'}">
                  ${scenarioVisual}
                  <div class="mail-preview-cta-zone">
                    ${simulationButton}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="choice-area choice-area--mail">
            <h1>Τι θα έκανες;</h1>
            <div class="choice-grid">${choices}</div>
          </div>
        </section>
      </article>
    `;

    document.querySelectorAll('[data-choice]').forEach(button => {
      button.addEventListener('click', () => {
        chooseAnswer(Number(button.dataset.choice));
      });
    });

    const openQrSimulationBtn = document.getElementById('openQrSimulationBtn');
    if (openQrSimulationBtn) {
      openQrSimulationBtn.addEventListener('click', () => {
        openQrSimulation(item, openQrSimulationBtn);
      });
    }

    playMailNotification();
    resetMobileViewport();
    resetIdleTimers();
  }


  function chooseAnswer(index) {
    if (answered) return;
    answered = true;

    const item = data.items[currentIndex];
    const choice = item.choices[index];

    if (!choice.safe) {
      hadUnsafeChoice = true;
    }

    score = Math.min(
      data.max_score,
      score + Number(choice.score || 0)
    );

    renderFeedback(item, choice);
  }


  function renderFeedback(item, choice) {
    const flags = item.red_flags
      .map(flag => `<li>${escapeHtml(flag)}</li>`)
      .join('');

    const victimBanner = !choice.safe
      ? '<div class="result-badge victim-alert">☹️ ΔΥΣΤΥΧΩΣ ΕΠΕΣΕΣ ΘΥΜΑ ΑΠΑΤΗΣ</div>'
      : '';

    screen.innerHTML = `
      <article class="qr-feedback-card">
        <div class="eyebrow">EMAIL · QR · ΙΣΤΟΣΕΛΙΔΑ</div>
        <h1>ΑΝΑΛΥΣΗ ΑΠΑΝΤΗΣΗΣ</h1>

        ${victimBanner}

        <section class="feedback-panel">
          <div class="result-label ${choice.safe ? 'safe-text' : 'risk-text'}">
            ${choice.safe ? 'ΑΣΦΑΛΗΣ ΑΝΤΙΔΡΑΣΗ' : 'ΧΡΕΙΑΖΕΤΑΙ ΠΡΟΣΟΧΗ'}
          </div>

          <p>${escapeHtml(choice.feedback)}</p>
        </section>

        <div class="feedback-grid">
          <section>
            <h2>ΣΗΜΑΔΙΑ ΚΙΝΔΥΝΟΥ</h2>
            <ul>${flags}</ul>
          </section>

          <section>
            <h2>ΑΣΦΑΛΕΣΤΕΡΗ ΕΝΕΡΓΕΙΑ</h2>
            <p>${escapeHtml(item.safe_action)}</p>
          </section>
        </div>

        <button id="nextBtn" class="primary-btn feedback-next">
          ${currentIndex === data.items.length - 1 ? 'ΔΕΣ ΑΠΟΤΕΛΕΣΜΑ' : 'ΕΠΟΜΕΝΟ ΣΕΝΑΡΙΟ'}
        </button>
      </article>
    `;

    document.getElementById('nextBtn').addEventListener('click', () => {
      if (currentIndex < data.items.length - 1) {
        currentIndex += 1;
        renderItem();
      } else {
        renderResult();
      }
    });

    resetMobileViewport();
    resetIdleTimers();
  }


  function renderResult() {
    const lesson = data.educational_message;

    const victimBanner = hadUnsafeChoice
      ? '<div class="result-badge victim-alert">☹️ ΔΥΣΤΥΧΩΣ ΕΠΕΣΕΣ ΘΥΜΑ ΑΠΑΤΗΣ</div>'
      : '';

    screen.innerHTML = `
      <article class="result-card">

        ${victimBanner}

        <div class="eyebrow">ΟΛΟΚΛΗΡΩΣΗ STATION 3</div>

        <h1>${reactionStatus(score, hadUnsafeChoice)}</h1>

        <p class="result-lead">
          Ένα email, ένα QR code ή ένα κουμπί «ΠΑΤΗΣΤΕ ΕΔΩ» δεν είναι απόδειξη ασφάλειας.
          Είναι τρόποι να οδηγηθείς σε έναν προορισμό που πρέπει πρώτα να ελέγξεις.
        </p>

        <div class="lesson-grid">

          <section>
            <h2>ΣΤΑΜΑΤΑ</h2>
            <p>${escapeHtml(lesson.stop)}</p>
          </section>

          <section>
            <h2>ΕΛΕΓΞΕ</h2>
            <p>${escapeHtml(lesson.check)}</p>
          </section>

          <section>
            <h2>ΕΠΙΒΕΒΑΙΩΣΕ</h2>
            <p>${escapeHtml(lesson.verify)}</p>
          </section>

        </div>

        <div class="result-actions">
          <button id="retryBtn" class="primary-btn">ΔΟΚΙΜΑΣΕ ΞΑΝΑ</button>
          <button id="resultHomeBtn" class="secondary-btn">ΑΡΧΙΚΗ FRAUD LAB</button>
        </div>

      </article>
    `;

    document.getElementById('retryBtn').addEventListener('click', showIntro);

    document.getElementById('resultHomeBtn').addEventListener('click', () => {
      window.location.href = '/';
    });

    resetMobileViewport();
    resetIdleTimers();
  }


  assistBtn.addEventListener('click', () => {
    assisted = !assisted;
    document.body.classList.toggle('assisted', assisted);
    assistBtn.setAttribute('aria-pressed', String(assisted));
  });

  homeBtn.addEventListener('click', () => {
    window.location.href = '/';
  });

  continueBtn.addEventListener('click', () => {
    timeoutModal.hidden = true;
    resetIdleTimers();
  });

  closeQrSimulationBtn.addEventListener('click', () => {
    closeQrSimulation();
  });

  window.addEventListener('message', event => {
    if (event.source !== qrSimulationFrame.contentWindow) {
      return;
    }

    const message = event.data;
    if (!message || typeof message !== 'object') {
      return;
    }

    if (message.type === 'fraudlab:qr-sim-height') {
      const reportedHeight = Number(message.height);
      if (!Number.isFinite(reportedHeight) || reportedHeight < 1) {
        return;
      }

      const viewportHeight = Math.max(1, qrSimulationViewport.clientHeight);
      const safeHeight = Math.min(6000, Math.ceil(reportedHeight));
      qrSimulationFrame.style.height = `${Math.max(viewportHeight, safeHeight)}px`;
      return;
    }

    if (message.type === 'fraudlab:qr-sim-scroll-top') {
      qrSimulationViewport.scrollTo({ top: 0, behavior: 'smooth' });
    }
  });

  ['pointerdown', 'touchstart'].forEach(eventName => {
    document.addEventListener(eventName, registerActivity, { passive: true });
  });

  document.addEventListener('keydown', event => {
    if (!qrSimulationOverlay.hidden) {
      if (event.key === 'Escape') {
        closeQrSimulation();
      }
      return;
    }

    registerActivity();
  });


  async function init() {
    try {
      const response = await fetch('/api/qr-challenge', { cache: 'no-store' });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      data = await response.json();

      if (!Array.isArray(data.items) || data.items.length === 0) {
        throw new Error('No QR scenarios');
      }

      showIntro();

    } catch (error) {
      console.error(error);

      screen.innerHTML = `
        <section class="fatal-card">
          <h1>Το Station 3 χρειάζεται επανεκκίνηση</h1>
          <button class="primary-btn" onclick="location.reload()">
            ΕΠΑΝΕΚΚΙΝΗΣΗ
          </button>
        </section>
      `;
      resetMobileViewport();
    }
  }

  init();

})();
