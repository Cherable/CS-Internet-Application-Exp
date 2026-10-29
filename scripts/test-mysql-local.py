r"""Run tests against a disposable loopback-only MySQL, without touching installed services.

Usage: .venv\Scripts\python.exe scripts/test-mysql-local.py --mysqld PATH
Requires mysqlclient and a MySQL server binary. No credentials are saved.
"""
import argparse
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time

import MySQLdb


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mysqld", default=shutil.which("mysqld"))
    parser.add_argument("--port", type=int, default=13316)
    args = parser.parse_args()
    if not args.mysqld:
        parser.error("Provide --mysqld with the installed MySQL server executable")
    # Refuse an occupied port before starting, never authenticate to a user's service.
    with socket.socket() as port_check:
        port_check.bind(("127.0.0.1", args.port))
    root = Path(__file__).resolve().parent.parent
    # MySQL for Windows may mishandle non-ASCII data paths; use the OS temp directory.
    temporary = Path(tempfile.mkdtemp(prefix="orangible-mysql-test-"))
    data = temporary / "data"
    data.mkdir()
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    server = conn = None
    code = 1
    try:
        initialized = subprocess.run([args.mysqld, "--no-defaults", "--initialize-insecure",
            f"--datadir={data}", "--console"], capture_output=True, creationflags=flags)
        if initialized.returncode:
            raise RuntimeError(initialized.stderr.decode(errors="replace"))
        with (temporary / "server.log").open("w") as log:
            server = subprocess.Popen([args.mysqld, "--no-defaults", f"--datadir={data}",
                "--bind-address=127.0.0.1", f"--port={args.port}", "--mysqlx=OFF",
                "--skip-log-bin", "--console"], stdout=log, stderr=log, creationflags=flags)
            for _ in range(60):
                if server.poll() is not None:
                    raise RuntimeError((temporary / "server.log").read_text(errors="replace"))
                try:
                    candidate = MySQLdb.connect(host="127.0.0.1", port=args.port, user="root")
                    cursor = candidate.cursor()
                    cursor.execute("SELECT @@datadir")
                    actual_data = Path(cursor.fetchone()[0]).resolve()
                    if actual_data != data.resolve():
                        candidate.close()
                        raise RuntimeError("Refusing a MySQL instance with an unexpected data directory")
                    conn = candidate
                    break
                except MySQLdb.OperationalError:
                    time.sleep(0.25)
            if conn is None:
                raise RuntimeError("MySQL startup timed out")
            password = secrets.token_urlsafe(32)
            cursor = conn.cursor()
            cursor.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s", (password,))
            cursor.execute("CREATE DATABASE campus_shop CHARACTER SET utf8mb4")
            version = conn.get_server_info()
            env = os.environ.copy()
            env.update(DB_ENGINE="mysql", MYSQL_DATABASE="campus_shop", MYSQL_USER="root",
                       MYSQL_PASSWORD=password, MYSQL_HOST="127.0.0.1", MYSQL_PORT=str(args.port),
                       DJANGO_DEBUG="true", PYTHONIOENCODING="utf-8")
            result = subprocess.run([sys.executable, "manage.py", "test", "--verbosity", "2", "--noinput"],
                cwd=root, env=env, capture_output=True, text=True, encoding="utf-8")
            evidence = root / "docs/stages/stage-02/mysql-test-results.txt"
            evidence.parent.mkdir(parents=True, exist_ok=True)
            evidence.write_text(f"Disposable local MySQL {version}; loopback only; no existing service used.\n"
                                + result.stdout + result.stderr, encoding="utf-8")
            print(result.stdout + result.stderr)
            code = result.returncode
    finally:
        if conn:
            try:
                conn.cursor().execute("SHUTDOWN")
            finally:
                conn.close()
        if server:
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.terminate()
                server.wait(timeout=10)
        # Only remove the unique temporary directory created above, never user data.
        if temporary.parent.resolve() == Path(tempfile.gettempdir()).resolve() and temporary.name.startswith("orangible-mysql-test-"):
            shutil.rmtree(temporary)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
