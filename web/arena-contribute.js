const CONTRIBUTION_REPOSITORY = 'https://github.com/Doldrums/arena';

export function buildAccessRequest({name = '', email = '', affiliation = '', system = '', research = ''} = {}, kind = 'system') {
  return {
    subject: `Empira research run access${system.trim() ? ` · ${system.trim()}` : ''}`,
    body: [
      'Hello Empira team,', '', 'I would like to request access for a research run.', '',
      `Name: ${name.trim()}`, `Reply email: ${email.trim()}`, `Affiliation: ${affiliation.trim() || 'Independent'}`,
      `Contribution: ${kind === 'task' ? 'Task' : 'System'}`, `System / release: ${system.trim() || 'To discuss'}`,
      '', 'Research question, tasks and expected run budget:', research.trim(), '',
      'Please let me know the next steps for worker access and release registration.',
    ].join('\n'),
  };
}

export function initArenaContributions({doc = document, accessEmail = doc.body.dataset.arenaAccessEmail || '', compose} = {}) {
  if (doc.getElementById('arena-contribution-dialog')) return null;
  const win = doc.defaultView;
  const dialog = doc.createElement('dialog');
  dialog.id = 'arena-contribution-dialog';
  dialog.className = 'arena-contribution-dialog';
  dialog.setAttribute('aria-labelledby', 'arena-contribution-title');
  dialog.setAttribute('aria-describedby', 'arena-contribution-description');
  dialog.innerHTML = `
    <div class="contribution-shell">
      <header class="contribution-header">
        <span class="contribution-eyebrow">Empira · Research community</span>
        <button type="button" class="contribution-close" aria-label="Close contribution dialog"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg></button>
        <h2 id="arena-contribution-title" tabindex="-1"></h2>
        <p id="arena-contribution-description"></p>
      </header>
      <div class="contribution-overview">
        <ol class="contribution-steps"></ol>
        <div class="contribution-next">
          <p class="contribution-review-note">Registration is reviewed separately from experiment access.</p>
          <a class="contribution-primary contribution-pr" target="_blank" rel="noopener noreferrer">Open a pull request <span aria-hidden="true">↗</span></a>
        </div>
        <section class="contribution-access-card" aria-labelledby="contribution-access-heading">
          <span class="contribution-access-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="m8 5 10 7-10 7z"/></svg></span>
          <div><h3 id="contribution-access-heading">Run access requires a key</h3><p>Request a key from the research team. Include your system, tasks and compute budget so we can arrange the experiment.</p><button class="contribution-access-link" type="button">Request run access <span aria-hidden="true">↗</span></button></div>
        </section>
      </div>
      <div class="contribution-request" hidden>
        <button class="contribution-back" type="button"><span aria-hidden="true">←</span> Back to contribution steps</button>
        <form class="contribution-access-form">
          <div class="contribution-form-pair">
            <label>Your name<input name="name" autocomplete="name" required maxlength="120" placeholder="Name"></label>
            <label>Research group<input name="affiliation" autocomplete="organization" maxlength="160" placeholder="Group or independent"></label>
          </div>
          <label>Reply email<input name="email" type="email" autocomplete="email" required maxlength="180" placeholder="you@institution.edu"></label>
          <label>System / release <span class="contribution-optional">optional</span><input name="system" maxlength="160" placeholder="e.g. sciel 1.0.4"></label>
          <label>What would you like to study?<textarea name="research" rows="4" required maxlength="3000" placeholder="Research question, tasks, model or hardware needs, and an approximate run budget."></textarea></label>
          <p class="contribution-email-note">Opens an email draft to <span class="contribution-email-recipient"></span>. Access keys are arranged with the team; this form does not launch a run.</p>
          <button class="contribution-primary" type="submit">Open email draft <span aria-hidden="true">↗</span></button>
          <p class="contribution-form-status" role="status" aria-live="polite"></p>
        </form>
      </div>
    </div>`;
  doc.body.append(dialog);
  const $ = selector => dialog.querySelector(selector);
  const title = $('#arena-contribution-title');
  const description = $('#arena-contribution-description');
  const form = $('.contribution-access-form');
  const recipient = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(accessEmail) ? accessEmail : '';
  $('.contribution-email-recipient').textContent = recipient || 'the research team';
  let kind = 'task', opener = null;
  const content = {
    task: {
      title: 'Submit a task',
      description: 'A scientific question, a clear evaluation contract, and the source to trace it back to.',
      steps: [
        ['Prepare the task', 'Describe the problem and why it matters. Include the candidate interface, evaluator, metric and original paper or source.'],
        ['Open a GitHub pull request', 'Add the task definition and pinned source references. State what is ready to evaluate and what still needs implementation.'],
        ['Review together', 'We check the task, evaluation protocol and provenance with you before it enters the catalog.'],
      ],
    },
    system: {
      title: 'Submit a system',
      description: 'Register a research system and an identifiable release. Keep its implementation in your private worker environment.',
      steps: [
        ['Prepare the private implementation', 'Use a private repository or container image for the worker. Keep implementation access and provider credentials out of the public submission.'],
        ['Register an immutable release', 'Arrange private CI registration with the team. Pin the source commit or image digest before submitting a public version.'],
        ['Open the public pull request', 'Identify the system and release, for example sciel 1.0.4. Share private worker details directly with the team.'],
        ['Review the integration', 'Agree on task interfaces, native evaluation and resource requirements. Registering a system and requesting a run are separate steps.'],
      ],
    },
  };
  function overview() {
    const copy = content[kind];
    title.textContent = copy.title;
    description.textContent = copy.description;
    $('.contribution-overview').hidden = false;
    $('.contribution-request').hidden = true;
    const list = $('.contribution-steps');
    list.replaceChildren();
    copy.steps.forEach(([heading, text], index) => {
      const item = doc.createElement('li');
      const number = doc.createElement('span');
      number.className = 'contribution-step-number'; number.setAttribute('aria-hidden', 'true');
      number.textContent = String(index + 1).padStart(2, '0');
      const body = doc.createElement('div');
      const h3 = doc.createElement('h3'); h3.textContent = heading;
      const paragraph = doc.createElement('p'); paragraph.textContent = text;
      body.append(h3, paragraph); item.append(number, body); list.append(item);
    });
    $('.contribution-pr').href = `${CONTRIBUTION_REPOSITORY}/compare?expand=1`;
    $('.contribution-review-note').textContent = kind === 'system'
      ? 'Private worker registration is being prepared. Contact the team before submitting a private release.'
      : 'A task contribution does not require launching an experiment.';
  }
  function close() { dialog.close(); }
  function open(nextKind, trigger) {
    kind = nextKind === 'system' ? 'system' : 'task'; opener = trigger;
    overview();
    if (!dialog.open) dialog.showModal();
    doc.body.classList.add('arena-contribution-open');
    title.focus();
  }
  function onTrigger(event) {
    const trigger = event.target.closest('[data-arena-contribution]');
    if (!trigger) return;
    event.preventDefault(); open(trigger.dataset.arenaContribution, trigger);
  }
  doc.addEventListener('click', onTrigger);
  $('.contribution-close').addEventListener('click', close);
  dialog.addEventListener('close', () => {
    doc.body.classList.remove('arena-contribution-open');
    if (opener?.isConnected) opener.focus();
  });
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) close();
  });
  $('.contribution-access-link').addEventListener('click', () => {
    title.textContent = 'Request run access';
    description.textContent = 'Tell us what you want to investigate. We’ll coordinate access and the execution setup with you.';
    $('.contribution-overview').hidden = true;
    $('.contribution-request').hidden = false;
    $('.contribution-form-status').textContent = '';
    form.elements.name.focus();
  });
  $('.contribution-back').addEventListener('click', () => { overview(); $('.contribution-access-link').focus(); });
  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    if (!recipient) {
      $('.contribution-form-status').textContent = 'The contact address is not configured yet. Please use the repository to contact the team.';
      return;
    }
    const values = Object.fromEntries(new win.FormData(form));
    const draft = buildAccessRequest(values, kind);
    const mailto = `mailto:${recipient}?subject=${encodeURIComponent(draft.subject)}&body=${encodeURIComponent(draft.body)}`;
    $('.contribution-form-status').textContent = 'Draft prepared. Review and send it from your email app.';
    if (compose) compose(mailto); else win.location.href = mailto;
  });
  return {open, dialog, destroy() { doc.removeEventListener('click', onTrigger); doc.body.classList.remove('arena-contribution-open'); dialog.remove(); }};
}

if (typeof document !== 'undefined' && document.body?.dataset.arenaApp === 'true') initArenaContributions();
