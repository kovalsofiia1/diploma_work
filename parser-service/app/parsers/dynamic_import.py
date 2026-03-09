from __future__ import annotations

import importlib.util
import sys
from types import ModuleType


def import_module_from_file(module_name: str, file_path: str) -> ModuleType:
    """
    Import a python file as a module, even if its filename contains '-' (not importable normally).
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not import module {module_name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[call-arg]
    return module


