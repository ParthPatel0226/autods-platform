"""Adapter: builds a DOMAIN_REGISTRY dict from domains.domain_registry API.

The backend exposes:
    list_available_domains() -> list[{"name": ..., "display_name": ..., "icon": ...}]
    get_domain_config(name: str) -> BaseDomainConfig

BaseDomainConfig has:
    .domain_name, .display_name, .icon, .detection_keywords (dict), .to_dict()
    NOTE: to_dict() does NOT include detection_keywords -- access directly.

This adapter builds a flat DOMAIN_REGISTRY dict for use in cf_* components.
"""
from __future__ import annotations

_REGISTRY: dict | None = None


def _build() -> dict:
    try:
        from domains.domain_registry import list_available_domains, get_domain_config
        registry: dict = {}
        for entry in list_available_domains():
            name = entry.get("name", "")
            if not name:
                continue
            try:
                cfg = get_domain_config(name)
                d = cfg.to_dict()
                # to_dict() may omit detection_keywords -- inject directly
                if "detection_keywords" not in d:
                    try:
                        d["detection_keywords"] = cfg.detection_keywords
                    except AttributeError:
                        d["detection_keywords"] = {}
                registry[name] = d
            except Exception:
                registry[name] = {**entry}
        return registry
    except Exception:
        return {}


def _get_registry() -> dict:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build()
    return _REGISTRY


class _RegistryProxy(dict):
    """Lazy-loading dict that builds the registry on first access."""

    def _load(self) -> None:
        if not super().__len__():
            self.update(_get_registry())

    def get(self, key, default=None):  # type: ignore[override]
        self._load()
        return super().get(key, default)

    def __getitem__(self, key):
        self._load()
        return super().__getitem__(key)

    def __contains__(self, key):
        self._load()
        return super().__contains__(key)

    def __iter__(self):
        self._load()
        return super().__iter__()

    def items(self):
        self._load()
        return super().items()

    def values(self):
        self._load()
        return super().values()

    def keys(self):
        self._load()
        return super().keys()


DOMAIN_REGISTRY: dict = _RegistryProxy()
