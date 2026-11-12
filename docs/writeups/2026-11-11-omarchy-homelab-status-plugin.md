# Omarchy shell plugin: Homelab Status

**Date:** 2026-11-11
**Machine(s):** Omarchy laptop (admin laptop)
**Status:** Complete
**Tags:** monitoring, omarchy, quickshell

---

## Why I built this

* Checkmk tells my phone when something breaks, but nothing on the laptop showed at a glance whether the lab was up. I wanted that in the bar.

## How I built it

* **Tools/stack:** Omarchy shell plugin (Quickshell/QML), a bash probe script using `/dev/tcp`.
* **Key steps:**
  * User plugin `tobias.homelab` in `~/.config/omarchy/plugins/tobias.homelab/`, built on Omarchy's `Panel` / `KeyboardPanel` kit.
  * `probe.sh` opens one TCP connection per host (3 s timeout, in parallel) and prints `host:port up|down ms`. It sends no data and writes nothing.
  * The bar icon is normal when every host answers, red when some are down, and dimmed when none answer (lab powered off, or laptop off the tailnet). The panel lists each host with latency; clicking a row copies its address.
  * Each row is coloured: green when the port answers, yellow when it answers slower than `slowMs` (default 250 ms) or when the port is closed but the host still answers one ping ("no service"), red when neither answers. Green and yellow are read from the active theme's `colors.toml`. The bar icon goes yellow when the worst row is yellow.
  * Checks run every 60 s in the background (`refreshIntervalSec`); `backgroundRefresh: false` limits them to while the panel is open.
  * Enabled with `omarchy plugin enable tobias.homelab --section right`, placed before `omarchy.network`.
  * Host list lives in the widget's entry in `~/.config/omarchy/shell.json` (`hosts`: name, host, port). Ten hosts: sentrygate, thearchivist, caddy, ntfy, wazuh, budget, jellyfin, checkmk, responder, pbs.
* **Config/scripts:** [`../../hosts/omarchy/homelab-status-plugin/`](../../hosts/omarchy/homelab-status-plugin/). No credentials are involved.

## What broke

* **Issue: panel said "No hosts configured".
  Symptom:** the manifest's `barWidget.defaults.hosts` list never reached the widget.
  **Root cause:** the shell does not merge manifest defaults into a widget's settings; `setting()` only reads the `shell.json` entry.
  **Fix:** set the list with `omarchy bar set tobias.homelab hosts '<json>' --json`.

* **Issue: colour change did not appear after saving.
  Symptom:** the panel kept running the old QML and `Homelab.js` after several files were rewritten at once; `omarchy-shell shell rescanPlugins` did not help.
  **Root cause:** not found.
  **Fix:** `omarchy restart shell`.

## What worked

* `omarchy plugin validate` exits 0. With the panel open, all ten hosts showed up with 46–56 ms latency over Tailscale. The probe script reports a closed port and malformed targets (`bad;host:80`, port 99999) as down without connecting. All three colours were checked with two temporary rows (a closed port on thearchivist, an unused address) and a 50 ms threshold, then removed.

## What I'd do differently

* This only proves a port accepts connections, not that the service behind it is healthy. Reading Checkmk's state would be richer but needs a credential on the laptop.
