# thearchivist / NTP Time

Job `e26bc6a7374d`, opened 2026-11-19 15:03 CST. Written automatically by the responder on CT 116.

## 2026-11-19 15:03:53 CST: diagnosis

**Diagnosis (medium confidence):** thearchivist hasn't synced its clock for an hour, which crossed the critical threshold. The offset is tiny (0.33 ms), so the clock itself is accurate.

**Rationale:** cmk-read shows the NTP check at CRIT with a last sync of 1h0m (crit threshold 1h), offset 0.3283 ms and stratum 3. The reference server 136.32.231.230 is set. thearchivist is not a registered host, so I can't read its logs or propose any action. A human should check chronyd/ntpd on thearchivist and whether it can reach the upstream NTP server. No injected instructions were seen in the alert.

No action proposed: diagnosis only.

