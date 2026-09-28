class CloudOpsError(RuntimeError):
    """An actionable, safe-to-display operational error."""

class UnsupportedProvider(CloudOpsError):
    pass

class Busy(CloudOpsError):
    pass
