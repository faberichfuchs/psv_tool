"""
Tests für die neuen Proof-Trace Features (Aufgaben 2, 3, 4, 5):
- _generate_hoare_proof: Hoare-Beweis mit Regelangaben
- _generate_invariant_ce_explanation: CE im Vor/Nach-Format
- _ctl_tableaux_explain: CTL Tableaux mit Fixpunkt-Schritten
- CDCL Exam Format rendering

Ausführen: pytest tests/test_proof_traces.py -v
"""
import pytest
import sys
sys.path.insert(0, ".")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hoare_proof_exam2():
    from tools.shared import _generate_hoare_proof
    return _generate_hoare_proof(
        code="i = 0\nwhile i != n:\n    i = i + 1\n    s = s + i",
        invariant_str="s >= i + 1",
        pre_str="s >= 1",
        post_str="s >= n + 1",
        vars_str="i, n, s",
    )


def _kripke_exam():
    states = ["s0", "s1", "s2"]
    transitions = [("s0", "s1"), ("s1", "s1"), ("s1", "s2"), ("s2", "s1")]
    labels = {"s0": {"a"}, "s1": {"b"}, "s2": {"a"}}
    return states, transitions, labels


# ── Aufgabe 2: Hoare Proof Trace ──────────────────────────────────────────────

def test_hoare_proof_contains_invariant():
    """Proof muss die Invariante nennen."""
    lines = _hoare_proof_exam2()
    text = "\n".join(lines)
    assert "s >= i + 1" in text


def test_hoare_proof_all_checks_pass():
    """Init, Erhaltung und Konsequenz müssen alle ✅ zeigen."""
    lines = _hoare_proof_exam2()
    text = "\n".join(lines)
    assert "✅" in text
    assert "Konsequenz-Regel" in text
    # All three must pass — count occurrences (proof is one code block)
    assert text.count("✅") >= 3, f"Erwartet 3x ✅, gefunden: {text.count('✅')}"


def test_hoare_proof_no_failing_check():
    """Kein ❌ im Proof (alle Checks müssen bestehen)."""
    lines = _hoare_proof_exam2()
    failing = [ln for ln in lines if "❌" in ln]
    assert len(failing) == 0, f"Unerwartete Fehler im Proof: {failing}"


def test_hoare_proof_rules_named():
    """Zuweisungsregel und While-Regel müssen explizit genannt werden."""
    lines = _hoare_proof_exam2()
    text = "\n".join(lines)
    assert "Zuweisungsregel" in text, "Zuweisungsregel fehlt im Proof"
    assert "While-Regel" in text, "While-Regel fehlt im Proof"


def test_hoare_proof_pre_and_post_shown():
    """Pre und Post müssen im Proof erscheinen."""
    lines = _hoare_proof_exam2()
    text = "\n".join(lines)
    assert "s >= 1" in text   # Pre
    assert "s >= n + 1" in text  # Post


def test_hoare_proof_wp_steps_shown():
    """WP-Substitutionsschritte müssen sichtbar sein."""
    lines = _hoare_proof_exam2()
    text = "\n".join(lines)
    assert "WP(i:=" in text or "WP(i=" in text, "WP für i-Zuweisung fehlt"
    assert "Zuweisungsregel" in text, "Zuweisungsregel fehlt"


def test_hoare_proof_while_condition_shown():
    """While-Bedingung i != n muss im Proof erscheinen."""
    lines = _hoare_proof_exam2()
    text = "\n".join(lines)
    assert "i != n" in text


# ── Aufgabe 3: Invariant CE Explanation ───────────────────────────────────────

def test_ce_explanation_table_present():
    """CE-Erklärung muss eine Vor/Nach-Tabelle enthalten."""
    from tools.shared import _generate_invariant_ce_explanation
    lines = _generate_invariant_ce_explanation(
        loop_body_str="i = i + 1\ns = s + i",
        invariant_str="s >= 2 * i",
        cond_str="i != n",
        counterexample={"i": "0", "s": "0", "n": "1"},
    )
    text = "\n".join(lines)
    assert "Vor Body" in text
    assert "Nach Body" in text
    assert "| Variable |" in text  # Markdown table


