// hosts/inventory.yml, normalised for rendering: addresses, network membership,
// topology edges and the status snapshot.
import { parse } from 'yaml';
import { isTracked, readTracked, tracked } from './repo';

export type Status = 'running' | 'stopped' | 'offline' | 'planned' | 'retired' | 'unknown';
export type Kind = 'physical' | 'lxc' | 'vm' | 'client';

export interface Port {
  port: number;
  proto: string;
  service: string;
  bind: string;
  via: 'direct' | 'caddy' | 'tailscale' | string;
  notes?: string;
}

export interface Address {
  ip: string; // without the /mask
  cidr?: string; // as written, when it carries a mask
  label: string; // interface name or "LAN" / "Tailscale"
  role?: string;
  network: string;
  notes?: string;
}

export interface Route {
  name: string;
  upstream: string;
  notes?: string;
  target?: string; // slug of the host the upstream address belongs to
}

export interface Host {
  slug: string;
  name: string;
  kind: Kind;
  group: 'physical' | 'lxc' | 'vm' | 'clients';
  vmid?: number;
  runs_on?: string;
  role: string;
  hardware?: string;
  os?: string;
  schedule?: string;
  formerly?: string;
  notes?: string;
  onboot?: boolean;
  web?: string | null;
  backup?: string;
  mounts: string[];
  resources?: { cores?: number; memory_mb?: number; disk_gb?: number; data_disk_gb?: number };
  monitored: { checkmk: boolean; wazuh: string | null };
  interfaces: { name: string; role?: string; ip: string | null; network: string; speed?: string; notes?: string }[];
  storage: { id: string; type: string; device: string; size?: string; use: string }[];
  ports: Port[];
  routes: Route[];
  depends_on: string[];
  // derived
  needed_by: string[];
  guests: string[];
  addresses: Address[];
  networks: string[];
  primaryAddress: string; // what to print when one address has to stand for the host
  dhcp: boolean;
  status: Status;
  idLabel: string; // "CT 103", "VM 150", "Physical", "Client"
  kindLabel: string;
  dir: string; // repo folder, e.g. hosts/lxc/ct103-caddy
  proxiedBy: { via: string; name: string; port: number }[]; // Caddy names that front this host
}

export interface Network {
  id: string;
  name: string;
  cidr: string | null;
  gateway?: string;
  dhcp_pool?: string;
  dns?: string;
  domain?: string;
  notes?: string;
  members: string[];
}

export interface Edge {
  kind: 'depends' | 'proxy';
  from: string;
  to: string;
  label?: string;
}

export interface StatusSnapshot {
  /** ISO date the statuses were observed. */
  asOf: string;
  /** false today: the site shows a dated snapshot. A future status.json can set this. */
  live: boolean;
  hosts: Record<string, Status>;
}

const raw = parse(readTracked('hosts/inventory.yml')) as {
  verified: string;
  networks: Omit<Network, 'members'>[];
  hosts: any[];
};

const stripMask = (ip: string) => ip.replace(/\/\d+$/, '');

/**
 * The one place host status comes from.
 *
 * Today it is the `status` field of each inventory entry, observed on
 * `verified`. If a tracked `status.json` appears at the repo root (the planned
 * CT 116 job), it wins, and nothing else in the site has to change:
 *   { "as_of": "2026-12-01", "live": true, "hosts": { "ct100-jellyfin": "running", ... } }
 */
function loadStatus(): StatusSnapshot {
  const fromInventory: StatusSnapshot = {
    asOf: String(raw.verified),
    live: false,
    hosts: Object.fromEntries(raw.hosts.map((h) => [h.slug, (h.status ?? 'unknown') as Status])),
  };
  if (!isTracked('status.json')) return fromInventory;
  const file = JSON.parse(readTracked('status.json'));
  return {
    asOf: String(file.as_of ?? fromInventory.asOf),
    live: Boolean(file.live),
    hosts: { ...fromInventory.hosts, ...(file.hosts ?? {}) },
  };
}

export const statusSnapshot = loadStatus();
export const inventoryVerified = String(raw.verified);

const KIND_LABEL: Record<Kind, string> = {
  physical: 'Physical machine',
  lxc: 'LXC container',
  vm: 'Virtual machine',
  client: 'Client',
};

