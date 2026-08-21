# pylinbus

LIN (Local Interconnect Network) interface module for Python with transport-layer support
and multiple hardware backends. Inspire by [python-can](https://github.com/hardbyte/python-can)

## Features

- **Abstract bus interface** - implement your own hardware driver by
  subclassing `LinBus`.
- **LIN Transport Protocol** - ISO-TP-style segmentation and reassembly
  (`LinTp`) over LIN diagnostic frames (0x3C / 0x3D).
- **udsoncan connection adapter** - drop-in `LinTpConnection` for the
  popular [udsoncan](https://github.com/pylessard/python-udsoncan) UDS library.
- **Hardware backends**:
  - **Toomoss** USB-LIN adapters (`toomoss_py`)
  - **Vector** XL API (`pyvxlapi`, Windows)
- **Master mode only** – Optimized for LIN Master operation (Slave support planned for future releases).

## Installation

```bash
pip install pylinbus
```

## Quick start

```python
from pylinbus import LinTp
from pylinbus.backends import ToomossLin

# Open the bus
bus = ToomossLin(channel=0, bitrate=19200)
tp = LinTp(bus, nad=0x01)

# Send / receive using the transport layer
tp.send(bytes([0x10, 0x01]))
rx = tp.recv(timeout=0.5)
print(rx.hex())

bus.shutdown()
```

## Using udsoncan

```python
from udsoncan.client import Client
from udsoncan.configs import default_client_config

from pylinbus.backends import ToomossLin
from pylinbus.connection import LinTpConnection

bus = ToomossLin(channel=0, bitrate=19200)
conn = LinTpConnection(bus, nad=0x01)

cfg = dict(default_client_config)
cfg["standard_version"] = 2006

with Client(conn, config=cfg) as client:
    response = client.change_session(1)
    print(response)
```

## Related

- [python-can](https://github.com/hardbyte/python-can) – for the inspiration.
- [udsoncan](https://github.com/pylessard/python-udsoncan) – for providing a comprehensive UDS library.
- [pyvxlapi](https://github.com/mikisama/pyvxlapi) - Vector hardware backend
- [toomoss-py](https://github.com/mikisama/toomoss_py) - Toomoss hardware backend

## License

MIT