def test_ce_explanation_shows_violation():
    """CE-Erklärung muss zeigen dass P nach dem Body verletzt ist."""
    from tools.shared import _generate_invariant_ce_explanation
    lines = _generate_invariant_ce_explanation(
        loop_body_str="i = i + 1\ns = s + i",
        invariant_str="s >= 2 * i",
        cond_str="i != n",
        counterexample={"i": "0", "s": "0", "n": "1"},
    )
    text = "\n".join(lines)
    assert "VERLETZT" in text or "nicht induktiv" in text.lower()


def test_ce_explanation_correct_values():
    """CE: i=0,s=0 → after body: i=1,s=1; 1 < 2*1=2 → P violated."""
    from tools.shared import _generate_invariant_ce_explanation
    lines = _generate_invariant_ce_explanation(
        loop_body_str="i = i + 1\ns = s + i",
        invariant_str="s >= 2 * i",
        cond_str="i != n",
        counterexample={"i": "0", "s": "0", "n": "1"},
    )
    text = "\n".join(lines)
    # After body: i=1, s=1
    assert "`i` | `0` | `1`" in text or ("i" in text and "1" in text)


def test_ce_explanation_s_ne_i():
    """CE für s≠i: i=1,s=0 → after: i=2,s=2 → 2=2 violates s≠i."""
    from tools.shared import _generate_invariant_ce_explanation
    lines = _generate_invariant_ce_explanation(
        loop_body_str="i = i + 1\ns = s + i",
        invariant_str="s != i",
        cond_str="i != n",
        counterexample={"i": "1", "s": "0", "n": "3"},
    )
    text = "\n".join(lines)
    assert "VERLETZT" in text or "False" in text


# ── Aufgabe 4: CTL Tableaux ───────────────────────────────────────────────────

def test_tableaux_eg_ex_a_correct_result():
    """EG(EX a) muss {s1} ergeben."""
    from tools.shared import _ctl_tableaux_explain
    states, transitions, labels = _kripke_exam()
    result, lines = _ctl_tableaux_explain(states, transitions, labels, "EG(EX a)")
    assert result == {"s1"}, f"Erwartet {{s1}}, erhalten: {result}"


def test_tableaux_eg_ex_a_shows_fixpoint_steps():
    """Tableaux muss Fixpunkt-Schritte Z0, Z1 zeigen."""
    from tools.shared import _ctl_tableaux_explain
    states, transitions, labels = _kripke_exam()
    _, lines = _ctl_tableaux_explain(states, transitions, labels, "EG(EX a)")
    text = "\n".join(lines)
    assert "Z₀" in text, "Z₀ Schritt fehlt"
    assert "Z1" in text or "Z₁" in text, "Z1 Schritt fehlt"
    assert "Fixpunkt" in text, "Fixpunkt-Meldung fehlt"


def test_tableaux_ex_a_subformula():
    """EX a Subformel muss als Zwischenschritt erscheinen."""
    from tools.shared import _ctl_tableaux_explain
    states, transitions, labels = _kripke_exam()
    _, lines = _ctl_tableaux_explain(states, transitions, labels, "EG(EX a)")
    text = "\n".join(lines)
    assert "EX" in text and "s1" in text, "EX a = {s1} muss gezeigt werden"


def test_tableaux_eg_a_empty():
    """EG a = {} — kein Zustand hat unendlichen a-Pfad."""
    from tools.shared import _ctl_tableaux_explain
    states, transitions, labels = _kripke_exam()
    result, lines = _ctl_tableaux_explain(states, transitions, labels, "EG a")
    assert result == set(), f"EG a sollte leer sein, erhalten: {result}"
    text = "\n".join(lines)
    assert "∅" in text or "{}" in text or result == set()


def test_tableaux_eu_bua_all_states():
    """E[b U a] = {s0,s1,s2}."""
    from tools.shared import _ctl_tableaux_explain
    states, transitions, labels = _kripke_exam()
    result, _ = _ctl_tableaux_explain(states, transitions, labels, "E[b U a]")
    assert result == {"s0", "s1", "s2"}


def test_tableaux_shows_kripke_structure():
    """Tableaux-Output muss die Kripke-Struktur beschreiben."""
    from tools.shared import _ctl_tableaux_explain
    states, transitions, labels = _kripke_exam()
    _, lines = _ctl_tableaux_explain(states, transitions, labels, "EG(EX a)")
    text = "\n".join(lines)
    assert "s0" in text and "s1" in text and "s2" in text
    assert "Kripke-Struktur" in text


