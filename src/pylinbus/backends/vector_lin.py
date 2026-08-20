"""
Vector XL-API LIN backend.

Wraps the ``pyvxlapi`` / ``_winapi`` bindings to provide a
:class:`pylinbus.lin.LinBus` implementation for Vector hardware
(VN1611, VN1630, etc.) on Windows.
"""

from __future__ import annotations

import ctypes
import logging
import time

from pylinbus.lin import LinBus

logger = logging.getLogger(__name__)

try:
    from _winapi import INFINITE, WaitForSingleObject  # type: ignore[import]
except ImportError:  # pragma: no cover
    INFINITE = 0xFFFFFFFF  # type: ignore[assignment]

    def WaitForSingleObject(*_args, **_kwargs):  # type: ignore[no-redef]
        raise OSError("WaitForSingleObject requires Windows")


try:
    from pyvxlapi import (  # type: ignore[import]
        LIN_MSG,
        XL_ACTIVATE_RESET_CLOCK,
        XL_BUS_ACTIVE_CAP_LIN,
        XL_BUS_TYPE_LIN,
        XL_INVALID_PORTHANDLE,
        XL_LIN_CALC_CHECKSUM,
        XL_LIN_CALC_CHECKSUM_ENHANCED,
        XL_LIN_MASTER,
        XL_LIN_VERSION_2_1,
        XLaccess,
        XLdriverConfig,
        XLevent,
        XLhandle,
        XLlinStatPar,
        XLportHandle,
        xlActivateChannel,
        xlClosePort,
        xlDeactivateChannel,
        xlFlushReceiveQueue,
        xlGetDriverConfig,
        xlLinSendRequest,
        xlLinSetChannelParams,
        xlLinSetDLC,
        xlLinSetSlave,
        xlLinSwitchSlave,
        xlOpenPort,
        xlReceive,
        xlSetNotification,
    )
except ImportError:  # pragma: no cover
    logger.warning("pyvxlapi not available; VectorLin backend disabled")
    LIN_MSG = 0
    XL_ACTIVATE_RESET_CLOCK = 0
    XL_BUS_ACTIVE_CAP_LIN = 0
    XL_BUS_TYPE_LIN = 0
    XL_INVALID_PORTHANDLE = 0
    XL_LIN_CALC_CHECKSUM = 0
    XL_LIN_CALC_CHECKSUM_ENHANCED = 0
    XL_LIN_MASTER = 0
    XL_LIN_VERSION_2_1 = 0
    XLaccess = ctypes.c_ulong  # type: ignore[assignment]
    XLdriverConfig = type("XLdriverConfig", (), {})  # type: ignore[assignment]
    XLevent = type("XLevent", (), {})  # type: ignore[assignment]
    XLhandle = ctypes.c_void_p  # type: ignore[assignment]
    XLlinStatPar = type("XLlinStatPar", (), {})  # type: ignore[assignment]
    XLportHandle = type("XLportHandle", (), {})  # type: ignore[assignment]

    def _missing_api(*_a, **_kw):  # type: ignore[no-redef]
        raise ImportError("pyvxlapi is required for the VectorLin backend")

    xlActivateChannel = xlClosePort = xlDeactivateChannel = _missing_api  # type: ignore
    xlFlushReceiveQueue = xlGetDriverConfig = xlLinSendRequest = _missing_api  # type: ignore
    xlLinSetChannelParams = xlLinSetDLC = xlLinSetSlave = _missing_api  # type: ignore
    xlLinSwitchSlave = xlOpenPort = xlReceive = _missing_api  # type: ignore
    xlSetNotification = _missing_api  # type: ignore


