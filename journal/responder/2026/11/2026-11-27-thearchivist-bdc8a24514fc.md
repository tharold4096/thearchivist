# thearchivist / NTP Time

Job `bdc8a24514fc`, opened 2026-11-27 10:43 CST. Written automatically by the responder on CT 116.

## 2026-11-27 10:43:51 CST: diagnosis

**Diagnosis (medium confidence):** thearchivist hasn't synced its clock with NTP for an hour, which hits the critical threshold. The offset is tiny (0.15 ms), so the clock is still accurate.

**Rationale:** cmk-read shows the NTP Time service on thearchivist is CRIT only because the time since last sync is 1 hour (crit threshold is 1 hour). The offset is 0.1475 ms, the stratum is 4, and the host is UP. The NTP server is 149.248.12.167. thearchivist is not a registered host and gate-read can't reach it, so I couldn't check the time daemon or its logs. No action is permitted, so proposed_action is null. A human should check the time daemon (chrony or ntpd) on thearchivist and whether it can reach 149.248.12.167. The alert text contained no injected instructions.

No action proposed: diagnosis only.