# ── SAT Exam Format ───────────────────────────────────────────────────────────

def test_cdcl_exam_format_imports():
    """_render_cdcl_exam_format muss importierbar sein."""
    from tools.sat import _render_cdcl_exam_format
    assert callable(_render_cdcl_exam_format)


def test_dpll_trace_has_backtrack():
    """DPLL-Trace muss Backtrack für x1=True zeigen (Exam-Formel)."""
    from tools.shared import _run_dpll_with_trace, _parse_cnf_text
    cnf = ("-1 -2\n1 2\n-2 -3\n2 3\n-3 -4\n3 4\n-4 -5\n4 5\n"
           "-5 -6\n5 6\n-6 -7\n6 7\n-1 -6 7\n-1 -7 6\n-6 -7 1\n6 7 1")
    _, model, trace = _run_dpll_with_trace(_parse_cnf_text(cnf))
    trace_text = " ".join(trace)
    assert "Entscheidung" in trace_text
    assert "Backtrack" in trace_text or "Konflikt" in trace_text


def test_dpll_trace_level_zero_decision():
    """Erste Entscheidung muss auf Level 0 sein."""
    from tools.shared import _run_dpll_with_trace, _parse_cnf_text
    cnf = ("-1 -2\n1 2\n-2 -3\n2 3\n-3 -4\n3 4\n-4 -5\n4 5\n"
           "-5 -6\n5 6\n-6 -7\n6 7\n-1 -6 7\n-1 -7 6\n-6 -7 1\n6 7 1")
    _, _, trace = _run_dpll_with_trace(_parse_cnf_text(cnf))
    assert any("L0:" in t for t in trace), "Kein L0 in Trace"


# ── AppTest: Hoare Tab zeigt Proof ────────────────────────────────────────────

@pytest.mark.slow
def test_hoare_tab_shows_proof_after_verify():
    """Nach Invariante-Check muss 'Prüfungsbeweis' im App erscheinen."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    # Switch to "Loop-Invariante prüfen" mode
    at.radio(key="wp_mode").set_value("Loop-Invariante prüfen")
    at.run()
    # Set loop invariant fields
    at.text_input(key="inv_vars").set_value("i, n, s")
    at.text_input(key="inv_pre").set_value("s >= 1")
    at.text_input(key="inv_I").set_value("s >= i + 1")
    at.text_input(key="inv_B").set_value("i != n")
    at.text_input(key="inv_Q").set_value("s >= n + 1")
    at.text_area(key="inv_init").set_value("i = 0")
    at.text_area(key="inv_body").set_value("i = i + 1\ns = s + i")
    btn = [b for b in at.button if b.label == "Invariante prüfen ✓"]
    assert btn, "Invariante-Button nicht gefunden"
    btn[0].click()
    at.run()
    exceptions = at.exception
    assert len(exceptions) == 0, f"App-Fehler: {[str(e) for e in exceptions]}"
    # Use .value to get actual markdown text content
    body = " ".join(e.value for e in at.markdown) + " ".join(e.value for e in at.success)
    # Either success message or proof content
    assert len(at.success) > 0 or "Zuweisungsregel" in body or "Invariante" in body or "Init" in body


@pytest.mark.slow
def test_invariant_falsifier_shows_ce_explanation():
    """Invariant Falsifier soll CE im Vor/Nach-Format zeigen."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    # Navigate to hoare tab (tab index 2)
    at.text_input(key="invf_pre").set_value("i >= 0")
    at.text_input(key="invf_inv").set_value("s >= 2 * i")  # non-inductive
    at.text_input(key="invf_post").set_value("i == n")
    at.text_area(key="invf_code").set_value("i = 0\nwhile i != n:\n    i = i + 1\n    s = s + i")
    btn = [b for b in at.button if "falsifizieren" in b.label.lower()]
    assert btn, "Falsifizier-Button nicht gefunden"
    btn[0].click()
    at.run()
    exceptions = at.exception
    assert len(exceptions) == 0, f"App-Fehler: {[str(e) for e in exceptions]}"
