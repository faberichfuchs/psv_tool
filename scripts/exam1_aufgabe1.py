"""
Löst Prüfung 1 (June 2023) Aufgabe 1 via Playwright.
Startet die App selbst auf Port 8503 (lässt 8501 unberührt).
Ausführen: python scripts/exam1_aufgabe1.py
"""
import sys, io, time, subprocess, socket
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from playwright.sync_api import sync_playwright

PORT = 8501
URL  = f"http://localhost:{PORT}"

FIB_C = """\
int fib (unsigned n) {
    unsigned a = 0;
    unsigned b = 1;
    unsigned c;
    unsigned i = 2;
    while ((i <= n) || (n == 0)) {
        c = a + b;
        a = b;
        b = c;
        i = i + 1;
        if (n == 0)
            return 0;
    }
    return b;
}"""

TESTS = "fib(0)\nfib(1)"


def start_app():
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.port", str(PORT),
         "--server.headless", "true",
         "--server.fileWatcherType", "none",
         "--logger.level", "error"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print(f"App gestartet (PID {proc.pid}) auf Port {PORT}, warte...")
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with socket.create_connection(("localhost", PORT), timeout=1):
                break
        except OSError:
            time.sleep(0.5)
    else:
        proc.kill()
        raise RuntimeError("App nicht bereit nach 30s")
    time.sleep(1)
    print("App bereit.\n")
    return proc


def wait_idle(page, timeout=90_000):
    try:
        page.wait_for_selector('[data-testid="stStatusWidget"]', timeout=3_000)
    except Exception:
        pass
    try:
        page.wait_for_selector('[data-testid="stStatusWidget"]',
                               state="hidden", timeout=timeout)
    except Exception:
        pass
    time.sleep(0.5)


def streamlit_fill(page, index: int, value: str):
    """Füllt n-te Textarea Streamlit-kompatibel (triggert React onChange)."""
    ta = page.locator("textarea").nth(index)
    ta.scroll_into_view_if_needed()
    ta.click(click_count=3)
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    # press_sequentially triggert onChange zuverlässig
    ta.press_sequentially(value, delay=2)
    ta.press("Tab")   # blur → Streamlit übernimmt Wert
    wait_idle(page, 5_000)


