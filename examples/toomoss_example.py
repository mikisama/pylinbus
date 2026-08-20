"""
Example: Send a LIN Frame via Toomoss hardware.
"""

from pylinbus.backends import ToomossLin


def main():
    bus = ToomossLin(channel=0, bitrate=19200)
    bus.send(0x3C, bytes([0xFF] * 8))
    bus.shutdown()


if __name__ == "__main__":
    main()
