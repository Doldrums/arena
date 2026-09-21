"""Execution-only helpers for native optimizer bridges.

Factories are user-supplied executable research code, staged and hashed by the
native runtime. Importing this module never loads a factory or a framework.
"""
import importlib.util
from pathlib import Path
import sys
import uuid


def bounded_positive(value):
    value = int(value)
    if not 1 <= value <= 1_000_000:
        raise ValueError("Budget must be between 1 and 1000000")
    return value


def load_factory(reference):
    filename, separator, function = reference.rpartition(":")
    path = Path(filename)
    if (not separator or not function.isidentifier() or path.is_absolute()
            or ".." in path.parts or path.suffix != ".py" or path.is_symlink()
            or not path.resolve().is_relative_to(Path.cwd().resolve())):
        raise ValueError("Factory must be a staged relative.py:function inside the workspace")
    # A distinct retained identity supports dataclasses, postponed annotations,
    # and pickled returned objects without later factories replacing their module.
    name = "arena_native_factory_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("Factory is not a Python source file")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        factory = getattr(module, function)
        if not callable(factory):
            raise ValueError("Factory must be callable")
        result = factory()
        if type(result) is not dict:
            raise ValueError("Factory must return a dictionary of native optimizer inputs")
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return result


def output_directory(value):
    # NativeRecipeAdapter supplies the reserved absolute output path, which is
    # outside the cloned workspace but inside the run's output directory.
    if not Path(value).is_absolute():
        raise ValueError("Native output must be an absolute runtime-reserved path")
    path = Path(value).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path
