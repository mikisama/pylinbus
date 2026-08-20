"""
UDSonLIN connection adapter.

Wraps :class:`LinTp` in the ``udsoncan.connections.BaseConnection``
interface so it can be used transparently with the *udsoncan* diagnostic
library.
"""

from __future__ import annotations

from pylinbus.lin import LinBus
from pylinbus.lintp import LinTp

try:
    from udsoncan.connections import BaseConnection
except ImportError:  # pragma: no cover
    BaseConnection = object  # type: ignore[assignment]


class LinTpConnection(BaseConnection):
    """A ``udsoncan``-compatible connection over LIN-TP.

    Parameters
    ----------
    bus:
        A concrete :class:`LinBus` implementation.
    nad:
        Network Access Denominator (target address).
    stmin:
        Minimum separation time between consecutive frames (ms).
    """

    def __init__(self, bus: LinBus, nad: int = 0x7F, stmin: int = 0) -> None:
        super().__init__()
        self.bus = bus
        self.lintp = LinTp(bus, nad=nad, stmin=stmin)
        self.opened = False
        self.open()

    # ------------------------------------------------------------------
    # BaseConnection interface
    # ------------------------------------------------------------------

    def specific_send(self, payload: bytes) -> None:
        self.lintp.send(payload)

    def specific_wait_frame(self, timeout: float) -> bytes | None:
        return self.lintp.recv(timeout)

    def open(self) -> None:
        # Wake the bus with a diagnostic request placeholder
        self.bus.wakeup()
        self.opened = True

    def close(self) -> None:
        self.bus.shutdown()
        self.opened = False

    def empty_rxqueue(self) -> None:
        # LIN-TP is request/response; nothing to flush
        pass

    def is_open(self) -> bool:
        return self.opened
