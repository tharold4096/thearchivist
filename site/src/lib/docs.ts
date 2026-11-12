// Every readable document on the site: writeups (front matter), host notes,
// and the responder journal. Also the open follow-ups pulled out of them.
import path from 'node:path';
import { parse } from 'yaml';
import { hosts, hostBySlug, slugForCheckmkName } from './inventory';
import { plainText, registerRoute, renderInline, renderMarkdown, type Heading } from './markdown';
import { readTracked, tracked } from './repo';

export type DocType = 'build' | 'change' | 'update' | 'incident' | 'reference' | 'responder' | 'note';

export interface Doc {
  /** repo path of the source file */
  source: string;
  /** site path, no base, no leading slash: "writeups/builds/2026-…" */
  route: string;
  title: string;
  date: string;
  type: DocType;
  status: string;
  hosts: string[];
  tags: string[];
  summary: string;
  verified?: string;
  open: number;
  /** listed on the Writeups page */
  listed: boolean;
  html: string;
  headings: Heading[];
  text: string;
  /** build-series part number, when the file is one of docs/build/NN-*.md */
  part?: number;
}

export interface FollowUp {
  html: string;
  text: string;
}

export interface FollowUpGroup {
  source: string;
  route: string;
  title: string;
  date: string;
  hosts: string[];
  origin: 'writeup' | 'host';
  items: FollowUp[];
}

export const TYPE_LABEL: Record<DocType, string> = {
  build: 'Build',
  change: 'Change',
  update: 'Update',
  incident: 'Incident',
  reference: 'Reference',
  responder: 'Responder',
  note: 'Note',
};

function splitFrontMatter(raw: string): { data: Record<string, any> | null; body: string } {
  const m = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/.exec(raw);
  if (!m) return { data: null, body: raw };
  return { data: parse(m[1]) ?? {}, body: raw.slice(m[0].length) };
}

/** Drop the leading "# Title" — the page header already prints it. */
function stripTitle(body: string): { title?: string; body: string } {
  const m = /^\s*# (.+)\r?\n/.exec(body);
  if (!m) return { body };
  return { title: m[1].trim(), body: body.slice(m[0].length) };
}

