import {
  REPOSITORY,
  adapterLabel,
  linkedNativeAdapters,
  participantKind,
  safeExternalURL,
} from './arena-model.js';
export function createArenaParticipantDetail(context) {
  const { $ } = context;
  const link = (...args) => context.link(...args);
  const route = (...args) => context.route(...args);
  const empty = (...args) => context.empty(...args);
  const element = (...args) => context.element(...args);
  const badge = (...args) => context.badge(...args);
  const fact = (...args) => context.fact(...args);
  const section = (...args) => context.section(...args);
  const externalLinks = (...args) => context.externalLinks(...args);
  const recordDetails = (...args) => context.recordDetails(...args);
  function participantDetail(participant) {
    const holder = $('arena-detail');
    holder.replaceChildren();
    holder.append(
      link('← Back to participants', route({ participant: null }), 'inline-link', true),
    );
    if (!participant) {
      empty(holder, 'Participant not found', 'This participant is not in the current registry.');
      return;
    }
    const heading = element('div', 'arena-detail-top');
    const title = element('div');
    title.append(
      element('h2', 'arena-detail-title', participant.name || participant.id),
      element('span', 'arena-task-id', participant.id),
    );
    heading.append(title, badge(participantKind(participant)));
    holder.append(
      heading,
      element(
        'p',
        'arena-detail-description',
        participant.description || 'No description supplied.',
      ),
    );
    participantAttribution(holder, participant, true);
    participantPapers(holder, participant, true);
    const facts = element('dl', 'arena-detail-facts');
    if (participant.search_family?.label)
      fact(facts, 'Method family', participant.search_family.label);
    fact(facts, 'Arena integration', adapterLabel(participant));
    const adapters = linkedNativeAdapters(participant);
    if (participant.adapter_status === 'native_cli' || adapters.length)
      fact(facts, 'Validation', 'Source and fixture checks · native environment to be verified');
    if (participant.repository?.commit) {
      fact(facts, 'Source revision', participant.repository.commit);
      for (const [label, key] of [
        ['Native execution', 'native_run'],
        ['Canonical evaluation', 'canonical_evaluation'],
        ['Pause', 'pause'],
        ['Resume', 'resume'],
      ]) {
        const value = participant.capabilities?.[key];
        fact(
          facts,
          label,
          value === true
            ? 'Available'
            : value === false
              ? 'Integration pending'
              : 'To be specified',
        );
      }
    }
    holder.append(facts);
    if (adapters.length) {
      const integration = section(holder, 'Local native adapters');
      integration.append(
        element(
          'p',
          '',
          'These adapters use the implementation’s native evaluation. They do not establish canonical task compatibility or a verified runtime.',
        ),
      );
      for (const adapter of adapters) {
        const details = element('dl', 'arena-detail-facts');
        fact(details, 'Engine', `${adapter.name} (${adapter.engine})`);
        fact(details, 'Profiles', adapter.profiles.join(', '));
        fact(details, 'Pinned source', adapter.repository.commit);
        integration.append(details);
        externalLinks(integration, [
          [
            `${adapter.name} pinned source`,
            `${adapter.repository.url}/tree/${adapter.repository.commit}`,
          ],
        ]);
      }
    }
    externalLinks(
      holder,
      participantSourceLinks(participant).concat([
        ['Propose an integration', `${REPOSITORY}/compare?expand=1`],
      ]),
    );
    if (participant.provenance?.filename) {
      const provenance = section(holder, 'Research provenance');
      provenance.append(
        element(
          'p',
          '',
          `Curated from ${participant.provenance.filename}${participant.provenance.line_start ? `, lines ${participant.provenance.line_start}–${participant.provenance.line_end}` : ''}. Paper and source links identify the original research.`,
        ),
      );
    }
    recordDetails(holder, participant);
  }

  function participantSourceLinks(participant) {
    const refs = (participant.code_links || []).map((item) => [
      item.label || 'Research source',
      item.url,
    ]);
    if (participant.repository?.url && !refs.some(([, url]) => url === participant.repository.url))
      refs.unshift(['Code', participant.repository.url]);
    return refs;
  }

  function participantAttribution(container, participant, detailed = false) {
    const attribution = participant.attribution;
    if (!attribution?.display) return;
    const byline = element('div', `arena-participant-byline${detailed ? ' is-detail' : ''}`);
    byline.append(element('span', '', 'by '));
    const source = safeExternalURL(attribution.source_url);
    const name = source
      ? link(attribution.display, source, 'arena-attribution-link')
      : element('span', '', attribution.display);
    name.title = `${attribution.source_locator || 'Research attribution'}${attribution.evidence_note ? ` · ${attribution.evidence_note}` : ''}`;
    byline.append(name);
    container.append(byline);
    if (detailed) {
      const context = element('p', 'arena-attribution-context');
      context.append(
        element(
          'span',
          '',
          (attribution.kind === 'authors' ? attribution.authors : attribution.organizations)?.join(
            ' · ',
          ) || attribution.display,
        ),
      );
      if (attribution.evidence_note) context.append(element('span', '', attribution.evidence_note));
      container.append(context);
    }
  }

  function participantPapers(container, participant, detailed = false) {
    if (!participant.papers?.length) return;
    const list = element('div', `arena-participant-papers${detailed ? ' is-detail' : ''}`);
    for (const paper of participant.papers) {
      const row = element('div', 'arena-paper-citation');
      const title = safeExternalURL(paper.url)
        ? link(paper.title || paper.id, paper.url, 'arena-paper-title')
        : element('span', 'arena-paper-title', paper.title || paper.id);
      const metadata = [paper.year, paper.venue].filter(Boolean).join(' · ');
      row.append(
        element(
          'span',
          'arena-paper-label',
          paper.kind === 'technical_report' ? 'Report' : 'Paper',
        ),
        title,
      );
      if (metadata) row.append(element('span', 'arena-paper-meta', metadata));
      list.append(row);
    }
    container.append(list);
  }
  return { participantDetail, participantSourceLinks, participantAttribution, participantPapers };
}
