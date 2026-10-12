# ntfy users/ACL relevant to CheckMK (CT 102)

Topic names are **unguessable and kept off git** (`<SET-ON-HOST>`). ntfy's iOS
relay wakes phones on `sha256(base-url/topic)` at ntfy.sh. With a common pair
like `http://ntfy.home.arpa` + `homelab-alerts`, strangers' servers wake our
phone (phantom empty "New message" pushes; confirmed 2026-10-12 18:06:12),
and anyone who knows the name can do the same on purpose.

| User | Access | Credential / topic lives at |
|---|---|---|
| `checkmk` | write-only `homelab-alerts-<SET-ON-HOST>` | token -> CT 115 `~monitoring/etc/ntfy-token` (600); URL -> `~monitoring/etc/ntfy-url` (600) |
| `homelab` | write-only `homelab-updates-<SET-ON-HOST>` | `/usr/local/sbin/homelab-update` and `/etc/thinpool-alert.conf` on thearchivist |
| `tobias` | admin | phone app (subscriptions on `http://ntfy.home.arpa`) |

Recreate:
    NTFY_PASSWORD=<random> ntfy user add checkmk
    ntfy access checkmk homelab-alerts-<suffix> write-only
    ntfy token add --label "checkmk notifications" checkmk
Suffix: `tr -dc 'a-z0-9' < /dev/urandom | head -c 10` (letters/digits only).
