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

  let data = null;
  let currentIndex = 0;
  let score = 0;
  let hadUnsafeChoice = false;
  let answered = false;
  let assisted = false;

  let warningTimer = null;
  let resetTimer = null;

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
    resetIdleTimers();
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
          Δεν υπάρχουν πραγματικοί σύνδεσμοι,
          λογαριασμοί ή προσωπικά δεδομένα.
        </div>

        <button id="startBtn" class="primary-btn" type="button">
          ΕΝΑΡΞΗ CHALLENGE
        </button>

      </article>
    `;

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


    const linkBlock = item.link_text
      ? `
        <div class="fake-link">
          ${escapeHtml(item.link_text)}
        </div>

        <div class="simulation-note">
          ${escapeHtml(item.link_warning)}
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


    document
      .querySelectorAll('[data-choice-index]')
      .forEach(button => {
        button.addEventListener('click', () => {
          chooseAnswer(
            Number(button.dataset.choiceIndex)
          );
        });
      });

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

        <h1>
          ${reactionStatus(score, hadUnsafeChoice)}
        </h1>

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
