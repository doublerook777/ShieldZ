"""Run the api with N worker processes: `python -m shieldz.service.serve` (SHIELDZ_WORKERS=N).

uvicorn's own `--workers` added ~40 ms to every keep-alive request in our tests (Nagle waiting for
the client's delayed ACK). Here the parent opens one listening socket with TCP_NODELAY, which
accepted connections inherit, and forks workers that share it. State shared between workers
(history, outbox, pepper) lives in SQLite / files and is safe across processes.
"""

from __future__ import annotations

import multiprocessing as mp
import os
import signal
import socket
import sys

import uvicorn

HOST = "127.0.0.1"  # host network: never 0.0.0.0 (runbook §5, ADR D8)
PORT = 8000


def listen_socket(host: str = HOST, port: int = PORT) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.bind((host, port))
    sock.listen(1024)
    sock.set_inheritable(True)
    return sock


def _serve(sock: socket.socket) -> None:
    config = uvicorn.Config(
        "shieldz.service.app:create_app", factory=True, access_log=False, log_level="warning"
    )
    uvicorn.Server(config).run(sockets=[sock])


def main() -> int:
    workers = max(1, int(os.environ.get("SHIELDZ_WORKERS", "1")))
    sock = listen_socket()
    if workers == 1:
        _serve(sock)
        return 0
    ctx = mp.get_context("fork")
    procs = [ctx.Process(target=_serve, args=(sock,), daemon=True) for _ in range(workers)]
    for p in procs:
        p.start()

    def stop(*_):
        for p in procs:
            if p.is_alive():
                p.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    for p in procs:
        p.join()
    return 0 if all(p.exitcode in (0, -signal.SIGTERM) for p in procs) else 1


if __name__ == "__main__":
    sys.exit(main())
