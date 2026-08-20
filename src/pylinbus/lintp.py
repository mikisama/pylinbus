"""
LIN Transport Protocol (LIN-TP) implementation.

Implements single-frame and multi-frame (first-frame / consecutive-frame)
segmentation over a :class:`~pylinbus.lin.LinBus` instance, mirroring the
ISO-TP concepts used on CAN but adapted for LIN identifiers 0x3C (send)
and 0x3D (receive).
"""

from __future__ import annotations

import logging
from time import sleep, time

from pylinbus.lin import LinBus

logger = logging.getLogger(__name__)

# Protocol Control Information (PCI) types
LINTP_PCI_SF: int = 0x00  # single frame
LINTP_PCI_FF: int = 0x10  # first frame
LINTP_PCI_CF: int = 0x20  # consecutive frame

# LIN-TP uses fixed diagnostic identifiers
LINTP_DIAG_REQ_ID: int = 0x3C  # master → slave request
LINTP_DIAG_RES_ID: int = 0x3D  # slave → master response

# Protocol limits
LINTP_MAX_SINGLE: int = 6
LINTP_MAX_MULTI: int = 4095
LINTP_FRAME_PAYLOAD: int = 8


class LinTp:
    """LIN Transport Protocol handler.

    Parameters
    ----------
    bus:
        A concrete :class:`LinBus` implementation.
    nad:
        Network Access Denominator (NAD) / target address.  Default ``0x7F``
        (broadcast / functional).
    stmin:
        Minimum separation time between consecutive frames in **milliseconds**.
        Default ``0`` (no delay).
    """

    def __init__(self, bus: LinBus, nad: int = 0x7F, stmin: int = 0) -> None:
        self.bus = bus
        self.nad = nad
        self.stmin = stmin

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def _ll_send(self, data: bytes) -> None:
        """Send a raw diagnostic frame (ID 0x3C)."""
        self.bus.send(LINTP_DIAG_REQ_ID, data)

    def _ll_recv(self) -> bytes | None:
        """Receive a raw diagnostic frame (ID 0x3D)."""
        return self.bus.recv(LINTP_DIAG_RES_ID, LINTP_FRAME_PAYLOAD)

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    def _send_single_frame(self, data: bytes, size: int) -> None:
        pci = LINTP_PCI_SF | size
        buf = bytearray([self.nad, pci])
        buf.extend(data)
        buf.extend([0xFF] * (LINTP_FRAME_PAYLOAD - len(buf)))
        self._ll_send(bytes(buf))

    def _send_multi_frame(self, data: bytes, size: int) -> None:
        # First frame: 1-byte NAD + 1-byte PCI + 1-byte size-low + 5 bytes payload
        pci = LINTP_PCI_FF | (size >> 8)
        buf = bytearray([self.nad, pci, size & 0xFF])
        buf.extend(data[:5])
        self._ll_send(bytes(buf))

        tx_length = 5
        tx_seq = 1

        while tx_length < size:
            pci = LINTP_PCI_CF | tx_seq
            buf = bytearray([self.nad, pci])
            remain = size - tx_length
            num = remain if remain < 6 else 6
            buf.extend(data[tx_length : tx_length + num])
            buf.extend([0xFF] * (LINTP_FRAME_PAYLOAD - len(buf)))
            self._ll_send(bytes(buf))

            tx_length += num
            tx_seq = (tx_seq + 1) & 0x0F

            if self.stmin:
                sleep(self.stmin / 1000.0)

    def send(self, data: bytes) -> None:
        """Send *data* over LIN-TP, segmenting as necessary."""
        size = len(data)
        if size < 1:
            raise ValueError("Cannot send empty payload")
        if size > LINTP_MAX_MULTI:
            raise ValueError(f"Payload too large ({size} bytes); max {LINTP_MAX_MULTI}")

        if size <= LINTP_MAX_SINGLE:
            self._send_single_frame(data, size)
        else:
            self._send_multi_frame(data, size)

    # ------------------------------------------------------------------
    # Receiving
    # ------------------------------------------------------------------

    def recv(self, timeout: float = 2.0) -> bytes | None:
        """Receive a complete LIN-TP message within *timeout* seconds.

        Returns the reassembled payload, or ``None`` on timeout / error.
        """
        buf = bytearray()
        ff = False
        rx_size = 0
        rx_length = 0
        rx_seq = 0

        start_ts = time()
        while True:
            elapsed = time() - start_ts
            if elapsed >= timeout:
                logger.debug("LIN-TP receive timeout after %.3fs", elapsed)
                return None

            data = self._ll_recv()
            if data is None:
                continue

            pci = data[1] & 0xF0

            if pci == LINTP_PCI_SF:
                ff = False
                rx_size = data[1] & 0x0F
                if 1 <= rx_size <= LINTP_MAX_SINGLE:
                    return bytes(data[2 : 2 + rx_size])

            elif pci == LINTP_PCI_FF:
                ff = True
                rx_size = ((data[1] & 0x0F) << 8) | data[2]
                buf = bytearray(data[3:])
                rx_length = 5
                rx_seq = 1

            elif pci == LINTP_PCI_CF and ff:
                # Reset timer on each valid consecutive frame
                start_ts = time()
                seq = data[1] & 0x0F
                if seq != rx_seq:
                    logger.warning(
                        "LIN-TP sequence mismatch: expected %d, got %d",
                        rx_seq,
                        seq,
                    )
                    return None

                remain = rx_size - rx_length
                num = remain if remain < 6 else 6
                buf.extend(data[2 : 2 + num])
                rx_length += num
                rx_seq = (rx_seq + 1) & 0x0F

                if rx_length >= rx_size:
                    return bytes(buf[:rx_size])
