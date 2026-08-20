"""
Abstract LIN bus interface.

Hardware vendors should subclass :class:`LinBus` and implement the five
abstract methods (:meth:`send`, :meth:`recv`, :meth:`set_bitrate`,
:meth:`wakeup`, :meth:`shutdown`).  See :mod:`pylinbus.backends` for
reference implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LinBus(ABC):
    """Hardware-agnostic LIN bus interface.

    Parameters
    ----------
    channel:
        Logical channel number understood by the underlying driver.
    bitrate:
        Bus speed in bits per second (default ``19200``, the LIN default).
    **kwargs:
        Vendor-specific options forwarded by subclasses.
    """

    def __init__(self, channel: int = 0, bitrate: int = 19200, **kwargs) -> None:
        self.channel = channel
        self.bitrate = bitrate
        self.is_shutdown = True

    # ------------------------------------------------------------------
    # Abstract API
    # ------------------------------------------------------------------

    @abstractmethod
    def send(self, id: int, data: bytes) -> None:
        """
        Transmit a LIN frame.

        Parameters
        ----------
        id:
            LIN identifier (0-63).
        data:
            Payload bytes.
        """
        raise NotImplementedError

    @abstractmethod
    def recv(self, id: int, dlc: int = 8) -> bytes | None:
        """
        Receive a LIN frame for the given identifier.

        Parameters
        ----------
        id:
            LIN identifier (0-63).
        dlc:
            Data length code (number of bytes expected).

        Returns
        -------
        bytes or None
            Received payload, or ``None`` if nothing was available.
        """
        raise NotImplementedError

    @abstractmethod
    def set_bitrate(self, bitrate: int = 19200) -> None:
        """
        Change the bus baud rate.

        Parameters
        ----------
        bitrate:
            New baud rate in bits per second.
        """
        raise NotImplementedError

    @abstractmethod
    def shutdown(self) -> None:
        """Release hardware resources and deactivate the channel."""
        raise NotImplementedError

    def wakeup(self) -> None:
        """Send a wake-up frame (broadcast 0xFF on ID 0x3C)."""
        self.send(0x3C, bytes([0xFF] * 8))
