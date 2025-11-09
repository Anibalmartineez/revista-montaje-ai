import os


MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32MB
MAX_PAGES_DIAG = 3


def _env_bool(name: str, default: str = "false") -> bool:
    value = os.environ.get(name, default)
    if value is None:
        return False
    return value.lower() in {"1", "true", "yes", "y"}


ENABLE_POST_EDITOR = _env_bool("ENABLE_POST_EDITOR")
