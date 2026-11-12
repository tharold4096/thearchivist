// The only door between the repository and the site.
//
// Everything the site shows comes through `tracked` / `readTracked`, which are
// backed by `git ls-files`. A file that git does not track cannot reach the
// build, even when it sits in the working tree — that is what keeps the
// local-only arr-stack material off the public site.
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';

export const REPO_ROOT = execFileSync('git', ['rev-parse', '--show-toplevel'], {
  encoding: 'utf8',
}).trim();

export const GITHUB_REPO = 'https://github.com/tharold4096/thearchivist';
export const GITHUB_BRANCH = 'main';

// Belt and braces: if one of these ever shows up in `git ls-files`, the repo
// itself has leaked and the build must stop rather than publish it.
const DENY = /(arr-stack|sonarr|radarr|prowlarr|lidarr|readarr|bazarr|seerr|qbittorrent|flaresolverr|(^|\/)ct1(09|1[0-4])-)/i;

const all = execFileSync('git', ['ls-files', '-z'], { cwd: REPO_ROOT, encoding: 'utf8' })
  .split('\0')
  .filter(Boolean);

const leaked = all.filter((p) => DENY.test(p));
if (leaked.length) {
  throw new Error(
    `Refusing to build: git tracks files that match the local-only deny list:\n  ${leaked.join('\n  ')}`,
  );
}

/** Every git-tracked path that is repo content (the site's own source is excluded). */
export const tracked: string[] = all.filter((p) => !p.startsWith('site/') && !p.startsWith('.github/'));

const trackedSet = new Set(tracked);
const trackedDirs = new Set<string>();
for (const p of tracked) {
  let d = path.posix.dirname(p);
  while (d && d !== '.') {
    trackedDirs.add(d);
    d = path.posix.dirname(d);
  }
}

export const isTracked = (p: string) => trackedSet.has(p);
export const isTrackedDir = (p: string) => trackedDirs.has(p.replace(/\/$/, ''));

export function readTracked(p: string): string {
  if (!trackedSet.has(p)) throw new Error(`Not a git-tracked file: ${p}`);
  return readFileSync(path.join(REPO_ROOT, p), 'utf8');
}

export const githubBlob = (p: string) => `${GITHUB_REPO}/blob/${GITHUB_BRANCH}/${p}`;
export const githubTree = (p: string) => `${GITHUB_REPO}/tree/${GITHUB_BRANCH}/${p.replace(/\/$/, '')}`;
