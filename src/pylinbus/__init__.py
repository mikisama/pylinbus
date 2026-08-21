"""
pylinbus - LIN Bus Transport Protocol for Python
===============================================

Quick start
-----------
>>> from pylinbus import LinBus, LinTp
>>> from pylinbus.backends import VectorLin
>>> bus = VectorLin(channel=0, bitrate=19200)
>>> tp  = LinTp(bus, nad=0x01)
>>> tp.send(bytes([0x10, 0x01]))
>>> rx  = tp.recv(timeout=0.5)
"""

from pylinbus.lin import LinBus
from pylinbus.lintp import LinTp

__version__ = "0.1.2"

__all__ = [
    "LinBus",
    "LinTp",
]