/** "## Section" blocks of a markdown body, keyed by heading text. */
export function sections(body: string): { heading: string; body: string }[] {
  const out: { heading: string; body: string }[] = [];
  let current: { heading: string; lines: string[] } = { heading: '', lines: [] };
  let fence = false;
  for (const line of body.split(/\r?\n/)) {
    if (/^\s*```/.test(line)) fence = !fence;
    const m = !fence && /^## (.+)$/.exec(line);
    if (m) {
      out.push({ heading: current.heading, body: current.lines.join('\n') });
      current = { heading: m[1].trim(), lines: [] };
    } else current.lines.push(line);
  }
  out.push({ heading: current.heading, body: current.lines.join('\n') });
  return out;
}

/** Unchecked "- [ ]" items, with any indented continuation lines. */
function uncheckedItems(body: string): string[] {
  const items: string[] = [];
  const lines = body.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const m = /^(\s*)[-*] \[ \] (.*)$/.exec(lines[i]);
    if (!m) continue;
    const indent = m[1].length;
    const parts = [m[2]];
    while (i + 1 < lines.length && /^\s+\S/.test(lines[i + 1]) && lines[i + 1].search(/\S/) > indent && !/^\s*[-*] /.test(lines[i + 1])) {
      parts.push(lines[++i].trim());
    }
    items.push(parts.join(' '));
  }
  return items;
}

const isHostReadme = (p: string) => /^hosts\/[^/]+\/[^/]+\/README\.md$/.test(p);
const hostDirOf = (p: string) => /^(hosts\/[^/]+\/([^/]+))\//.exec(p);

// ---------------------------------------------------------------- routes
// Decide every page's address first, so links between documents resolve.

interface Pending {
  source: string;
  route: string;
  kind: 'writeup' | 'hostnote' | 'journal';
}
const pending: Pending[] = [];

for (const p of tracked) {
  if (!p.endsWith('.md')) continue;
  if (p.startsWith('docs/templates/')) continue;
  if (p.startsWith('docs/')) {
    if (path.posix.basename(p) === 'README.md') continue;
    const route = `writeups/${p.replace(/^docs\//, '').replace(/^writeups\//, '').replace(/\.md$/, '')}`;
    pending.push({ source: p, route, kind: 'writeup' });
  } else if (p.startsWith('journal/responder/')) {
    if (path.posix.basename(p) === 'README.md') continue;
    pending.push({ source: p, route: `journal/${path.posix.basename(p, '.md')}`, kind: 'journal' });
  } else if (p.startsWith('hosts/') && !isHostReadme(p) && p !== 'hosts/README.md') {
    const m = hostDirOf(p);
    if (!m) continue;
    const rest = p.slice(m[1].length + 1).replace(/\.md$/, '').toLowerCase().replace(/[^a-z0-9/]+/g, '-');
    pending.push({ source: p, route: `hosts/${m[2]}/${rest}`, kind: 'hostnote' });
  }
}

for (const p of pending) registerRoute(p.source, p.route);
for (const h of hosts) {
  registerRoute(`${h.dir}/README.md`, `hosts/${h.slug}`);
  registerRoute(h.dir, `hosts/${h.slug}`);
}
// Index pages in the repo map to the matching section of the site.
registerRoute('hosts/README.md', 'hosts');
registerRoute('hosts', 'hosts');
registerRoute('docs/writeups/README.md', 'writeups');
registerRoute('docs/writeups', 'writeups');
registerRoute('docs/writeups/builds', 'writeups/?type=build');
registerRoute('docs/writeups/changes', 'writeups/?type=change');
registerRoute('docs/writeups/updates', 'writeups/?type=update');
registerRoute('docs/writeups/incidents', 'writeups/?type=incident');
registerRoute('docs/overview', 'writeups/?type=reference');
registerRoute('journal/responder/README.md', 'writeups/?type=responder');
registerRoute('journal/responder', 'writeups/?type=responder');

// ---------------------------------------------------------------- documents

function loadWriteup(p: Pending): Doc {
  const { data, body } = splitFrontMatter(readTracked(p.source));
  const stripped = stripTitle(body);
  const fm = data ?? {};
  const rendered = renderMarkdown(stripped.body, p.source);
  const partMatch = /^docs\/build\/(\d{2})-/.exec(p.source);
  const hostMatch = hostDirOf(p.source);
  return {
    source: p.source,
    route: p.route,
    title: String(fm.title ?? stripped.title ?? path.posix.basename(p.source, '.md')),
    date: String(fm.date ?? ''),
    type: (fm.type ?? 'note') as DocType,
    status: String(fm.status ?? ''),
    hosts: (fm.hosts ?? (hostMatch ? [hostMatch[2]] : [])).filter((s: string) => hostBySlug.has(s)),
    tags: fm.tags ?? [],
    summary: String(fm.summary ?? ''),
    verified: fm.verified ? String(fm.verified) : undefined,
    open: Number(fm.open ?? 0),
    listed: Boolean(data),
    html: rendered.html,
    headings: rendered.headings,
    text: plainText(rendered.html),
    part: partMatch ? Number(partMatch[1]) : undefined,
  };
}

export interface JournalEvent {
  time: string;
  kind: string;
}

export interface JournalDoc extends Doc {
  job: string;
  checkmkHost: string;
  service: string;
  events: JournalEvent[];
  outcome: string;
}

function loadJournal(p: Pending): JournalDoc {
  const base = path.posix.basename(p.source, '.md');
  const m = /^(\d{4}-\d{2}-\d{2})-(.+)-([0-9a-f]{12})$/.exec(base);
  if (!m) throw new Error(`Unexpected journal file name: ${p.source}`);
  const [, date, checkmkHost, job] = m;
  const stripped = stripTitle(readTracked(p.source));
  const rendered = renderMarkdown(stripped.body, p.source);
  const events: JournalEvent[] = rendered.headings
    .filter((h) => h.depth === 2)
    .map((h) => {
      const e = /^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?(?: [A-Z]{2,4})?): (.+)$/.exec(h.text);
      return e ? { time: e[1], kind: e[2] } : { time: '', kind: h.text };
    });
  const service = (stripped.title ?? '').split(' / ').slice(1).join(' / ') || 'alert';
  const slug = slugForCheckmkName(checkmkHost);
  const proposal = /\*\*Proposed action:\*\*\s*(.+)/.exec(stripped.body)?.[1]?.trim();
  const diagnosis = /\*\*Diagnosis[^*]*\*\*\s*(.+)/.exec(stripped.body)?.[1]?.trim() ?? '';
  const outcome = events.length ? events[events.length - 1].kind : 'recorded';
  return {
    source: p.source,
    route: p.route,
    title: `${checkmkHost}: ${service}`,
    date,
    type: 'responder',
    status: outcome,
    hosts: slug ? [slug] : [],
    tags: ['responder', ...(proposal && !/^none/i.test(proposal) ? ['fix-proposed'] : [])],
    summary: plainText(renderInline(diagnosis, p.source)),
    open: 0,
    listed: true,
    html: rendered.html,
    headings: rendered.headings,
    text: plainText(rendered.html),
    job,
    checkmkHost,
    service,
    events,
    outcome,
  };
}

export const writeups: Doc[] = pending.filter((p) => p.kind === 'writeup').map(loadWriteup);
export const hostNotes: Doc[] = pending.filter((p) => p.kind === 'hostnote').map(loadWriteup);
export const journal: JournalDoc[] = pending.filter((p) => p.kind === 'journal').map(loadJournal);

const newestFirst = (a: Doc, b: Doc) => b.date.localeCompare(a.date) || (a.part ?? 0) - (b.part ?? 0) || a.title.localeCompare(b.title);

/** Everything shown on the Writeups page, newest first. */
export const listedDocs: Doc[] = [...writeups, ...hostNotes.filter((d) => d.listed), ...journal].sort(newestFirst);

/** Every document that gets a page. */
export const allDocs: Doc[] = [...writeups, ...hostNotes, ...journal];

export const docsForHost = (slug: string) => listedDocs.filter((d) => d.hosts.includes(slug));
export const notesForHost = (slug: string) => hostNotes.filter((d) => d.route.startsWith(`hosts/${slug}/`));

// ---------------------------------------------------------------- host READMEs

export interface HostPage {
  /** the one-line description under the title in the README */
  lede?: string;
  /** hand-written sections worth showing; the generated tables are rebuilt from the inventory instead */
  sections: { heading: string; id: string; html: string }[];
  followUps: FollowUp[];
  date: string;
}

const GENERATED = new Set([
  'At a glance',
  'Ports',
  'Reverse-proxy routes',
  'Depends on / needed by',
  'History',
  'Interfaces',
  'Storage',
  'Guests',
  'Known issues / follow-ups',
]);

const toFollowUp = (item: string, source: string): FollowUp => {
  const html = renderInline(item, source);
  return { html, text: plainText(html) };
};

export const hostPages = new Map<string, HostPage>();
for (const h of hosts) {
  const source = `${h.dir}/README.md`;
  const { data, body } = splitFrontMatter(readTracked(source));
  const stripped = stripTitle(body);
  const parts = sections(stripped.body);
  const intro = parts[0].body.trim();
  const lede = /^>\s*(.+)$/m.exec(intro)?.[1];
  const followUpSection = parts.find((s) => s.heading === 'Known issues / follow-ups');
  hostPages.set(h.slug, {
    lede: lede ? renderInline(lede, source) : undefined,
    sections: parts
      .filter((s) => s.heading && !GENERATED.has(s.heading))
      // the generator's "nothing here yet" stub is not worth a section
      .filter((s) => !/^\s*_None yet\./.test(s.body))
      .map((s) => ({
        heading: s.heading,
        id: s.heading.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''),
        html: renderMarkdown(s.body, source).html,
      })),
    followUps: followUpSection ? uncheckedItems(followUpSection.body).map((i) => toFollowUp(i, source)) : [],
    date: String(data?.date ?? ''),
  });
}

// ---------------------------------------------------------------- follow-ups

export const followUps: FollowUpGroup[] = [];
for (const d of writeups) {
  if (!d.listed) continue;
  const body = splitFrontMatter(readTracked(d.source)).body;
  const items = uncheckedItems(body);
  if (items.length !== d.open) {
    throw new Error(`${d.source}: front matter says open: ${d.open} but the file has ${items.length} unchecked item(s)`);
  }
  if (!items.length) continue;
  followUps.push({
    source: d.source,
    route: d.route,
    title: d.title,
    date: d.date,
    hosts: d.hosts,
    origin: 'writeup',
    items: items.map((i) => toFollowUp(i, d.source)),
  });
}
for (const h of hosts) {
  const page = hostPages.get(h.slug)!;
  if (!page.followUps.length) continue;
  followUps.push({
    source: `${h.dir}/README.md`,
    route: `hosts/${h.slug}`,
    title: h.name,
    date: page.date,
    hosts: [h.slug],
    origin: 'host',
    items: page.followUps,
  });
}
followUps.sort((a, b) => b.date.localeCompare(a.date));

/** Known issues recorded on the host's own page (not the follow-ups of every writeup that mentions it). */
export const openCountForHost = (slug: string) => hostPages.get(slug)?.followUps.length ?? 0;

export const totalOpen = followUps.reduce((n, g) => n + g.items.length, 0);
