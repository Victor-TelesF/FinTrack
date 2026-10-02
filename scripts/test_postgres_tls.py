"""Run tests on synthetic PostgreSQL with TLS, without Docker/system installation.

Usage: uv run --locked python -m scripts.test_postgres_tls --pg-bin /path/to/pg/bin
Requires PostgreSQL binaries, their shared libraries and openssl. All keys/data
live in a temporary directory; the server is loopback-only and stopped on exit.
"""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

import httpx
from sqlalchemy import URL, create_engine, inspect


def check_runtime(pg_bin, root, port, url, env, python):
    """Exercise the real API/release scripts with locked, no-dev dependencies."""
    subprocess.run([str(pg_bin / "createdb"), "-h", str(root), "-p", str(port), "-U", "fintrack_tls",
                    "release_test"], check=True, stdout=subprocess.DEVNULL)
    runtime_env = {**env, "POSTGRES_DB": "release_test", "VIRTUAL_ENV": str(python.parent.parent),
                   "PATH": str(python.parent) + os.pathsep + os.environ.get("PATH", "")}
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        api_port = probe.getsockname()[1]
    runtime_env["PORT"] = str(api_port)
    runtime_env["FINTRACK_CHECK_BASE_URL"] = f"http://127.0.0.1:{api_port}"
    engine = create_engine(url.set(database="release_test"))

    def run_api(check):
        log_path = root / "api.log"
        with log_path.open("w") as log:
            process = subprocess.Popen(["/bin/sh", "start.sh"], env=runtime_env, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 20
                with httpx.Client(base_url=runtime_env["FINTRACK_CHECK_BASE_URL"], trust_env=False) as client:
                    while True:
                        if process.poll() is not None:
                            raise RuntimeError("Synthetic API exited before liveness")
                        try:
                            if client.get("/health/live").status_code == 200:
                                break
                        except httpx.HTTPError:
                            pass
                        if time.monotonic() >= deadline:
                            raise RuntimeError("Synthetic API did not become live")
                        time.sleep(0.1)
                check()
            finally:
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise RuntimeError("Synthetic API failed graceful shutdown") from None
        assert "Application shutdown complete" in log_path.read_text()
        assert env["POSTGRES_PASSWORD"] not in log_path.read_text()

    try:
        def before_release():
            assert not inspect(engine).has_table("alembic_version"), "API must not run migrations"

        run_api(before_release)
        subprocess.run(["/bin/sh", "release.sh"], env=runtime_env, check=True)
        run_api(lambda: subprocess.run([str(python), "-m", "scripts.check_release"], env=runtime_env, check=True))
        print("Runtime passed: API without migrations, explicit TLS release, no-dev HTTP flow, graceful shutdown")
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--runtime-python", type=Path, help="Python from a locked --no-dev environment")
    args = parser.parse_args()
    pg_bin = args.pg_bin.resolve()
    for name in ("initdb", "pg_ctl", "createdb"):
        if not (pg_bin / name).is_file():
            parser.error(f"Missing PostgreSQL binary: {name}")
    with TemporaryDirectory(prefix="fintrack-stage1-tls-") as directory:
        root = Path(directory)
        data = root / "data"
        password = "synthetic@:/%?# +secret"
        pwfile = root / "password"
        pwfile.write_text(password + "\n")
        pwfile.chmod(0o600)

        def run(*command, **kwargs):
            # Neither the synthetic password nor a credential URL appears in argv.
            return subprocess.run(command, check=True, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE, text=True, **kwargs)

        for name in ("ca", "wrong-ca"):
            run("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                "-subj", f"/CN=FinTrack synthetic {name}", "-keyout", str(root / f"{name}.key"),
                "-out", str(root / f"{name}.pem"))
        run("openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes", "-subj", "/CN=localhost",
            "-keyout", str(root / "server.key"), "-out", str(root / "server.csr"))
        extensions = root / "server.ext"
        extensions.write_text("subjectAltName=DNS:localhost\nextendedKeyUsage=serverAuth\n")
        run("openssl", "x509", "-req", "-in", str(root / "server.csr"), "-CA", str(root / "ca.pem"),
            "-CAkey", str(root / "ca.key"), "-CAcreateserial", "-days", "1", "-extfile", str(extensions),
            "-out", str(root / "server.pem"))
        (root / "server.key").chmod(0o600)
        run(str(pg_bin / "initdb"), "-D", str(data), "--username=fintrack_tls", "--pwfile", str(pwfile),
            "--auth-local=trust", "--auth-host=scram-sha-256", "--no-locale", "--encoding=UTF8")
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        with (data / "postgresql.conf").open("a") as config:
            config.write(
                f"\nlisten_addresses = '127.0.0.1'\nport = {port}\n"
                f"unix_socket_directories = '{root}'\nssl = on\n"
                f"ssl_cert_file = '{root / 'server.pem'}'\nssl_key_file = '{root / 'server.key'}'\n"
            )
        # Require TLS for TCP, not just availability of TLS.
        (data / "pg_hba.conf").write_text(
            "local all all trust\nhostssl all all 127.0.0.1/32 scram-sha-256\n"
            "hostnossl all all 127.0.0.1/32 reject\n"
        )
        started = False
        try:
            run(str(pg_bin / "pg_ctl"), "-D", str(data), "-l", str(root / "server.log"), "-w", "start")
            started = True
            run(str(pg_bin / "createdb"), "-h", str(root), "-p", str(port), "-U", "fintrack_tls",
                "fintrack_stage1_test")
            url = URL.create("postgresql+psycopg", username="fintrack_tls", password=password,
                             host="localhost", port=port, database="fintrack_stage1_test",
                             query={"sslmode": "verify-full", "sslrootcert": str(root / "ca.pem")})
            env = {**os.environ,
                   "POSTGRES_USER": "fintrack_tls", "POSTGRES_PASSWORD": password,
                   "POSTGRES_HOST": "localhost", "POSTGRES_PORT": str(port),
                   "POSTGRES_DB": "fintrack_stage1_test", "DATABASE_URL": "",
                   "DATABASE_SSLMODE": "verify-full", "DATABASE_SSLROOTCERT": str(root / "ca.pem"),
                   "SECRET_KEY": "synthetic", "ALGORITHM": "HS256", "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
                   "ADMIN_KEY": "synthetic", "BRAPI_TOKEN": "",
                   "FINTRACK_TLS_TEST_URL": url.render_as_string(hide_password=False),
                   "FINTRACK_TLS_WRONG_CA": str(root / "wrong-ca.pem")}
            result = subprocess.run([sys.executable, "-m", "pytest", "-q"], env=env)
            if result.returncode == 0 and args.runtime_python:
                # Preserve the venv path: resolving this symlink selects base Python.
                check_runtime(pg_bin, root, port, url, env, args.runtime_python.absolute())
            return result.returncode
        finally:
            if started:
                run(str(pg_bin / "pg_ctl"), "-D", str(data), "-m", "fast", "-w", "stop")


if __name__ == "__main__":
    raise SystemExit(main())
