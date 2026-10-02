(() => {
  'use strict';

  const screen = document.getElementById('screen');
  const homeBtn = document.getElementById('homeBtn');
  const assistBtn = document.getElementById('assistBtn');
  const timeoutModal = document.getElementById('timeoutModal');
  const continueBtn = document.getElementById('continueBtn');

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
    resetIdleTimers();
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

        <div class="eyebrow">QR & ΙΣΤΟΣΕΛΙΔΑ</div>
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

    const fakeForm = item.fake_form || {
      field_1_label: 'Ονοματεπώνυμο',
      field_1_value: '••••••••••',
      field_2_label: 'Στοιχεία πληρωμής',
      field_2_value: '•••• •••• •••• ••••',
      button_text: item.cta || 'ΣΥΝΕΧΕΙΑ'
    };

    const choices = item.choices.map((choice, i) => `
      <button class="choice-btn" data-choice="${i}">
        <span>${i + 1}</span>
        ${escapeHtml(choice.label)}
      </button>
    `).join('');

    screen.innerHTML = `
      <article class="challenge-layout">

        <section class="left-panel">

          <div class="progress">
            <span>ΣΕΝΑΡΙΟ ${currentIndex + 1} ΑΠΟ ${data.items.length}</span>
            <span>SCORE ${score}/100</span>
          </div>

          <div class="poster-card">
            <div class="poster-kicker">${escapeHtml(item.category)}</div>
            <h2>${escapeHtml(item.poster_title)}</h2>
            <p>${escapeHtml(item.poster_text)}</p>

            <div class="qr-placeholder" aria-label="Εκπαιδευτικό QR">
              ${item.qr_image ? `<img class="scenario-qr-image" src="${escapeHtml(item.qr_image)}" alt="QR code σεναρίου">` : `<div class="qr-grid"></div><small>DEMO QR</small>`}
            </div>
          </div>

          <div class="choice-area">
            <h1>Τι θα έκανες;</h1>
            <div class="choice-grid">${choices}</div>
          </div>

        </section>


        <section class="browser-card">

          <div class="browser-top">
            <div class="browser-dots">● ● ●</div>
            <div class="address-bar">
              ${escapeHtml(item.url)}
            </div>
          </div>

          <div class="fake-site">

            <div class="site-brand">
              ${escapeHtml(item.site_name)}
            </div>

            <h2>
              ${escapeHtml(item.headline)}
            </h2>

            <p>
              ${escapeHtml(item.body)}
            </p>

            ${renderFakeForm(fakeForm)}

            <div class="simulation-warning">
              ΕΚΠΑΙΔΕΥΤΙΚΗ ΠΡΟΣΟΜΟΙΩΣΗ ·
              ΔΕΝ ΚΑΤΑΧΩΡΟΥΝΤΑΙ ΣΤΟΙΧΕΙΑ
            </div>

          </div>

        </section>

      </article>
    `;

    document.querySelectorAll('[data-choice]').forEach(button => {
      button.addEventListener('click', () => {
        chooseAnswer(Number(button.dataset.choice));
      });
    });

    setupFakeFormInteraction(fakeForm);
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
        <div class="eyebrow">QR & ΙΣΤΟΣΕΛΙΔΑ</div>
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
          Το QR code δεν είναι ταυτότητα.
          Είναι απλώς ένας γρήγορος τρόπος να ανοίξει ένας προορισμός.
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

  ['pointerdown', 'touchstart'].forEach(eventName => {
    document.addEventListener(eventName, registerActivity, { passive: true });
  });

  document.addEventListener('keydown', registerActivity);


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
