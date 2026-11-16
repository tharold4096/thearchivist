# thearchivist / NTP Time

Job `8fea32d01c07`, opened 2026-11-16 15:12 CST. Written automatically by the responder on CT 116.

## 2026-11-16 15:12:53 CST: diagnosis

**Diagnosis (medium confidence):** thearchivist hasn't synced its clock for about an hour, which crosses the critical threshold. The offset is tiny (0.2 ms), so the clock is still accurate.

**Rationale:** cmk-read shows the NTP check is critical only on time since last sync (1 hour, critical threshold 1 hour). The offset is 0.1951 ms, the stratum is 3, and the reference is 23.139.196.53. The host is up. thearchivist isn't registered with gate-read, so I couldn't check its chrony or ntpd logs, and no action is allowed. A human should check the time daemon on thearchivist and whether the upstream server 23.139.196.53 is reachable. They could also consider adding a second NTP source. Nothing in the tool output tried to give me instructions.

No action proposed: diagnosis only.

