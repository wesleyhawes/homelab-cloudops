"""An explicit registry, not arbitrary dynamic imports from user configuration."""
from dataclasses import dataclass
from ..errors import UnsupportedProvider

@dataclass(frozen=True)
class ProviderSpec:
    id: str
    title: str
    maturity: str
    role: str
    capabilities: tuple[str, ...]
    reason: str = ""

REGISTRY = {
    "nextcloud_aio": ProviderSpec("nextcloud_aio", "Nextcloud AIO", "pilot", "nextcloud_aio",
        ("check", "deploy", "backup", "backup_check", "verify", "recovery_info", "verify_recovery")),
    "owncloud_ocis": ProviderSpec("owncloud_ocis", "ownCloud Infinite Scale", "planned", "owncloud_ocis", (),
        "A separate adapter must protect oCIS identity, metadata, configuration and content."),
    "owncloud_server": ProviderSpec("owncloud_server", "ownCloud Server", "planned", "owncloud_server", (),
        "Classic ownCloud needs its own database, cache and application-aware recovery adapter."),
    "oxicloud": ProviderSpec("oxicloud", "OxiCloud", "planned", "oxicloud", (),
        "Requires a version-qualified PostgreSQL, file-storage and migration/recovery adapter."),
}

def provider_spec(name: str, operation: str | None = None) -> ProviderSpec:
    try:
        spec = REGISTRY[name]
    except KeyError as exc:
        raise UnsupportedProvider("Unknown provider.") from exc
    if spec.maturity == "planned":
        raise UnsupportedProvider(f"{spec.title} is an extension point, not an implemented deployment. {spec.reason}")
    if operation and operation not in spec.capabilities:
        raise UnsupportedProvider(f"{operation} is not supported by {spec.title}.")
    return spec


def adapter_for(config, state):
    """Only code-reviewed adapters may execute. Configuration cannot import code."""
    provider_spec(config.provider)
    if config.provider == "nextcloud_aio":
        from .nextcloud import NextcloudAIO
        return NextcloudAIO(config, state)
    raise UnsupportedProvider("Provider adapter is not implemented.")