class VectorLin(LinBus):
    """Vector hardware LIN backend (Windows only)."""

    def __init__(
        self,
        channel: int = 0,
        bitrate: int = 19200,
        name: str = "",
        **kwargs,
    ) -> None:
        super().__init__(channel, bitrate, **kwargs)

        driver_config = XLdriverConfig()
        xlGetDriverConfig(driver_config)

        if driver_config.channelCount == 0:
            raise RuntimeError("VectorLIN: No device connected!")

        channel_config = driver_config.channel[channel]
        if not (channel_config.channelBusCapabilities & XL_BUS_ACTIVE_CAP_LIN):
            raise RuntimeError(f"Channel {channel} does not support LIN communication")

        self.channel_mask = channel_config.channelMask
        permission_mask = XLaccess()
        self.port_handle = XLportHandle(XL_INVALID_PORTHANDLE)

        status = xlOpenPort(
            self.port_handle,
            name.encode(),
            self.channel_mask,
            permission_mask,
            256,
            3,
            XL_BUS_TYPE_LIN,
        )
        logger.debug("xlOpenPort status=%s", status)

        self.event_handle = XLhandle()
        status = xlSetNotification(self.port_handle, self.event_handle, 1)
        logger.debug("xlSetNotification status=%s", status)

        self.set_bitrate(bitrate)

        self.dlc_list = [0xFF] * 64
        xlLinSetDLC(self.port_handle, self.channel_mask, bytes(self.dlc_list))

        xlActivateChannel(
            self.port_handle,
            self.channel_mask,
            XL_BUS_TYPE_LIN,
            XL_ACTIVATE_RESET_CLOCK,
        )
        xlFlushReceiveQueue(self.port_handle)
        self.is_shutdown = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _recv_lin(self) -> bytes | None:
        xl_event = XLevent()
        event_count = ctypes.c_uint(1)
        status = xlReceive(self.port_handle, event_count, xl_event)
        if status != 0:
            return None
        if xl_event.tag != LIN_MSG:
            return None
        msg = xl_event.tagData.linMsgApi.linMsg
        dlc = msg.dlc
        return bytes(msg.data[:dlc])

    def _recv_internal(self, timeout: float = 0.01) -> bytes | None:
        end_time = time.time() + timeout if timeout else None
        while True:
            if end_time is None:
                time_left_ms = INFINITE
            else:
                time_left = end_time - time.time()
                time_left_ms = max(0, int(time_left * 1000))
            WaitForSingleObject(self.event_handle.value, time_left_ms)

            data = self._recv_lin()
            if data:
                return data
            if end_time is not None and time.time() > end_time:
                return None

    # ------------------------------------------------------------------
    # LinBus API
    # ------------------------------------------------------------------

    def send(self, id: int, data: bytes) -> None:
        chk_type = (
            XL_LIN_CALC_CHECKSUM
            if id in (0x3C, 0x3D)
            else XL_LIN_CALC_CHECKSUM_ENHANCED
        )

        if self.dlc_list[id] != len(data):
            self.dlc_list[id] = len(data)
            xlLinSetDLC(self.port_handle, self.channel_mask, bytes(self.dlc_list))

        xlLinSwitchSlave(self.port_handle, self.channel_mask, id, 0xFF)
        xlLinSetSlave(
            self.port_handle,
            self.channel_mask,
            id,
            bytes(data),
            len(data),
            chk_type,
        )
        xlLinSendRequest(self.port_handle, self.channel_mask, id, 0)
        self._recv_internal()

    def recv(self, id: int, dlc: int = 8) -> bytes | None:
        if self.dlc_list[id] != dlc:
            self.dlc_list[id] = dlc
            xlLinSetDLC(self.port_handle, self.channel_mask, bytes(self.dlc_list))

        xlLinSwitchSlave(self.port_handle, self.channel_mask, id, 0x00)
        xlLinSendRequest(self.port_handle, self.channel_mask, id, 0)
        return self._recv_internal()

    def set_bitrate(self, bitrate: int = 19200) -> None:
        LinStatPar = XLlinStatPar()
        LinStatPar.LINMode = XL_LIN_MASTER
        LinStatPar.baudrate = bitrate
        LinStatPar.LINVersion = XL_LIN_VERSION_2_1
        xlLinSetChannelParams(self.port_handle, self.channel_mask, LinStatPar)
        self.bitrate = bitrate
        self.dlc_list = [0xFF] * 64

    def shutdown(self) -> None:
        if self.is_shutdown:
            return
        xlDeactivateChannel(self.port_handle, self.channel_mask)
        xlClosePort(self.port_handle)
        self.is_shutdown = True
