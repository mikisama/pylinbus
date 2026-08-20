"""
Hardware backends for pylinbus.

Each backend is a concrete subclass of :class:`pylinbus.lin.LinBus`
that talks to a specific vendor's driver.

- :mod:`vector_lin` - Vector XL API (Windows)
- :mod:`toomoss_lin` - Toomoss USB-LIN adapter

Backends are imported lazily to avoid hard dependencies on vendor SDKs.
"""

from __future__ import annotations

__all__ = []  # populated below

try:  # pragma: no cover
    from pylinbus.backends.vector_lin import VectorLin

    __all__.append("VectorLin")
except ImportError:
    VectorLin = None  # type: ignore[assignment]

try:  # pragma: no cover
    from pylinbus.backends.toomoss_lin import ToomossLin

    __all__.append("ToomossLin")
except ImportError:
    ToomossLin = None  # type: ignore[assignment]
