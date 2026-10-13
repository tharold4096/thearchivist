# Responder journal

Records in this directory are written and pushed **automatically** by the responder on CT 116
(see [`hosts/responder/`](../../hosts/responder/)), one file per incident:
`YYYY/MM/<date>-<host>-<job id>.md`. Each event (diagnosis, approval, auto-run, denial, expiry)
is appended as a section.

What is published, and what isn't:

* Published: Claude's structured diagnosis and rationale, the proposed action, who approved it,
  and the executor's verified result.
* Not published: raw Claude transcripts and tool output (logs can contain secrets). Those stay
  in `/var/lib/responder/transcripts/` on CT 116.
* Every record passes a secret filter (tokens, bearer and password patterns, ntfy topic names,
  long opaque strings) before it is committed.
* Alerts from arr-stack hosts are never published.

Commits come from `Responder (CT 116)` using a write deploy key that is only for this repo.
