"""Provide qless_solver as a top-level package for CLI entrypoints."""

import sys
from importlib import import_module

module = import_module("cli.qless_solver")
sys.modules[__name__] = module
