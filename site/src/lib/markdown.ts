// Markdown → HTML for writeups, host notes and journal records.
//
// Raw HTML in the source is escaped, not passed through, so placeholders such
// as <SET-ON-HOST> or <CTID> show up as written instead of vanishing as
// unknown tags.
import MarkdownIt from 'markdown-it';
import path from 'node:path';
import { createHighlighter } from 'shiki';
import { githubBlob, githubTree, isTracked, isTrackedDir } from './repo';
import { url } from './paths';

const LANGS = ['sh', 'bash', 'xml', 'yaml', 'powershell', 'php', 'jsonc', 'json', 'python', 'ini', 'toml', 'diff'];
const THEMES = { light: 'vitesse-light', dark: 'vitesse-dark' } as const;

const highlighter = await createHighlighter({ themes: Object.values(THEMES), langs: LANGS });

/** repo path → site path, filled in by docs.ts once it knows every page. */
const routes = new Map<string, string>();
export function registerRoute(repoPath: string, sitePath: string) {
  routes.set(repoPath.replace(/\/$/, ''), sitePath);
}

export interface Heading {
  depth: number;
  id: string;
  text: string;
}

function slugify(text: string, used: Map<string, number>): string {
  const base =
    text
      .toLowerCase()
      .replace(/[`*_~]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'section';
  const n = used.get(base) ?? 0;
  used.set(base, n + 1);
  return n ? `${base}-${n}` : base;
}

/**
 * Resolve a link written in a repo markdown file.
 *  - another page on the site      → its site URL
 *  - any other git-tracked file    → the file on GitHub
 *  - anything git does not track   → null (rendered as plain text)
 */
export function resolveHref(href: string, sourcePath: string): { href: string; external: boolean } | null {
  if (/^[a-z][a-z0-9+.-]*:/i.test(href) || href.startsWith('//')) return { href, external: true };
  if (href.startsWith('#')) return { href, external: false };

  const [rawPath, frag] = href.split('#');
  const target = path.posix.normalize(path.posix.join(path.posix.dirname(sourcePath), decodeURI(rawPath))).replace(/\/$/, '');
  if (target.startsWith('..')) return null;
  const hash = frag ? `#${frag}` : '';

  const route = routes.get(target) ?? routes.get(`${target}/README.md`);
  if (route !== undefined) return { href: url(route) + hash, external: false };
  if (isTracked(target)) return { href: githubBlob(target) + hash, external: true };
  if (isTrackedDir(target)) return { href: githubTree(target), external: true };
  return null;
}

const md = new MarkdownIt({
  html: false,
  linkify: false,
  typographer: false,
  highlight(code, lang) {
    const language = LANGS.includes(lang) ? lang : 'text';
    return highlighter.codeToHtml(code.replace(/\n$/, ''), {
      lang: language,
      themes: THEMES,
      defaultColor: false,
    });
  },
});

// Heading ids + collected outline.
md.core.ruler.push('heading_ids', (state) => {
  const used = new Map<string, number>();
  const headings: Heading[] = [];
  const tokens = state.tokens;
  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i].type !== 'heading_open') continue;
    const inline = tokens[i + 1];
    const text = (inline.children ?? [])
      .filter((t) => t.type === 'text' || t.type === 'code_inline')
      .map((t) => t.content)
      .join('');
    const id = slugify(text, used);
    tokens[i].attrSet('id', id);
    headings.push({ depth: Number(tokens[i].tag.slice(1)), id, text });
  }
  state.env.headings = headings;
});

// Links: rewrite to site routes or GitHub; unpublished targets lose the link.
md.core.ruler.push('repo_links', (state) => {
  const source: string = state.env.sourcePath;
  for (const block of state.tokens) {
    for (const t of block.children ?? []) {
      if (t.type !== 'link_open') continue;
      const resolved = resolveHref(t.attrGet('href') ?? '', source);
      if (!resolved) {
        t.attrSet('data-unpublished', '1');
        continue;
      }
      t.attrSet('href', resolved.href);
      if (resolved.external && /^https?:/.test(resolved.href)) t.attrSet('rel', 'noopener');
    }
  }
});

const openStack: boolean[] = [];
md.renderer.rules.link_open = (tokens, idx, options, _env, self) => {
  const dead = tokens[idx].attrGet('data-unpublished') === '1';
  openStack.push(dead);
  return dead ? '<span class="unpublished" title="Kept in the local repo, not published">' : self.renderToken(tokens, idx, options);
};
md.renderer.rules.link_close = (tokens, idx, options, _env, self) =>
  openStack.pop() ? '</span>' : self.renderToken(tokens, idx, options);

// Wide tables scroll inside their own box instead of stretching the page.
md.renderer.rules.table_open = () => '<div class="table-scroll" tabindex="0" role="group" aria-label="Table"><table>';
md.renderer.rules.table_close = () => '</table></div>';

function postprocess(html: string): string {
  return (
    html
      // GitHub task lists
      .replace(/<li>(\s*<p>)?\[ \] /g, '<li class="task">$1<span class="box" role="img" aria-label="Open"></span>')
      .replace(/<li>(\s*<p>)?\[[xX]\] /g, '<li class="task done">$1<span class="box" role="img" aria-label="Done"></span>')
      // the generator writes <br> inside table cells
      .replace(/&lt;br\s*\/?&gt;/g, '<br>')
  );
}

export interface Rendered {
  html: string;
  headings: Heading[];
}

/** Render a whole document. `sourcePath` is the repo path, used to resolve relative links. */
export function renderMarkdown(source: string, sourcePath: string): Rendered {
  const env: { sourcePath: string; headings?: Heading[] } = { sourcePath };
  const html = postprocess(md.render(source, env));
  return { html, headings: env.headings ?? [] };
}

/** Render one line (a follow-up item, a table cell) without the wrapping <p>. */
export function renderInline(source: string, sourcePath: string): string {
  return md.renderInline(source, { sourcePath });
}

/** Rendered HTML → searchable plain text. */
export function plainText(html: string): string {
  return html
    .replace(/<[^>]+>/g, ' ')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, '&')
    .replace(/\s+/g, ' ')
    .trim();
}