function normalise(h: any): Host {
  const kind = h.kind as Kind;
  const group = (h.group ?? (kind === 'lxc' ? 'lxc' : kind === 'vm' ? 'vm' : kind === 'client' ? 'clients' : 'physical')) as Host['group'];
  const interfaces = (h.interfaces ?? []) as Host['interfaces'];

  const addresses: Address[] = [];
  for (const i of interfaces) {
    if (i.ip) addresses.push({ ip: stripMask(i.ip), cidr: i.ip.includes('/') ? i.ip : undefined, label: i.name, role: i.role, network: i.network, notes: i.notes });
  }
  const dhcp = h.ip === 'dhcp';
  if (h.ip && !dhcp) addresses.push({ ip: stripMask(h.ip), label: 'LAN', network: 'lab-lan' });
  if (h.tailscale_ip) addresses.push({ ip: h.tailscale_ip, label: 'Tailscale', network: 'tailnet' });

  const networks = new Set<string>(h.networks ?? []);
  for (const i of interfaces) networks.add(i.network);
  for (const a of addresses) networks.add(a.network);
  if (!networks.size && h.runs_on) networks.add('lab-lan');
  if (dhcp) networks.add('lab-lan');

  const dir = tracked
    .find((p) => p.startsWith('hosts/') && p.endsWith(`/${h.slug}/README.md`))
    ?.replace(/\/README\.md$/, '');
  if (!dir) throw new Error(`No tracked README for host ${h.slug}`);

  const primary = addresses.find((a) => a.network === 'lab-lan') ?? addresses[0];

  return {
    slug: h.slug,
    name: h.name,
    kind,
    group,
    vmid: h.vmid,
    runs_on: h.runs_on,
    role: h.role,
    hardware: h.hardware,
    os: h.os,
    schedule: h.schedule,
    formerly: h.formerly,
    notes: h.notes,
    onboot: h.onboot,
    web: h.web ?? null,
    backup: h.backup,
    mounts: h.mounts ?? [],
    resources: h.resources,
    monitored: { checkmk: Boolean(h.monitored?.checkmk), wazuh: h.monitored?.wazuh ?? null },
    interfaces,
    storage: (h.storage ?? []).map((s: any) => ({ ...s, size: s.size ? String(s.size) : undefined })),
    ports: (h.ports ?? []).map((p: any) => ({ ...p, service: String(p.service), bind: String(p.bind) })),
    routes: h.routes ?? [],
    depends_on: h.depends_on ?? [],
    needed_by: [],
    guests: [],
    addresses,
    networks: [...networks],
    primaryAddress: primary ? primary.ip : dhcp ? 'DHCP' : 'no address',
    dhcp,
    status: statusSnapshot.hosts[h.slug] ?? 'unknown',
    idLabel: kind === 'lxc' ? `CT ${h.vmid}` : kind === 'vm' ? `VM ${h.vmid}` : kind === 'client' ? 'Client' : 'Physical',
    kindLabel: KIND_LABEL[kind],
    dir,
    proxiedBy: [],
  };
}

export const hosts: Host[] = raw.hosts.map(normalise);
export const hostBySlug = new Map(hosts.map((h) => [h.slug, h]));

for (const h of hosts) {
  for (const dep of h.depends_on) {
    const target = hostBySlug.get(dep);
    if (!target) throw new Error(`${h.slug} depends on unknown host ${dep}`);
    target.needed_by.push(h.slug);
  }
  if (h.runs_on) {
    const parent = hostBySlug.get(h.runs_on);
    if (!parent) throw new Error(`${h.slug} runs on unknown host ${h.runs_on}`);
    parent.guests.push(h.slug);
  }
}

const hostByIp = new Map<string, Host>();
for (const h of hosts) for (const a of h.addresses) hostByIp.set(a.ip, h);

export const edges: Edge[] = [];
for (const h of hosts) {
  for (const dep of h.depends_on) edges.push({ kind: 'depends', from: h.slug, to: dep });
  for (const r of h.routes) {
    const [ip, port] = r.upstream.split(':');
    const target = hostByIp.get(ip);
    if (!target) continue;
    r.target = target.slug;
    target.proxiedBy.push({ via: h.slug, name: r.name, port: Number(port) });
    if (!edges.some((e) => e.kind === 'proxy' && e.from === h.slug && e.to === target.slug)) {
      edges.push({ kind: 'proxy', from: h.slug, to: target.slug });
    }
  }
}

export const networks: Network[] = raw.networks.map((n) => ({
  ...n,
  members: hosts.filter((h) => h.networks.includes(n.id)).map((h) => h.slug),
}));
export const networkById = new Map(networks.map((n) => [n.id, n]));

export const GROUPS: { id: Host['group']; label: string }[] = [
  { id: 'physical', label: 'Physical machines' },
  { id: 'lxc', label: 'Containers' },
  { id: 'vm', label: 'Virtual machines' },
  { id: 'clients', label: 'Clients' },
];

export const STATUS_LABEL: Record<Status, string> = {
  running: 'Running',
  stopped: 'Stopped',
  offline: 'Offline',
  planned: 'Planned',
  retired: 'Retired',
  unknown: 'Not checked',
};

/** Journal records name hosts the way Checkmk does ("jellyfin", "samba-vm"). */
export function slugForCheckmkName(name: string): string | undefined {
  return hosts.find((h) => h.name === name || h.slug === name)?.slug;
}
