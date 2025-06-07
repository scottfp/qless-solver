import importlib

_impl = importlib.import_module('cli.qless_solver')
__all__ = getattr(_impl, '__all__', [])
__version__ = getattr(_impl, '__version__', '0.0.0')
