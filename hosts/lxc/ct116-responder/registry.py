"""Load the host registry and answer the only questions the rest of the code may ask of it."""
import tomllib

DEFAULT_PATH = "/etc/responder/registry.toml"


class Registry:
    def __init__(self, data):
        self.hosts = data.get("hosts", {})
        prot = data.get("protected", {})
        self._protected_names = set(prot.get("checkmk_names", []))
        self._protected_units = set(prot.get("units", []))

    @classmethod
    def load(cls, path=DEFAULT_PATH):
        with open(path, "rb") as f:
            return cls(tomllib.load(f))

    def by_checkmk_name(self, name):
        """Registry key for a Checkmk host name, or None."""
        for key, h in self.hosts.items():
            if h.get("checkmk_name") == name:
                return key
        return None

    def host(self, key):
        return self.hosts.get(key)

    def is_read(self, key, verb):
        h = self.hosts.get(key)
        return bool(h) and verb in h.get("read_verbs", [])

    def is_write(self, key, verb):
        h = self.hosts.get(key)
        return bool(h) and verb in h.get("write_verbs", [])

    def is_protected(self, key):
        """Protected = always ask, never remembered. Unknown hosts count as protected."""
        h = self.hosts.get(key)
        if not h:
            return True
        return (bool(h.get("protected"))
                or h.get("checkmk_name") in self._protected_names
                or h.get("unit") in self._protected_units)

    def validate_proposal(self, proposal):
        """Return (host_key, verb, unit) if the proposal names a registered write verb, else None."""
        if not isinstance(proposal, dict):
            return None
        key, verb = proposal.get("host"), proposal.get("verb")
        if not isinstance(key, str) or not isinstance(verb, str) or not self.is_write(key, verb):
            return None
        return key, verb, self.hosts[key]["unit"]
