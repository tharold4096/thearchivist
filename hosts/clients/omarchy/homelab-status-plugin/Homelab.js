.pragma library

var MAX_HOSTS = 40
var HOST_RE = /^[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$/

// Turn the `hosts` setting into a clean list. Anything that is not a plain
// hostname/IPv4 with a valid port is dropped, so nothing unexpected reaches
// the probe script's arguments.
function normalizeHosts(raw) {
  var out = []
  var seen = {}
  // Settings lists can arrive as QML list wrappers, not JS Arrays.
  if (!raw || typeof raw !== "object" || typeof raw.length !== "number") return out
  for (var i = 0; i < raw.length && out.length < MAX_HOSTS; i++) {
    var entry = raw[i]
    if (!entry || typeof entry !== "object") continue
    var host = String(entry.host === undefined ? "" : entry.host).trim()
    var port = parseInt(entry.port, 10)
    if (!HOST_RE.test(host) || !(port >= 1 && port <= 65535)) continue
    var target = host + ":" + port
    if (seen[target]) continue
    seen[target] = true
    var name = String(entry.name === undefined || entry.name === null ? "" : entry.name)
      .replace(/[\x00-\x1f\x7f]/g, " ").trim().slice(0, 40)
    out.push({ name: name !== "" ? name : host, host: host, port: port, target: target })
  }
  return out
}

// Parse probe.sh output into { "<host:port>": { state, ms } }, where state is
// "up", "partial" (host pings, port closed) or "down". Only targets we
// asked about are accepted.
function parseResults(text, hosts) {
  var wanted = {}
  for (var i = 0; i < hosts.length; i++) wanted[hosts[i].target] = true
  var results = {}
  var lines = String(text || "").slice(0, 16384).split("\n")
  for (var j = 0; j < lines.length; j++) {
    var match = /^(\S{1,260}) (up|partial|down) (\d{1,6})$/.exec(lines[j])
    if (!match || !wanted[match[1]]) continue
    results[match[1]] = { state: match[2], ms: parseInt(match[3], 10) }
  }
  return results
}

// "ok" (green), "warn" (yellow: answered slowly, or host up but port closed),
// "down" (red), or "" while unchecked.
function level(result, slowMs) {
  if (!result) return ""
  if (result.state === "down") return "down"
  if (result.state === "partial") return "warn"
  return result.ms > slowMs ? "warn" : "ok"
}

function summary(hosts, results, slowMs) {
  var counts = { total: hosts.length, ok: 0, warn: 0, down: 0, up: 0, known: 0 }
  for (var i = 0; i < hosts.length; i++) {
    var result = results[hosts[i].target]
    var lvl = level(result, slowMs)
    if (lvl === "") continue
    counts[lvl]++
    counts.known++
    if (result.state === "up") counts.up++
  }
  return counts
}

// Pull green/yellow/red out of the theme's colors.toml. Only #rrggbb values
// are accepted; anything missing keeps the fallback.
function palette(text, fallback) {
  var out = { green: fallback.green, yellow: fallback.yellow, red: fallback.red }
  var lines = String(text || "").slice(0, 16384).split("\n")
  for (var i = 0; i < lines.length; i++) {
    var match = /^\s*(green|yellow|red)\s*=\s*["']?(#[0-9A-Fa-f]{6})\b/.exec(lines[i])
    if (match) out[match[1]] = match[2]
  }
  return out
}
