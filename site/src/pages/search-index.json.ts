// The search index, fetched the first time the search box opens.
import { TYPE_LABEL, allDocs } from '../lib/docs';
import { hostBySlug, hosts } from '../lib/inventory';
import { url } from '../lib/paths';

export function GET() {
  const entries = [
    ...hosts.map((h) => ({
      k: 'host',
      t: h.name,
      u: url(`hosts/${h.slug}`),
      w: h.kind === 'lxc' || h.kind === 'vm' ? h.idLabel : h.kindLabel,
      s: [h.addresses.map((a) => a.ip).join(', '), h.role].filter(Boolean).join(' — '),
      x: [h.slug, h.idLabel, h.os, ...h.addresses.map((a) => a.ip), ...h.ports.map((p) => `${p.port} ${p.service}`), ...h.routes.map((r) => r.name), ...h.proxiedBy.map((p) => p.name), h.web ?? ''].join(' '),
      b: [h.role, h.hardware, h.notes, h.backup].filter(Boolean).join(' '),
    })),
    ...allDocs.map((d) => ({
      k: d.type === 'responder' ? 'journal' : 'doc',
      t: d.title,
      u: url(d.route),
      w: [TYPE_LABEL[d.type], d.date].filter(Boolean).join(', '),
      s: d.summary,
      x: [...d.tags, ...d.hosts, ...d.hosts.map((s) => hostBySlug.get(s)?.name ?? '')].join(' '),
      b: d.text,
    })),
  ];
  return new Response(JSON.stringify(entries), { headers: { 'Content-Type': 'application/json' } });
}
