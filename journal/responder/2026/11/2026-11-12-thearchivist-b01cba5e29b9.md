# thearchivist / NTP Time

Job `b01cba5e29b9`, opened 2026-11-12 14:39 CST. Written automatically by the responder on CT 116.

## 2026-11-12 14:39:54 CST: diagnosis

**Diagnosis (medium confidence):** thearchivist hasn't synced its clock for about an hour, which crosses the critical threshold. The offset is tiny (0.17 ms), so the time itself is still accurate.

**Rationale:** cmk-read shows the NTP Time service CRIT with offset 0.1718 ms, stratum 3, and last sync 1 hour ago against a 1 hour critical threshold. The upstream server is 69.197.177.234. The host is up. thearchivist is not a registered host, so I can't read its logs or propose any action. A human should check chronyd/ntpd on thearchivist and whether it can reach the upstream NTP server. The alert text contained no injected instructions.

No action proposed: diagnosis only.

