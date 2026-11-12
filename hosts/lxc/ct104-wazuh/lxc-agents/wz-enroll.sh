#!/bin/sh
# Runs on thearchivist host. Usage: wz-enroll.sh <CTID> <group>
# Enrolls a Wazuh agent pinned to the manager's version. Password is read from a
# host-side 600 file and never printed.
set -e
id=$1; grp=$2; VER=4.14.7-1; PASSF=/root/.wz-enroll.pass
[ -s "$PASSF" ] || { echo "missing $PASSF"; exit 1; }
pct push $id /usr/share/keyrings/wazuh.gpg /usr/share/keyrings/wazuh.gpg --perms 644
pct push $id "$PASSF" /root/.wz-enroll.pass --perms 600
pct exec $id -- sh -c "
  set -e
  echo 'deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main' > /etc/apt/sources.list.d/wazuh.list
  apt-get update -qq -o Dir::Etc::sourcelist=sources.list.d/wazuh.list -o Dir::Etc::sourceparts=- -o APT::Get::List-Cleanup=0
  WAZUH_MANAGER=192.168.10.204 WAZUH_AGENT_GROUP=$grp WAZUH_REGISTRATION_PASSWORD=\$(cat /root/.wz-enroll.pass) \
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq wazuh-agent=$VER >/dev/null
  rm -f /root/.wz-enroll.pass
  apt-mark hold wazuh-agent >/dev/null
  systemctl daemon-reload; systemctl enable --now wazuh-agent >/dev/null 2>&1
  printf '%s ' \$(hostname) \$(dpkg-query -W -f='\${Version}' wazuh-agent) \$(apt-mark showhold | grep -c wazuh-agent)hold \$(systemctl is-active wazuh-agent)
  [ -e /root/.wz-enroll.pass ] && echo PASSFILE-LEFT || echo passfile-removed
"
