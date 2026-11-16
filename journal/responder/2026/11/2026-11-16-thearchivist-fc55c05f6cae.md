# thearchivist / NTP Time

Job `fc55c05f6cae`, opened 2026-11-16 16:21 CST. Written automatically by the responder on CT 116.

## 2026-11-16 16:21:52 CST: diagnosis

**Diagnosis (medium confidence):** thearchivist hasn't synced its clock for an hour, so NTP Time is critical. The offset is tiny (0.11 ms), so the clock is still accurate.

**Rationale:** cmk-read shows offset 0.1148 ms, stratum 3, and time since last sync of 1 hour against a 1 hour critical threshold. The reference server is 23.139.196.53. thearchivist is not a registered host, so I can't read its logs and can't propose an action. A human should check whether chrony or ntpd is running on thearchivist and whether the upstream NTP server is reachable. The alert text contained no instructions.

No action proposed: diagnosis only.

