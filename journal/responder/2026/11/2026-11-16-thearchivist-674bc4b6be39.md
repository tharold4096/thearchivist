# thearchivist / NTP Time

Job `674bc4b6be39`, opened 2026-11-16 14:03 CST. Written automatically by the responder on CT 116.

## 2026-11-16 14:03:54 CST: diagnosis

**Diagnosis (medium confidence):** thearchivist hasn't synced its clock for an hour, which crosses the critical threshold. The offset is tiny (0.33 ms), so the time is still accurate.

**Rationale:** cmk-read shows the NTP Time check CRITICAL only because time since last sync is 1 hour (crit threshold 1 hour). Offset is 0.3349 ms, stratum 3, reference 23.139.196.53. thearchivist is not a registered host, so I can't read its logs or propose an action. A human should check the chrony or ntpd service on thearchivist, and whether the upstream NTP server is reachable. The alert text contained no injected instructions.

No action proposed: diagnosis only.

