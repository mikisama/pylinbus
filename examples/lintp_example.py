"""
Example: LIN-TP communication using a Toomoss USB-LIN adapter.
"""

from pylinbus import LinTp
from pylinbus.backends import ToomossLin


def main():
    # Open the bus
    bus = ToomossLin(channel=0, bitrate=19200)
    tp = LinTp(bus, nad=0x01)

    # Send / receive using the transport layer
    tp.send(bytes([0x10, 0x01]))
    rx = tp.recv(timeout=0.5)
    print(rx.hex())

    bus.shutdown()


if __name__ == "__main__":
    main()
