Samba file server — progress summary

VM built and fully configured on the Archivist: Debian 13, dedicated 400GB disk (archive:400) separate from Jellyfin's storage, ext4 with usrquota, four accounts (jill, adam, caleb, wesley) each capped at 100GB, Samba shares configured and validated. Confirmed working end-to-end over Tailscale. Destination NAT on Sentry Gate (WAN → VM:445) is correctly configured and confirmed functioning at the packet level — full three-way handshake completes in both directions between the family LAN and the VM.

Blocked on: Client/AP Isolation on the family WiFi router silently drops the return path between same-network WiFi devices — confirmed via packet capture (SYN-ACK sent, never arrives) and a failed same-network ping test. This is a deliberate security posture on the router, not a misconfiguration on Sentry Gate or the VM, and the decision has been made not to disable it network-wide. Resolution requires either per-device isolation exceptions (if the router supports that granularity) or a different access path for family devices — deferred to a later session, not an open bug in the file server itself.

Everything downstream of the router is done and correct. When this gets picked back up, the fix is router-side, not another pass through Samba/NAT/firewall config.
