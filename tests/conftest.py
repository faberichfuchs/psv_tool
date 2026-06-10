"""
Pytest fixtures für echte Browser-Tests via Playwright.
Startet die Streamlit-App als subprocess, wartet bis sie bereit ist,
gibt die URL zurück und stoppt den Prozess danach.
"""
import subprocess
import sys
import time
import socket
import pytest


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("localhost", port), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def streamlit_url():
    """Startet streamlit run app.py auf Port 8502 (nicht 8501 um laufende App nicht zu stören)."""
    port = 8502
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.port", str(port),
         "--server.headless", "true",
         "--server.fileWatcherType", "none",  # kein Hot-Reload während Tests
         "--logger.level", "error"],           # weniger Rauschen
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Warten bis Port offen (max 30s)
    deadline = time.time() + 30
    while not _port_open(port):
        if time.time() > deadline:
            proc.kill()
            raise RuntimeError(f"Streamlit auf Port {port} nicht bereit nach 30s")
        time.sleep(0.3)

    yield f"http://localhost:{port}"

    proc.kill()
    proc.wait()
