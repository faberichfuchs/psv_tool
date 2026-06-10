"""
Echte Browser-Tests via Playwright + Chromium.
Starten die App wirklich, klicken echte Buttons, prüfen echten DOM.

Ausführen: pytest tests/test_browser.py -v --headed   (mit sichtbarem Browser)
           pytest tests/test_browser.py -v             (headless)
"""
import pytest
from playwright.sync_api import Page, expect

TIMEOUT = 60_000  # ms — Analysieren kann 5-10s dauern

FIB_PY = (
    "def fib(n):\n"
    "    a, b, i = 0, 1, 2\n"
    "    while (i <= n) or (n == 0):\n"
    "        c = a + b\n"
    "        a = b\n"
    "        b = c\n"
    "        i += 1\n"
    "        if n == 0:\n"
    "            return 0\n"
    "    return b"
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _go(page: Page, url: str):
    page.goto(url)
    # Warten bis Streamlit vollständig geladen (kein Spinner mehr)
    page.wait_for_selector('[data-testid="stApp"]', timeout=15_000)
    page.wait_for_load_state("networkidle", timeout=15_000)


def _set_textarea(page: Page, label_text: str, value: str):
    """Findet Textarea per Label-Text und setzt Wert."""
    ta = page.locator(f'textarea').filter(
        has=page.locator(f':scope')
    )
    # Streamlit Textareas haben aria-label oder werden via Label gefunden
    field = page.get_by_label(label_text).first
    field.click()
    field.select_all()
    field.type(value)


def _click_analysieren(page: Page):
    page.get_by_role("button", name="Analysieren").click()
    # Warten bis Streamlit fertig ist (kein Spinner / "Running" mehr)
    page.wait_for_selector('[data-testid="stStatusWidget"]', timeout=2_000, state="detached")
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.slow
def test_app_loads_in_browser(page: Page, streamlit_url: str):
    """App öffnet sich im echten Browser ohne Fehler."""
    _go(page, streamlit_url)
    expect(page.get_by_text("Coverage Analyzer")).to_be_visible(timeout=10_000)


@pytest.mark.slow
def test_five_tabs_in_browser(page: Page, streamlit_url: str):
    """Alle 5 Tabs sind im echten DOM sichtbar."""
    _go(page, streamlit_url)
    expect(page.get_by_role("tab", name="Coverage")).to_be_visible()
    expect(page.get_by_role("tab", name="SAT")).to_be_visible()
    expect(page.get_by_role("tab", name="Hoare")).to_be_visible()
    expect(page.get_by_role("tab", name="Temporal")).to_be_visible()


@pytest.mark.slow
def test_analysieren_shows_statement_coverage(page: Page, streamlit_url: str):
    """Nach Analysieren: Statement Coverage Metrik erscheint im echten Browser."""
    _go(page, streamlit_url)

    # Python-Code eingeben
    code = "def fib(n):\n    a, b, i = 0, 1, 2\n    while (i <= n) or (n == 0):\n        c = a + b\n        a = b\n        b = c\n        i += 1\n        if n == 0:\n            return 0\n    return b"
    page.get_by_label("Python-Code").fill(code)

    # Testfälle eingeben
    page.get_by_label("Testfälle", exact=True).fill("fib(0)\nfib(1)")

    # Analysieren klicken
    page.get_by_role("button", name="Analysieren").click()

    # Warten bis Ergebnis sichtbar (stMetric um Checklist-<strong> auszuschließen)
    expect(page.locator('[data-testid="stMetric"]').filter(has_text="Statement Coverage")).to_be_visible(timeout=TIMEOUT)
    expect(page.get_by_text("Ausführung abgeschlossen")).to_be_visible(timeout=TIMEOUT)


@pytest.mark.slow
def test_analysieren_shows_dataflow(page: Page, streamlit_url: str):
    """Nach Analysieren: Data-flow Coverage Section erscheint mit echten Daten."""
    _go(page, streamlit_url)

    code = "def fib(n):\n    a, b, i = 0, 1, 2\n    while (i <= n) or (n == 0):\n        c = a + b\n        a = b\n        b = c\n        i += 1\n        if n == 0:\n            return 0\n    return b"
    page.get_by_label("Python-Code").fill(code)
    page.get_by_label("Testfälle", exact=True).fill("fib(0)\nfib(1)")
    page.get_by_role("button", name="Analysieren").click()

    # Data-flow Header muss erscheinen
    expect(page.get_by_text("Data-flow Coverage")).to_be_visible(timeout=TIMEOUT)

    # Darf NICHT den "noch nicht berechnet"-Hinweis zeigen
    not_computed_msg = page.get_by_text("Führe zuerst oben Analysieren aus")
    expect(not_computed_msg).not_to_be_visible(timeout=5_000)


@pytest.mark.slow
def test_analysieren_shows_reachability(page: Page, streamlit_url: str):
    """Nach Analysieren: Reachability zeigt Metriken, nicht den Placeholder."""
    _go(page, streamlit_url)

    code = "def fib(n):\n    a, b, i = 0, 1, 2\n    while (i <= n) or (n == 0):\n        c = a + b\n        a = b\n        b = c\n        i += 1\n        if n == 0:\n            return 0\n    return b"
    page.get_by_label("Python-Code").fill(code)
    page.get_by_label("Testfälle", exact=True).fill("fib(0)\nfib(1)")
    page.get_by_role("button", name="Analysieren").click()

    # "Erreichbare Zeilen" Metrik muss sichtbar sein (exact=True verhindert Match auf "Unerreichbare Zeilen")
    expect(page.get_by_text("Erreichbare Zeilen", exact=True)).to_be_visible(timeout=TIMEOUT)

    # Placeholder darf nicht mehr da sein
    expect(page.get_by_text("Wird nach Analysieren automatisch berechnet")).not_to_be_visible()


@pytest.mark.slow
def test_branch_coverage_metric_shown(page: Page, streamlit_url: str):
    """Bug 1: Branch Coverage muss als eigene Metrik (mit %) erscheinen, nicht nur als Rohliste."""
    _go(page, streamlit_url)
    page.get_by_label("Python-Code").fill(FIB_PY)
    page.get_by_label("Testfälle", exact=True).fill("fib(0)\nfib(1)")
    page.get_by_role("button", name="Analysieren").click()
    expect(page.get_by_text("Ausführung abgeschlossen")).to_be_visible(timeout=TIMEOUT)
    # Branch Coverage muss als stMetric-Widget erscheinen (nicht nur als Text im Expander)
    branch_section = page.locator('[data-testid="stMetric"]').filter(has_text="Branch Coverage")
    expect(branch_section).to_be_visible(timeout=10_000)


@pytest.mark.slow
def test_existing_tests_prepopulated_after_analyse(page: Page, streamlit_url: str):
    """Bug 2: Nach Analysieren soll 'Bestehende Testfälle' mit den Testfällen vorbelegt sein."""
    _go(page, streamlit_url)
    page.get_by_label("Python-Code").fill(FIB_PY)
    page.get_by_label("Testfälle", exact=True).fill("fib(0)\nfib(1)")
    page.get_by_role("button", name="Analysieren").click()
    expect(page.get_by_text("Ausführung abgeschlossen")).to_be_visible(timeout=TIMEOUT)
    # Minimale Testmenge: Bestehende Tests dürfen NICHT 0 Obligationen decken
    # (wenn richtig vorbelegt, zeigt die App "fib(0), fib(1) decken X/Y Obligationen" mit X > 0)
    body = page.inner_text("body")
    # Muss "fib(0), fib(1)" im Bestehende-Testfälle-Kontext erscheinen
    assert "fib(0)" in body and "fib(1)" in body, "Testfälle nicht in Bestehende Testfälle übernommen"
    # NICHT "decken 0/" — das wäre der Bug
    minimale_idx = body.find("Bestehende Testfälle")
    if minimale_idx >= 0:
        snippet = body[minimale_idx: minimale_idx + 200]
        assert "decken 0/" not in snippet, \
            f"Bug 2 noch aktiv: Bestehende Testfälle zeigt 0 Obligationen. Snippet: {snippet}"


@pytest.mark.slow
def test_c_code_transpilation_visible(page: Page, streamlit_url: str):
    """C-Code eingeben → Transpilierter Code erscheint im echten Browser."""
    _go(page, streamlit_url)

    # Auf C / C++ umschalten (Radio-Inputs sind hidden, Label-Text klicken)
    page.locator("label").filter(has_text="C / C++").click()
    page.wait_for_load_state("networkidle", timeout=5_000)

    fib_c = "int fib(unsigned n) {\n    unsigned a=0;\n    unsigned b=1;\n    unsigned c;\n    unsigned i=2;\n    while((i<=n)||(n==0)) {\n        c =a+b;\n        a =b;\n        b =c;\n        i =i+1;\n        if(n==0) { return 0; }\n    }\n    return b;\n}"
    page.get_by_label("C-Code").fill(fib_c)
    page.get_by_label("C-Code").press("Tab")  # blur → Streamlit onChange
    page.wait_for_load_state("networkidle", timeout=10_000)

    # Transpilierter Code Expander muss erscheinen
    expect(page.get_by_text("Transpilierter Python-Code")).to_be_visible(timeout=10_000)
    expect(page.get_by_text("def fib")).to_be_visible(timeout=5_000)
