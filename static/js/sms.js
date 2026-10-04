(() => {
  'use strict';

  const API_URL = '/api/sms-challenge';

  const IDLE_WARNING_MS = 65000;
  const IDLE_RESET_MS = 75000;

  const screen = document.getElementById('screen');
  const homeBtn = document.getElementById('homeBtn');
  const assistBtn = document.getElementById('assistBtn');
  const timeoutModal = document.getElementById('timeoutModal');
  const continueBtn = document.getElementById('continueBtn');
  const simulationOverlay = document.getElementById('simulationOverlay');
  const simulationViewport = document.getElementById('simulationViewport');
  const simulationFrame = document.getElementById('simulationFrame');
  const simulationOverlayTitle = document.getElementById('simulationOverlayTitle');
  const closeSimulationBtn = document.getElementById('closeSimulationBtn');

  let data = null;
  let currentIndex = 0;
  let score = 0;
  let hadUnsafeChoice = false;
  let answered = false;
  let assisted = false;

  let warningTimer = null;
  let resetTimer = null;
  let simulationTimer = null;
  let simulationReturnFocus = null;

  const SIMULATION_MAX_MS = 180000;

  const smsSound = new Audio(
    '/static/audio/ui/incoming_sms.mp3'
  );

  smsSound.preload = 'auto';
  smsSound.volume = 0.90;


  function playSmsNotification() {

    try {

      smsSound.pause();
      smsSound.currentTime = 0;

      const playback = smsSound.play();

      if (playback) {

        playback.catch(error => {
          console.warn(
            'SMS sound blocked:',
            error
          );
        });

      }

    } catch (error) {

      console.warn(
        'SMS sound failed:',
        error
      );

    }

  }



  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }



  // SMS FINAL STATUS SHIELD v2
  function reactionStatus(value, unsafe) {
    if (unsafe && value < 40) {
      return { label: 'ΚΙΝΔΥΝΟΣ', tone: 'danger' };
    }

    if (unsafe) {
      return { label: 'ΠΡΟΣΟΧΗ', tone: 'caution' };
    }

    return { label: 'ΑΣΦΑΛΗΣ', tone: 'safe' };
  }

  function renderReactionStatus(value, unsafe) {
    const status = reactionStatus(value, unsafe);

    const mark = status.tone === 'safe'
      ? '<path class="final-status-shield-mark" d="M18 37.5 27 46l19-22 5 4.5L27.5 56 13 42.5 18 37.5Z"></path>'
      : '<path class="final-status-shield-mark" d="M28.5 18h7L34.4 43h-4.8L28.5 18Zm.2 31h6.6v6.6h-6.6V49Z"></path>';

    return `
      <h1 class="final-status final-status--${status.tone}">
        <span class="final-status-shield" aria-hidden="true">
          <svg viewBox="0 0 64 72" focusable="false">
            <path
              class="final-status-shield-shape"
              d="M32 2 56 11v20c0 17.8-10.4 31.5-24 39C18.4 62.5 8 48.8 8 31V11L32 2Z"
            ></path>
            ${mark}
          </svg>
        </span>
        <span class="final-status-label">${status.label}</span>
      </h1>
    `;
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
      showIntro();
    }, IDLE_RESET_MS);
  }


  function registerActivity() {
    if (!simulationOverlay.hidden) {
      return;
    }

    resetIdleTimers();
  }


  function closeSimulation({ restartIdle = true, restoreFocus = true } = {}) {
    clearTimeout(simulationTimer);
    simulationTimer = null;

    if (simulationOverlay.hidden) {
      return;
    }

    simulationOverlay.hidden = true;
    document.body.classList.remove('simulation-open');
    simulationFrame.src = 'about:blank';
    simulationFrame.style.height = '100%';
    simulationViewport.scrollTop = 0;

    const focusTarget = simulationReturnFocus;
    simulationReturnFocus = null;

    if (restartIdle) {
      resetIdleTimers();
    }

    if (restoreFocus && focusTarget && document.contains(focusTarget)) {
      focusTarget.focus();
    }
  }


  function openSimulation(item, triggerButton) {
    const url = String(item.simulation_url || '');

    if (!/^\/static\/sms_sites\/index\.html\?scenario=(courier_fee|bank_alert|marketplace_payment|traffic_fine_sms)$/.test(url)) {
      console.warn('Blocked invalid simulation URL:', url);
      return;
    }

    clearTimeout(warningTimer);
    clearTimeout(resetTimer);
    timeoutModal.hidden = true;

    simulationReturnFocus = triggerButton;
    simulationOverlayTitle.textContent = `ΠΡΟΣΟΜΟΙΩΣΗ · ${item.category}`;
    simulationViewport.scrollTop = 0;
    simulationFrame.style.height = '100%';
    simulationFrame.src = `${url}&v=3`;
    simulationOverlay.hidden = false;
    document.body.classList.add('simulation-open');
    closeSimulationBtn.focus();

    clearTimeout(simulationTimer);
    simulationTimer = window.setTimeout(() => {
      closeSimulation({ restartIdle: false, restoreFocus: false });
      showIntro();
    }, SIMULATION_MAX_MS);
  }


  function resetMobileScroll() {
    if (window.matchMedia('(max-width: 768px)').matches) {
      window.scrollTo(0, 0);
    }
  }


  function scoreLabel(value) {
    if (value >= 90) {
      return 'Ισχυρή Αντίσταση στο Phishing';
    }

    if (value >= 70) {
      return 'Καλή Αντίδραση — Μερικά σημεία χρειάζονται προσοχή';
    }

    if (value >= 50) {
      return 'Ορισμένα μηνύματα κατάφεραν να δημιουργήσουν πίεση';
    }

    return 'Δες ποια σημεία προσπάθησαν να επηρεάσουν την απόφασή σου';
  }


  function showIntro() {
    currentIndex = 0;
    score = 0;
    answered = false;
    hadUnsafeChoice = false;

    screen.innerHTML = `
      <article class="intro-card">

        <div class="intro-kicker">
          ΜΗΝΥΜΑ Ή ΠΑΓΙΔΑ;
        </div>

        <h1>
          Έλαβες ένα μήνυμα στο κινητό σου. Τι θα έκανες;
        </h1>

        <p>
          Θα δεις πέντε σύντομα μηνύματα.
          Δεν χρειάζεται να αποδείξεις αν είναι πραγματικά ή ψεύτικα.
          Επίλεξε τι θα έκανες στην πραγματική ζωή.
        </p>

        <div class="privacy-note">
          Οι σύνδεσμοι που ανοίγουν είναι τοπικές εκπαιδευτικές προσομοιώσεις.
          Δεν αποστέλλονται ή αποθηκεύονται στοιχεία.
        </div>

        <button id="startBtn" class="primary-btn" type="button">
          ΕΝΑΡΞΗ CHALLENGE
        </button>

      </article>
    `;

    resetMobileScroll();

    document
      .getElementById('startBtn')
      .addEventListener('click', () => {

        renderItem();

      });

    resetIdleTimers();
  }


  function renderItem() {
    answered = false;

    playSmsNotification();

    const item = data.items[currentIndex];

    const choices = item.choices
      .map(
        (choice, index) => `
          <button
            class="choice-btn"
            type="button"
            data-choice-index="${index}"
          >
            <span class="choice-number">${index + 1}</span>
            <span>${escapeHtml(choice.label)}</span>
          </button>
        `
      )
      .join('');


    const simulationButton = item.simulation_url
      ? `
        <button
          id="simulationLinkBtn"
          class="sms-sim-trigger"
          type="button"
        >
          ${escapeHtml(item.simulation_label || 'ΠΑΤΑ ΕΔΩ')}
        </button>
      `
      : '';

    const linkBlock = item.link_text
      ? `
        <div class="fake-link">
          ${escapeHtml(item.link_text)}
        </div>

        ${simulationButton}

        <div class="simulation-note">
          ${escapeHtml(item.link_warning)}
          ${item.simulation_url ? '<br><strong>Η προσομοίωση δεν επηρεάζει το score.</strong>' : ''}
        </div>
      `
      : '';


    screen.innerHTML = `
      <article class="challenge-layout">

        <section class="challenge-info">

          <div class="progress-row">

            <div>
              ΜΗΝΥΜΑ ${currentIndex + 1}
              ΑΠΟ ${data.items.length}
            </div>

            <div>
              SCORE ${score}/100
            </div>

          </div>

          <div class="category">
            ${escapeHtml(item.category)}
          </div>

          <h1>Τι θα έκανες;</h1>

          <p class="question-copy">
            Διάβασε το μήνυμα όπως θα το έβλεπες
            στο κινητό σου και διάλεξε την αντίδρασή σου.
          </p>

          <div class="choice-grid">
            ${choices}
          </div>

          <section id="feedbackPanel" class="feedback-panel" hidden></section>

        </section>


        <section class="phone-preview" aria-label="Προσομοίωση SMS">

          <div class="phone-device">

            <div class="phone-status">
              <span>09:41</span>
              <span>● ● ●</span>
            </div>

            <div class="messages-header">
              <div class="avatar">?</div>

              <div>
                <strong>${escapeHtml(item.sender)}</strong>
                <small>SMS</small>
              </div>
            </div>

            <div class="message-area">

              <div class="sms-bubble">

                <p>
                  ${escapeHtml(item.message)}
                </p>

                ${linkBlock}

                <time>
                  ${escapeHtml(item.time)}
                </time>

              </div>

            </div>

            <div class="phone-warning">
              ΕΚΠΑΙΔΕΥΤΙΚΗ ΠΡΟΣΟΜΟΙΩΣΗ
            </div>

          </div>

        </section>

      </article>
    `;

    resetMobileScroll();

    document
      .querySelectorAll('[data-choice-index]')
      .forEach(button => {
        button.addEventListener('click', () => {
          chooseAnswer(
            Number(button.dataset.choiceIndex)
          );
        });
      });

    const simulationLinkBtn =
      document.getElementById('simulationLinkBtn');

    if (simulationLinkBtn) {
      simulationLinkBtn.addEventListener('click', () => {
        openSimulation(item, simulationLinkBtn);
      });
    }

    resetIdleTimers();
  }


  function chooseAnswer(choiceIndex) {
    if (answered) {
      return;
    }

    answered = true;

    const item = data.items[currentIndex];
    const choice = item.choices[choiceIndex];

    if (!choice.safe) {
      hadUnsafeChoice = true;
    }

    score += Number(choice.score || 0);

    score = Math.max(
      0,
      Math.min(data.max_score, score)
    );

    const flags = item.red_flags
      .map(flag => `<li>${escapeHtml(flag)}</li>`)
      .join('');

    const buttonLabel =
      currentIndex === data.items.length - 1
        ? 'ΔΕΣ ΤΟ ΑΠΟΤΕΛΕΣΜΑ'
        : 'ΕΠΟΜΕΝΟ ΜΗΝΥΜΑ';

    const victimBanner = !choice.safe
      ? '<div class="result-badge victim-alert">☹️ ΔΥΣΤΥΧΩΣ ΕΠΕΣΕΣ ΘΥΜΑ ΑΠΑΤΗΣ</div>'
      : '';

    screen.innerHTML = `
      <article class="feedback-view premium-view">
        <section class="premium-panel feedback-shell">
          <div class="premium-headline-row">
            ${victimBanner}
            <div class="section-kicker">SMS / PHISHING</div>
            <div class="section-title-small">ΑΝΑΛΥΣΗ ΑΠΑΝΤΗΣΗΣ</div>
          </div>

          <section class="premium-card feedback-summary-card">
            <div class="feedback-summary-top">
              <div>
                <div class="panel-label">Η ΕΠΙΛΟΓΗ ΣΟΥ</div>
                <div class="feedback-result ${choice.safe ? 'safe' : 'risk'}">
                  ${choice.safe ? 'ΑΣΦΑΛΗΣ ΑΝΤΙΔΡΑΣΗ' : 'ΧΡΕΙΑΖΕΤΑΙ ΠΕΡΙΣΣΟΤΕΡΗ ΠΡΟΣΟΧΗ'}
                </div>
              </div>

              <div class="score-chip">
                ΜΗΝΥΜΑ ${currentIndex + 1}/${data.items.length}
                <span>•</span>
                SCORE ${score}/${data.max_score}
              </div>
            </div>

            <p class="feedback-copy summary-copy">
              ${escapeHtml(choice.feedback)}
            </p>
          </section>

          <div class="feedback-card-grid">
            <section class="premium-card detail-card">
              <div class="panel-label">ΣΗΜΑΔΙΑ ΚΙΝΔΥΝΟΥ</div>
              <ul class="feedback-flags-list">
                ${flags}
              </ul>
            </section>

            <section class="premium-card detail-card safe-card">
              <div class="panel-label">ΑΣΦΑΛΕΣΤΕΡΗ ΕΝΕΡΓΕΙΑ</div>
              <p class="safe-copy">
                ${escapeHtml(item.safe_action)}
              </p>
            </section>
          </div>

          <div class="feedback-actions-row">
            <button
              id="nextBtn"
              class="primary-btn"
              type="button"
            >
              ${buttonLabel}
            </button>
          </div>
        </section>
      </article>
    `;

    resetMobileScroll();

    document
      .getElementById('nextBtn')
      .addEventListener('click', () => {
        if (currentIndex < data.items.length - 1) {
          currentIndex += 1;
          renderItem();
        } else {
          renderResult();
        }
      });

    resetIdleTimers();
  }


  function renderResult() {
    console.log("SMS FINAL hadUnsafeChoice:", hadUnsafeChoice);

    const lesson = data.educational_message;

    const victimBanner = hadUnsafeChoice
      ? '<div class="result-badge victim-alert">☹️ ΔΥΣΤΥΧΩΣ ΕΠΕΣΕΣ ΘΥΜΑ ΑΠΑΤΗΣ</div>'
      : '<div class="result-kicker">ΟΛΟΚΛΗΡΩΣΗ CHALLENGE</div>';

    screen.innerHTML = `
      <article class="result-card sms-final-card">

        ${victimBanner}

        ${renderReactionStatus(score, hadUnsafeChoice)}

        <p class="result-copy">
          Το σημαντικό δεν είναι να μπορείς πάντα να
          «μαντεύεις» αν ένα μήνυμα είναι ψεύτικο.
          Το σημαντικό είναι να μην αφήνεις το ίδιο το
          μήνυμα να αποφασίζει από ποιο κανάλι θα
          επιβεβαιώσεις την πληροφορία.
        </p>


        <div class="lesson-grid">

          <section>
            <div>1</div>
            <h2>ΣΤΑΜΑΤΑ</h2>
            <p>${escapeHtml(lesson.stop)}</p>
          </section>

          <section>
            <div>2</div>
            <h2>ΕΛΕΓΞΕ</h2>
            <p>${escapeHtml(lesson.check)}</p>
          </section>

          <section>
            <div>3</div>
            <h2>ΕΠΙΒΕΒΑΙΩΣΕ</h2>
            <p>${escapeHtml(lesson.verify)}</p>
          </section>

        </div>


        <div class="result-actions">

          <button
            id="retryBtn"
            class="primary-btn"
            type="button"
          >
            ΔΟΚΙΜΑΣΕ ΞΑΝΑ
          </button>

          <button
            id="resultHomeBtn"
            class="secondary-btn"
            type="button"
          >
            ΑΡΧΙΚΗ FRAUD LAB
          </button>

        </div>

      </article>
    `;

    resetMobileScroll();

    document
      .getElementById('retryBtn')
      .addEventListener('click', showIntro);


    document
      .getElementById('resultHomeBtn')
      .addEventListener('click', () => {
        window.location.href = '/';
      });


    resetIdleTimers();
  }


  function toggleAssist() {
    assisted = !assisted;

    document.body.classList.toggle(
      'assisted',
      assisted
    );

    assistBtn.setAttribute(
      'aria-pressed',
      String(assisted)
    );
  }


  function renderFatal() {
    screen.innerHTML = `
      <section class="fatal-card">

        <h1>
          Το station χρειάζεται επανεκκίνηση
        </h1>

        <p>
          Δεν φορτώθηκαν τα τοπικά δεδομένα
          του SMS Challenge.
        </p>

        <button
          class="primary-btn"
          onclick="window.location.reload()"
        >
          ΕΠΑΝΕΚΚΙΝΗΣΗ
        </button>

      </section>
    `;

    resetMobileScroll();
  }


  async function init() {
    try {
      const response =
        await fetch(API_URL, {
          cache: 'no-store'
        });

      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}`
        );
      }

      data = await response.json();

      if (
        !Array.isArray(data.items) ||
        data.items.length === 0
      ) {
        throw new Error(
          'No SMS challenge items'
        );
      }

      showIntro();

    } catch (error) {
      console.error(error);
      renderFatal();
    }
  }


  homeBtn.addEventListener(
    'click',
    () => {
      window.location.href = '/';
    }
  );


  assistBtn.addEventListener(
    'click',
    toggleAssist
  );


  continueBtn.addEventListener(
    'click',
    () => {
      timeoutModal.hidden = true;
      resetIdleTimers();
    }
  );


  closeSimulationBtn.addEventListener(
    'click',
    () => {
      closeSimulation();
    }
  );


  window.addEventListener('message', event => {
    if (event.source !== simulationFrame.contentWindow) {
      return;
    }

    const data = event.data;

    if (!data || typeof data !== 'object') {
      return;
    }

    if (data.type === 'fraudlab:sms-sim-height') {
      const reportedHeight = Number(data.height);

      if (!Number.isFinite(reportedHeight) || reportedHeight < 1) {
        return;
      }

      const viewportHeight = Math.max(1, simulationViewport.clientHeight);
      const safeHeight = Math.min(5000, Math.ceil(reportedHeight));
      simulationFrame.style.height = `${Math.max(viewportHeight, safeHeight)}px`;
      return;
    }

    if (data.type === 'fraudlab:sms-sim-scroll-top') {
      simulationViewport.scrollTo({ top: 0, behavior: 'smooth' });
    }
  });


  [
    'pointerdown',
    'touchstart'
  ].forEach(eventName => {

    document.addEventListener(
      eventName,
      registerActivity,
      { passive: true }
    );

  });


  document.addEventListener(
    'keydown',
    event => {

      if (!simulationOverlay.hidden) {
        if (event.key === 'Escape') {
          closeSimulation();
        }

        return;
      }

      registerActivity();

      if (!timeoutModal.hidden) {
        if (
          event.key === 'Enter' ||
          event.key === ' '
        ) {
          continueBtn.click();
        }

        return;
      }


      if (
        ['1', '2', '3'].includes(event.key)
      ) {

        const button =
          document.querySelector(
            `[data-choice-index="${
              Number(event.key) - 1
            }"]`
          );

        if (button && !button.disabled) {
          button.click();
        }

      } else if (
        event.key.toLowerCase() === 'h'
      ) {

        window.location.href = '/';

      }

    }
  );


  init();

})();
