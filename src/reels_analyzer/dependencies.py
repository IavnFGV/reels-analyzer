from __future__ import annotations

import shutil
from importlib.util import find_spec


def require_python_package(package_name: str, feature_name: str) -> None:
    if find_spec(package_name) is None:
        raise RuntimeError(
            f"Feature '{feature_name}' requires Python package '{package_name}'. "
            f"Install the matching optional dependency."
        )


def require_command(command_name: str, feature_name: str) -> None:
    if shutil.which(command_name) is None:
        raise RuntimeError(
            f"Feature '{feature_name}' requires system command '{command_name}' to be installed."
        )
