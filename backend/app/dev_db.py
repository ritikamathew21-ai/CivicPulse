"""Runs a local PostgreSQL from the pgserver package's binaries, so nothing has to be installed.

pgserver's own launcher is not used: it logs inside the data folder, which on Windows blocks
crash recovery for 30 s, and it gives up after 10 s.
"""

import subprocess
from pathlib import Path

PORT = 54329
START_TIMEOUT_S = 90


def ensure_running() -> str:
    from pgserver._commands import POSTGRES_BIN_PATH

    home = Path.home() / ".civicpulse"
    data, log = home / "pgdata", home / "postgres.log"
    home.mkdir(exist_ok=True)

    def run(program: str, *args: str) -> subprocess.CompletedProcess:
        # The server inherits these handles, so a pipe here would never close
        return subprocess.run(
            [str(POSTGRES_BIN_PATH / program), "-D", str(data), *args],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    if not (data / "PG_VERSION").exists():
        run("initdb", "-U", "postgres", "--auth=trust", "--encoding=utf8").check_returncode()
    if run("pg_ctl", "status").returncode != 0:
        started = run(
            "pg_ctl", "-w", "-t", str(START_TIMEOUT_S), "-l", str(log),
            "-o", f"-h 127.0.0.1 -p {PORT}", "start",
        )
        if started.returncode != 0:
            raise RuntimeError(f"Local PostgreSQL did not start, see {log}")
    return f"postgresql://postgres@127.0.0.1:{PORT}/postgres"
