"""
Example: UDS diagnostic service over LIN-TP using udsoncan.
"""

from udsoncan.client import Client
from udsoncan.configs import default_client_config

from pylinbus.backends import ToomossLin
from pylinbus.connection import LinTpConnection


def main():
    bus = ToomossLin(channel=0, bitrate=19200)
    conn = LinTpConnection(bus, nad=0x01)

    cfg = dict(default_client_config)
    cfg["standard_version"] = 2006

    with Client(conn, config=cfg) as client:
        response = client.change_session(1)
        print(response)


if __name__ == "__main__":
    main()
