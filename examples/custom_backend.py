"""
Example: implementing a custom LinBus backend
"""

from typing import Optional

from pylinbus import LinTp
from pylinbus.lin import LinBus


class MyCustomLin(LinBus):
    """Skeleton for a custom LIN backend."""

    def __init__(self, channel: int = 0, bitrate: int = 19200) -> None:
        super().__init__(channel, bitrate)
        self._rx_queue: list[bytes] = []
        self.is_shutdown = False

    def send(self, id: int, data: bytes) -> None:
        print(f"[TX] id=0x{id:02X} data={data.hex()}")
        # ... call your hardware driver here ...

    def recv(self, id: int, dlc: int = 8) -> Optional[bytes]:
        # ... poll your hardware here ...
        if self._rx_queue:
            return self._rx_queue.pop(0)
        return None

    def set_bitrate(self, bitrate: int = 19200) -> None:
        self.bitrate = bitrate
        print(f"[CONFIG] bitrate set to {bitrate}")

    def wakeup(self) -> None:
        print("[WAKEUP] sending wake pulse")
        self.send(0x3C, b"\xff" * 8)

    def shutdown(self) -> None:
        print("[SHUTDOWN] releasing resources")
        self.is_shutdown = True


def main():
    # Open the bus
    bus = MyCustomLin(channel=0, bitrate=19200)
    tp = LinTp(bus, nad=0x01)

    # Feed a fake single-frame response into the queue
    bus._rx_queue.append(bytes([0x01, 0x02, 0x50, 0x01, 0xFF, 0xFF, 0xFF, 0xFF]))

    # Send / receive using the transport layer
    tp.send(bytes([0x10, 0x01]))
    rx = tp.recv(timeout=0.5)
    print(rx.hex())

    bus.shutdown()


if __name__ == "__main__":
    main()
