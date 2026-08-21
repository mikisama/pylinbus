# Pylinbus Examples: From Simple to Complex

This guide presents the provided `pylinbus` examples in a progressive order, starting with the most basic usage and building up to advanced customizations. Each step adds new concepts and layers of functionality.

---

## 1. Basic LIN Frame Transmission (Hardware Backend)

**Goal:** Send a single raw LIN frame using a supported hardware adapter.

**Complexity:** ★☆☆☆☆
**Concepts:** Opening a bus, sending a frame, shutting down.

Both `ToomossLin` and `VectorLin` backends work identically – only the import changes.

```python
# toomoss_example.py (or vector_example.py)
from pylinbus.backends import ToomossLin   # or VectorLin

def main():
    # Open the bus on channel 0 at 19.2 kbps
    bus = ToomossLin(channel=0, bitrate=19200)
    # bus = VectorLin(channel=0, bitrate=19200)

    # Send a frame with ID 0x3C and 8 bytes of 0xFF
    bus.send(0x3C, bytes([0xFF] * 8))

    # Release resources
    bus.shutdown()

if __name__ == "__main__":
    main()
```

**What you learn:**
- How to instantiate a hardware-specific LIN bus.
- The basic `send()` and `shutdown()` methods.

---

## 2. LIN Transport Layer (LIN‑TP) Communication

**Goal:** Exchange multi‑frame messages using the LIN Transport Protocol (ISO 17987‑3).

**Complexity:** ★★☆☆☆
**Concepts:** Wrapping the bus with `LinTp`, using NAD (Node Address), sending and receiving with timeouts.

```python
# lintp_example.py
from pylinbus import LinTp
from pylinbus.backends import ToomossLin

def main():
    bus = ToomossLin(channel=0, bitrate=19200)

    # Create a transport-layer instance with our node address (NAD = 0x01)
    tp = LinTp(bus, nad=0x01)

    # Send a short message (will be packed into a single-frame LIN‑TP frame)
    tp.send(bytes([0x10, 0x01]))

    # Receive a response (blocks up to 0.5 seconds)
    rx = tp.recv(timeout=0.5)
    print(rx.hex())   # prints the received payload

    bus.shutdown()

if __name__ == "__main__":
    main()
```

**What you learn:**
- How to use the `LinTp` wrapper for segmentation/reassembly.
- The difference between raw frame send and transport‑layer send.
- Handling timeouts and receiving data.

---

## 3. UDS Diagnostic Service over LIN‑TP

**Goal:** Perform a Unified Diagnostic Services (UDS) request (e.g., session change) using `udsoncan` on top of LIN‑TP.

**Complexity:** ★★★☆☆
**Concepts:** Combining `LinTpConnection` with the `udsoncan` client, configuring diagnostic session.

```python
# uds_example.py
from udsoncan.client import Client
from udsoncan.configs import default_client_config

from pylinbus.backends import ToomossLin
from pylinbus.connection import LinTpConnection

def main():
    bus = ToomossLin(channel=0, bitrate=19200)

    # Create a connection object that adapts LinTp to udsoncan's interface
    conn = LinTpConnection(bus, nad=0x01)

    # Customise UDS client configuration (use ISO 14229-1:2006)
    cfg = dict(default_client_config)
    cfg["standard_version"] = 2006

    # Use the connection in a udsoncan client context
    with Client(conn, config=cfg) as client:
        response = client.change_session(1)   # request default session
        print(response)                       # print the UDS response

    # Connection and bus are automatically closed by the context manager

if __name__ == "__main__":
    main()
```

**What you learn:**
- How to bridge `pylinbus` with a higher‑level diagnostic library.
- Using `LinTpConnection` to conform to `udsoncan`’s required interface.
- Handling session control and interpreting diagnostic responses.

---

## 4. Implementing a Custom LIN Backend

**Goal:** Create your own hardware driver by subclassing `LinBus` and integrating it with LIN‑TP.

**Complexity:** ★★★★☆
**Concepts:** Extending the abstract `LinBus` class, implementing `send()`, `recv()`, `set_bitrate()`, `wakeup()`, and `shutdown()`; simulating reception with an internal queue.

```python
# custom_backend.py
from typing import Optional
from pylinbus import LinTp
from pylinbus.lin import LinBus

class MyCustomLin(LinBus):
    """Skeleton for a custom LIN backend."""

    def __init__(self, channel: int = 0, bitrate: int = 19200) -> None:
        super().__init__(channel, bitrate)
        self._rx_queue: list[bytes] = []   # fake RX buffer
        self.is_shutdown = False

    def send(self, id: int, data: bytes) -> None:
        # Here you would call your actual hardware driver
        print(f"[TX] id=0x{id:02X} data={data.hex()}")

    def recv(self, id: int, dlc: int = 8) -> Optional[bytes]:
        # Poll your hardware; here we simulate with a queue
        if self._rx_queue:
            return self._rx_queue.pop(0)
        return None

    def set_bitrate(self, bitrate: int = 19200) -> None:
        self.bitrate = bitrate
        print(f"[CONFIG] bitrate set to {bitrate}")

    def wakeup(self) -> None:
        print("[WAKEUP] sending wake pulse")
        self.send(0x3C, b"\xff" * 8)   # typical wake‑up frame

    def shutdown(self) -> None:
        print("[SHUTDOWN] releasing resources")
        self.is_shutdown = True


def main():
    # Use the custom backend
    bus = MyCustomLin(channel=0, bitrate=19200)
    tp = LinTp(bus, nad=0x01)

    # Simulate an incoming response (e.g., from a slave)
    bus._rx_queue.append(bytes([0x01, 0x02, 0x50, 0x01, 0xFF, 0xFF, 0xFF, 0xFF]))

    # Send a request and receive the simulated response
    tp.send(bytes([0x10, 0x01]))
    rx = tp.recv(timeout=0.5)
    print(rx.hex())   # should print the queued data

    bus.shutdown()

if __name__ == "__main__":
    main()
```

**What you learn:**
- The complete interface a LIN backend must provide.
- How to integrate your custom driver with the transport layer.
- Simulating hardware behaviour for testing or prototyping.
- The importance of proper resource cleanup (`shutdown`).

---

## Summary Table

| Example                       | Complexity | Key Feature                                  |
|-------------------------------|------------|----------------------------------------------|
| `toomoss_example.py`          | ★☆☆☆☆      | Raw frame send                               |
| `vector_example.py`           | ★☆☆☆☆      | Same, different hardware                     |
| `lintp_example.py`            | ★★☆☆☆      | LIN‑TP send/receive                          |
| `uds_example.py`              | ★★★☆☆      | UDS diagnostic over LIN‑TP                   |
| `custom_backend.py`           | ★★★★☆      | Full custom driver + LIN‑TP integration      |

Start with the basic frame send to verify your hardware, then move to transport‑layer communication, add diagnostic services, and finally extend the framework with your own backend when needed.
