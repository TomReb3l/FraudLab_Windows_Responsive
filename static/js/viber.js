(() => {
  'use strict';

  const API_URL = '/api/viber-scenario';
  const IDLE_WARNING_MS = 65000;
  const IDLE_RESET_MS = 75000;
  const screen = document.getElementById('viberScreen');
  const modal = document.getElementById('timeoutModal');
  const continueBtn = document.getElementById('continueBtn');
  const assistBtn = document.getElementById('assistBtn');
  const homeBtn = document.getElementById('homeBtn');
  const sound = new Audio('/static/audio/ui/incoming_sms.mp3');
  sound.preload = 'auto';
  sound.volume = 0.55;

  let scenario = null;
  let variant = 'sms';
  let currentId = null;
  let history = [];
  let finished = false;
  let assisted = false;
  let warningTimer = null;
  let resetTimer = null;

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;').replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;').replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function idleToHome() {
    clearTimeout(warningTimer);
    clearTimeout(resetTimer);
    window.location.replace('/');
  }

  function activity() {
    clearTimeout(warningTimer);
    clearTimeout(resetTimer);
    modal.hidden = true;
    warningTimer = window.setTimeout(() => {
      modal.hidden = false;
      continueBtn.focus();
    }, IDLE_WARNING_MS);
    resetTimer = window.setTimeout(idleToHome, IDLE_RESET_MS);
  }

  function notify() {
    try {
      sound.pause();
      sound.currentTime = 0;
      const result = sound.play();
      if (result && typeof result.catch === 'function') result.catch(() => {});
    } catch (_) { /* Browser may block audio before user gesture. */ }
  }

  function displayText(item) {
    if (typeof item.text === 'string') return item.text;
    if (item.text_by_variant) return item.text_by_variant[variant] || '';
    return '';
  }

  function enterNode(id) {
    // Automatically traverse informational nodes, retaining their transcript.
    const visited = new Set();
    while (id) {
      if (visited.has(id) || visited.size > 20) throw Error('Μη έγκυρη διαδρομή σεναρίου.');
      visited.add(id);
      const node = scenario.nodes[id];
      if (!node) throw Error('Άγνωστος κόμβος σεναρίου.');
      currentId = id;
      const messages = node.messages_by_variant ? node.messages_by_variant[variant] : node.messages;
      if (messages) {
        for (const message of messages) history.push({ kind: 'message', speaker: message.speaker, text: message.text });
      }
      if (node.event) {
        history.push({ kind: 'event', event: node.event });
        notify();
      }
      if (node.outcome || Array.isArray(node.choices)) {
        finished = Boolean(node.outcome);
        render();
        return;
      }
      id = node.next_by_variant ? node.next_by_variant[variant] : node.next_node;
    }
    throw Error('Ο κόμβος δεν έχει έγκυρη συνέχεια.');
  }

  function choose(id) {
    if (finished || !scenario) return;
    const node = scenario.nodes[currentId];
    const choice = node.choices.find(option => option.id === id);
    if (!choice) return;
    history.push({ kind: 'message', speaker: 'visitor', text: displayText(choice) });
    try { enterNode(choice.next_node); }
    catch (error) { renderError(error); }
    activity();
  }

  function eventHtml(event) {
    const flash = event.kind === 'flash_call';
    return `<div class="viber-event ${flash ? 'viber-event--call' : ''}" role="status">
      <div class="viber-event-label">${escapeHtml(event.label)}</div>
      <div class="viber-event-title">${escapeHtml(event.title)}</div>
      <div class="viber-event-value">${escapeHtml(event.value)}</div>
      <div class="viber-event-hint">${escapeHtml(event.hint)}</div>
    </div>`;
  }

  function transcriptHtml() {
    return history.map(item => {
      if (item.kind === 'event') return `<div class="viber-event-row">${eventHtml(item.event)}</div>`;
      const self = item.speaker === 'visitor';
      return `<div class="viber-bubble-row ${self ? 'viber-bubble-row--self' : ''}">
        <div class="viber-bubble ${self ? 'viber-bubble--self' : ''}">${escapeHtml(item.text)}</div>
      </div>`;
    }).join('');
  }

  function shieldHtml(outcome) {
    const safe = outcome !== 'danger';
    const mark = safe
      ? '<path d="M18 37.5 27 46l19-22 5 4.5L27.5 56 13 42.5 18 37.5Z"/>'
      : '<path d="M28.5 18h7L34.4 43h-4.8L28.5 18Zm.2 31h6.6v6.6h-6.6V49Z"/>';
    return `<span class="viber-result-shield viber-result-shield--${escapeHtml(outcome)}" aria-hidden="true">
      <svg viewBox="0 0 64 72" focusable="false"><path class="viber-shield-shape" d="M32 2 56 11v20c0 17.8-10.4 31.5-24 39C18.4 62.5 8 48.8 8 31V11L32 2Z"/>${mark}</svg>
    </span>`;
  }

  function resultHtml(outcome) {
    const info = scenario.endings[outcome];
    return `<div class="viber-result viber-result--${escapeHtml(outcome)}">
      <div class="viber-result-header">
        ${shieldHtml(outcome)}
        <h1>${escapeHtml(info.title)}</h1>
        <p>${escapeHtml(info.subtitle)}</p>
      </div>
      <div class="viber-result-sections">${info.sections.map(section =>
        `<section class="viber-result-section"><h2>${escapeHtml(section.title)}</h2>
        <p>${escapeHtml(section.by_variant ? section.by_variant[variant] : section.text)}</p></section>`
      ).join('')}</div>
      <p class="viber-result-motto">${escapeHtml(info.motto)}</p>
      <div class="viber-result-actions">
        <button type="button" class="viber-primary" data-action="restart">ΞΑΝΑΔΟΚΙΜΑΣΕ</button>
        <button type="button" class="viber-secondary" data-action="alternate">ΔΟΚΙΜΑΣΕ ΤΗΝ ΑΛΛΗ ΕΚΔΟΧΗ</button>
        <button type="button" class="viber-secondary" data-action="home">ΑΡΧΙΚΗ</button>
      </div>
      <p class="viber-result-footnote">Εκπαιδευτική αξιολόγηση της επιλογής σου — δεν πραγματοποιήθηκε πραγματική κλήση ή ενεργοποίηση. <span>${escapeHtml(scenario.simulation_notice)}</span></p>
    </div>`;
  }

  function render() {
    const node = scenario.nodes[currentId];
    if (node.outcome) {
      screen.innerHTML = resultHtml(node.outcome);
      screen.scrollTop = 0;
      return;
    }
    screen.innerHTML = `<div class="viber-experience">
      <div class="viber-chat" aria-label="Εικονική συνομιλία Viber">
        <header class="viber-chat-header">
          <span class="viber-avatar" aria-hidden="true">Γ</span>
          <span><strong>${escapeHtml(scenario.fictional_contact)}</strong><small>Viber · Αποθηκευμένη επαφή</small></span>
          <span class="viber-chat-header-icons" aria-hidden="true">☎ &nbsp; ▣</span>
        </header>
        <div id="viberTranscript" class="viber-transcript" role="log" aria-live="off">${transcriptHtml()}</div>
        <div class="viber-chat-footer">Φανταστική συνομιλία · Δεν αποστέλλονται πραγματικά μηνύματα.</div>
      </div>
      <aside class="viber-decision" aria-label="Επιλογές απάντησης">
        <div class="viber-decision-kicker">Η ΔΙΚΗ ΣΟΥ ΑΠΟΦΑΣΗ</div>
        <h1>${escapeHtml(node.prompt || 'Τι απαντάς;')}</h1>
        <div class="viber-choices">${node.choices.map(choice =>
          `<button class="viber-choice" type="button" data-choice="${escapeHtml(choice.id)}"><b>${escapeHtml(choice.id)}.</b><span>${escapeHtml(displayText(choice))}</span></button>`
        ).join('')}</div>
        <p class="viber-decision-footnote">Διάλεξε την αντίδρασή σου. Η συνομιλία αλλάζει σύμφωνα με την απάντηση.</p>
      </aside>
    </div>`;
    const transcript = document.getElementById('viberTranscript');
    if (transcript) transcript.scrollTop = transcript.scrollHeight;
  }

  function showIntro() {
    currentId = null;
    finished = false;
    history = [];
    const variantLabel = variant === 'sms' ? 'SMS ενεργοποίησης' : 'Flash Call';
    screen.innerHTML = `<section class="viber-intro">
      <div class="viber-intro-kicker">STATION 04 · ΔΙΑΔΡΑΣΤΙΚΗ ΕΜΠΕΙΡΙΑ</div>
      <h1>Viber Fraud</h1>
      <h2>Μιλάς πραγματικά με τον φίλο σου;</h2>
      <p>Λαμβάνεις μήνυμα από μια γνωστή, αποθηκευμένη επαφή. Πώς θα αντιδράσεις όταν σου ζητήσει μια μικρή εξυπηρέτηση;</p>
      <div class="viber-intro-mode">Εκδοχή προσομοίωσης: <strong>${escapeHtml(variantLabel)}</strong></div>
      <button type="button" class="viber-primary viber-start" data-action="start">ΕΝΑΡΞΗ ΕΜΠΕΙΡΙΑΣ →</button>
      <p class="viber-intro-disclaimer">Όλα τα πρόσωπα, οι αριθμοί και τα μηνύματα είναι φανταστικά. Δεν συλλέγονται προσωπικά στοιχεία.</p>
    </section>`;
  }

  function restart(nextVariant) {
    if (nextVariant) variant = nextVariant;
    activity();
    showIntro();
  }

  function renderError(error) {
    console.error('Viber scenario error:', error);
    screen.innerHTML = `<div class="viber-error"><h1>Η προσομοίωση δεν είναι διαθέσιμη.</h1>
      <p>Παρουσιάστηκε πρόβλημα στη φόρτωση του τοπικού σεναρίου. Μπορείς να επιστρέψεις στην αρχική οθόνη.</p>
      <button type="button" class="viber-primary" data-action="home">ΑΡΧΙΚΗ</button></div>`;
  }

  screen.addEventListener('click', event => {
    const btn = event.target.closest('button');
    if (!btn) return;
    if (btn.dataset.choice) { choose(btn.dataset.choice); return; }
    switch (btn.dataset.action) {
      case 'start':
        history = [];
        finished = false;
        try { enterNode(scenario.start_node); } catch (error) { renderError(error); }
        break;
      case 'restart': restart(); break;
      case 'alternate': restart(variant === 'sms' ? 'flash_call' : 'sms'); break;
      case 'home': window.location.href = '/'; break;
      default: break;
    }
    activity();
  });

  assistBtn.addEventListener('click', () => {
    assisted = !assisted;
    document.body.classList.toggle('assisted', assisted);
    assistBtn.setAttribute('aria-pressed', String(assisted));
    activity();
  });
  homeBtn.addEventListener('click', () => { window.location.href = '/'; });
  continueBtn.addEventListener('click', () => activity());
  ['pointerdown', 'touchstart', 'wheel'].forEach(name => document.addEventListener(name, activity, { passive: true }));
  document.addEventListener('keydown', event => {
    activity();
    if (!modal.hidden && ['Enter', ' '].includes(event.key)) { event.preventDefault(); continueBtn.click(); return; }
    if (event.key.toLowerCase() === 'h' && !event.altKey && !event.ctrlKey) {
      window.location.href = '/';
      return;
    }
    if (currentId && scenario && !finished && /^[1-3]$/.test(event.key)) {
      const choice = scenario.nodes[currentId].choices[Number(event.key) - 1];
      if (choice) choose(choice.id);
    }
  });

  async function init() {
    activity();
    try {
      const response = await fetch(API_URL, { cache: 'no-store', credentials: 'same-origin' });
      if (!response.ok) throw Error(`HTTP ${response.status}`);
      scenario = await response.json();
      if (!scenario || !scenario.nodes || !scenario.nodes[scenario.start_node]) throw Error('Invalid scenario data');
      variant = scenario.default_variant || 'sms';
      showIntro();
    } catch (error) { renderError(error); }
  }
  init();
})();
