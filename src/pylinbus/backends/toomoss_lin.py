"""
Toomoss USB-LIN adapter backend.

Wraps the ``toomoss_py`` / ``usb2lin_ex`` C bindings to provide a
:class:`pylinbus.lin.LinBus` implementation for Toomoss hardware.
"""

from __future__ import annotations

import logging
from ctypes import byref, c_ubyte, c_uint
from enum import IntEnum

from pylinbus.lin import LinBus

logger = logging.getLogger(__name__)

try:
    from toomoss_py.api.usb2lin_ex import (  # type: ignore[import]
        LIN_EX_CHECK_EXT,
        LIN_EX_CHECK_STD,
        LIN_EX_MASTER,
        LIN_EX_CtrlPowerOut,
        LIN_EX_Init,
        LIN_EX_MasterRead,
        LIN_EX_MasterWrite,
        USB_CloseDevice,
        USB_OpenDevice,
        USB_ScanDevice,
    )
except ImportError:  # pragma: no cover
    logger.warning("toomoss_py not available; ToomossLin backend disabled")

    LIN_EX_CHECK_STD = LIN_EX_CHECK_EXT = 0
    LIN_EX_MASTER = 0

    def _missing_api(*_a, **_kw):
        raise ImportError("toomoss_py is required for the ToomossLin backend")

    LIN_EX_CtrlPowerOut = LIN_EX_Init = _missing_api  # type: ignore
    LIN_EX_MasterRead = LIN_EX_MasterWrite = _missing_api  # type: ignore
    USB_CloseDevice = USB_OpenDevice = USB_ScanDevice = _missing_api  # type: ignore


class VBATConfig(IntEnum):
    """VBAT output voltage configuration."""

    OUTPUT_0V = 0
    OUTPUT_12V = 1
    OUTPUT_5V = 2


class ToomossLin(LinBus):
    """Toomoss USB-LIN adapter backend."""

    def __init__(
        self,
        index: int = 0,
        channel: int = 0,
        bitrate: int = 19200,
        vbat_output: VBATConfig = VBATConfig.OUTPUT_0V,
        **kwargs,
    ) -> None:
        super().__init__(channel, bitrate, **kwargs)

        self.dev = 0
        self.init_bitrate = bitrate
        self.vbat_output = vbat_output

        dev_handles = (c_uint * 8)()
        ret = USB_ScanDevice(byref(dev_handles))
        if ret == 0:
            raise RuntimeError("ToomossLIN: No device connected!")

        self.dev = dev_handles[index]

        ret = USB_OpenDevice(self.dev)
        if ret == 0:
            raise RuntimeError("ToomossLIN: Failed to open device!")

        self.set_bitrate(bitrate)
        self.is_shutdown = False

    # ------------------------------------------------------------------
    # LinBus API
    # ------------------------------------------------------------------

    def send(self, id: int, data: bytes) -> None:
        data_buffer = (c_ubyte * 8)(*data)
        check_type = LIN_EX_CHECK_STD if id == 0x3C else LIN_EX_CHECK_EXT
        ret = LIN_EX_MasterWrite(
            self.dev,
            self.channel,
            id,
            data_buffer,
            len(data),
            check_type,
        )
        if ret < 0:
            raise RuntimeError(f"ToomossLIN: send failed (id=0x{id:02X})")

    def recv(self, id: int, dlc: int = 8) -> bytes | None:
        data_buffer = (c_ubyte * 8)()
        ret = LIN_EX_MasterRead(
            self.dev,
            self.channel,
            id,
            data_buffer,
        )
        if ret > 0:
            return bytes(data_buffer[:dlc])
        return None

    def set_bitrate(self, bitrate: int = 19200) -> None:
        self.bitrate = bitrate
        ret = LIN_EX_Init(self.dev, self.channel, bitrate, LIN_EX_MASTER)
        if ret < 0:
            raise RuntimeError("ToomossLIN: Init failed!")

        ret = LIN_EX_CtrlPowerOut(self.dev, self.channel, self.vbat_output)
        if ret < 0:
            raise RuntimeError("ToomossLIN: VBAT config failed!")

    def shutdown(self) -> None:
        if self.is_shutdown:
            return
        self.set_bitrate(self.init_bitrate)
        USB_CloseDevice(self.dev)
        self.is_shutdown = True
