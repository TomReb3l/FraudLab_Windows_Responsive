"""
FraudLab Exhibition Configuration

Central configuration layer.
Exhibition mode is the default safe mode.
"""

import os


def get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.lower() in (
        "1",
        "true",
        "yes",
        "on"
    )


FRAUDLAB_MODE = os.getenv(
    "FRAUDLAB_MODE",
    "exhibition"
)

ENABLE_AI = get_bool_env(
    "ENABLE_AI",
    False
)

OFFLINE_MODE = get_bool_env(
    "OFFLINE_MODE",
    True
)

DEBUG_MODE = get_bool_env(
    "DEBUG_MODE",
    False
)


def is_exhibition_mode() -> bool:
    return FRAUDLAB_MODE.lower() == "exhibition"


def is_ai_enabled() -> bool:
    return ENABLE_AI