def run():
    proc = start_app()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=80)
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(URL)
            page.wait_for_selector('[data-testid="stApp"]', timeout=15_000)
            wait_idle(page)

            # ── Sprache: C / C++ ─────────────────────────────────────────
            page.get_by_text("C / C++", exact=True).click()
            wait_idle(page)

            # ── Code eingeben ─────────────────────────────────────────────
            print("Eingabe: C-Code...")
            streamlit_fill(page, 0, FIB_C)

            # ── Transpilierter Code sichtbar? ─────────────────────────────
            page.wait_for_selector("text=Transpilierter Python-Code", timeout=10_000)
            transpiled = page.locator("pre code").first.inner_text()
            print("Transpilierter Code:")
            print(transpiled)
            assert "if n == 0:" in transpiled, "FEHLER: if n==0 nicht korrekt transpiliert!"
            assert transpiled.index("return 0") > transpiled.index("if n == 0:"), \
                "FEHLER: return 0 nicht eingerueckt!"
            print("Transpilation OK.\n")

            # ── Testfälle eingeben ────────────────────────────────────────
            print("Eingabe: Testfaelle...")
            streamlit_fill(page, 1, TESTS)
            page.screenshot(path="scripts/01_vor_analysieren.png")

            # ── Analysieren ───────────────────────────────────────────────
            print("Klicke Analysieren...")
            page.get_by_role("button", name="Analysieren").click()
            wait_idle(page, timeout=90_000)
            page.screenshot(path="scripts/02_nach_analysieren.png")

            body = page.inner_text("body")

            # Prüfe ob Analyse lief
            if "Ausführung abgeschlossen" not in body:
                print("WARNUNG: Analysieren lief nicht durch!")
                print("Seiteninhalt (Ausschnitt):", body[:500])
                browser.close()
                return

            print("Analyse OK.\n")

            # ── 1a: Control-Flow Coverage ─────────────────────────────────
            print("=" * 60)
            print("AUFGABE 1a — Control-Flow Coverage (n=0 und n=1)")
            print("=" * 60)
            for crit in ["Statement Coverage", "Branch Coverage", "Decision Coverage", "MC/DC"]:
                idx = body.find(crit)
                if idx >= 0:
                    snippet = body[idx: idx + 120].replace("\n", "  ")
                    print(f"  {snippet}")
                else:
                    print(f"  [{crit} nicht gefunden]")
            print()

            # ── 1b: Data-Flow Coverage ────────────────────────────────────
            print("=" * 60)
            print("AUFGABE 1b — Data-Flow Coverage")
            print("=" * 60)
            idx = body.find("Data-flow Coverage")
            if idx >= 0:
                print(body[idx: idx + 800].strip())
            else:
                print("[Data-flow Coverage nicht gefunden — auto-run fehlgeschlagen?]")
                # Zeige Fehlermeldung falls vorhanden
                idx2 = body.find("Dataflow-Analyse fehlgeschlagen")
                if idx2 >= 0:
                    print("FEHLER:", body[idx2: idx2 + 200])
            print()

            # ── 1c: Minimale Testmenge ────────────────────────────────────
            print("=" * 60)
            print("AUFGABE 1c — all-p-uses/some-c-uses")
            print("=" * 60)
            page.locator('[data-testid="stSelectbox"]').first.click()
            time.sleep(0.5)
            page.get_by_role("option", name="all-p-uses/some-c-uses").click()
            wait_idle(page)
            page.screenshot(path="scripts/03_min_p_uses.png")
            body2 = page.inner_text("body")
            idx = body2.find("Minimale Testmenge")
            if idx >= 0:
                print(body2[idx: idx + 500].strip())
            print()

            print("=" * 60)
            print("AUFGABE 1c — MC/DC (Witnesses via Coverage-Sektion oben)")
            print("=" * 60)
            idx = body2.find("MC/DC")
            if idx >= 0:
                print(body2[idx: idx + 400].strip())
            print()

            # ── 1d: Mutation Testing ──────────────────────────────────────
            print("=" * 60)
            print("AUFGABE 1d — Mutation Testing (i=2 -> i=1)")
            print("=" * 60)
            print("Klicke 'Mutation Score berechnen'...")
            # Zuerst zur Mutation-Sektion scrollen
            mut_btn = page.get_by_role("button", name="Mutation Score berechnen")
            mut_btn.scroll_into_view_if_needed()
            mut_btn.click()
            # Warte explizit bis Spinner erscheint
            try:
                page.wait_for_selector('[data-testid="stStatusWidget"]', timeout=8_000)
                print("  (Spinner sichtbar, berechne Mutanten...)")
            except Exception:
                print("  (Kein Spinner — sofortiges Ergebnis?)")
            # Warte bis Spinner verschwindet
            try:
                page.wait_for_selector('[data-testid="stStatusWidget"]',
                                       state="hidden", timeout=180_000)
                print("  (Spinner weg)")
            except Exception:
                print("  (Timeout beim Warten auf Spinner-Ende)")
            time.sleep(1.5)
            # Expander für Überlebende + Getötete öffnen
            for exp_text in ["Überlebende Mutanten", "Getötete Mutanten"]:
                try:
                    page.get_by_text(exp_text, exact=False).first.click()
                    time.sleep(0.3)
                except Exception:
                    pass
            page.screenshot(path="scripts/04_mutation.png", full_page=True)
            body3 = page.inner_text("body")
            print("\n--- Mutation Section ---")
            idx_mut = body3.find("Mutation Testing")
            if idx_mut >= 0:
                print(body3[idx_mut: idx_mut + 1200].strip())
            else:
                print("[nicht gefunden]")
            print()

            print("=" * 60)
            page.screenshot(path="scripts/05_final.png", full_page=True)
            print("Fertig. Screenshots in scripts/")
            browser.close()
    finally:
        proc.kill()


if __name__ == "__main__":
    run()
