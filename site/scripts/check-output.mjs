// Scans the built site before it can be deployed. Fails the build if the
// output contains anything that looks like a secret or local-only material.
//
// Run automatically by `npm run build`, and again as its own CI step.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';

const DIST = path.resolve(import.meta.dirname, '../dist');

const CHECKS = [
  { name: 'ntfy token', re: /tk_[A-Za-z0-9]{8,}/g },
  // The placeholder form (homelab-alerts-<SET-ON-HOST>, -<suffix>) is expected; a real suffix is not.
  { name: 'ntfy topic name', re: /homelab-(?:alerts|updates)-(?!&lt;|<|\\u003c)[A-Za-z0-9]/g },
  { name: 'private key', re: /BEGIN [A-Z ]*PRIVATE KEY/g },
  // Paths that only exist in the local-only arr-stack material.
  { name: 'arr-stack path', re: /inventory\.arr-stack|hosts\/lxc\/arr-stack|hosts\/lxc\/ct1(?:09|1[0-4])-/g },
];

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = path.join(dir, name);
    if (statSync(p).isDirectory()) yield* walk(p);
    else yield p;
  }
}

let files = 0;
let placeholders = 0;
const findings = [];
for (const file of walk(DIST)) {
  if (!/\.(html|json|js|css|txt|xml|svg)$/.test(file)) continue;
  files++;
  const text = readFileSync(file, 'utf8');
  placeholders += (text.match(/&lt;SET-ON-HOST&gt;/g) ?? []).length;
  for (const { name, re } of CHECKS) {
    for (const m of text.matchAll(re)) {
      const at = Math.max(0, m.index - 40);
      findings.push(`${name}: ${path.relative(DIST, file)}: …${text.slice(at, m.index + 60).replace(/\s+/g, ' ')}…`);
    }
  }
  // A placeholder that reached the page as a raw tag would be invisible to readers.
  if (file.endsWith('.html') && /<set-on-host/i.test(text)) findings.push(`unescaped <SET-ON-HOST> placeholder: ${path.relative(DIST, file)}`);
}

if (findings.length) {
  console.error(`\ncheck-output: ${findings.length} problem(s) in the built site:\n  ${findings.join('\n  ')}\n`);
  process.exit(1);
}
console.log(`check-output: ${files} files scanned, no secrets or local-only paths; ${placeholders} <SET-ON-HOST> placeholders shown as text.`);
