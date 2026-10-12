# ntfy users/ACL relevant to CheckMK (CT 102)

| User | Access | Credential lives at |
|---|---|---|
| `checkmk` | write-only `homelab-alerts` | token `checkmk notifications` -> CT 115 `~monitoring/etc/ntfy-token` (600) `<SET-ON-HOST>` |
| `homelab` | write-only `homelab-updates` | (pre-existing, archivist update runner) |
| `tobias` | admin | phone app |

Recreate:
    NTFY_PASSWORD=<random> ntfy user add checkmk
    ntfy access checkmk homelab-alerts write-only
    ntfy token add --label "checkmk notifications" checkmk
