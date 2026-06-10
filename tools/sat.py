"""
Tab 1 — SAT / Z3 Solver
"""

import traceback

import streamlit as st

from tools.shared import (
    _euf_parse_constraints,
    _euf_congruence_closure,
    _euf_term_to_str,
    _parse_cnf_text,
    _run_dpll_with_trace,
    _find_smt_model,
    _analyze_unsat_core,
    _eliminate_quantifiers,
    _check_equivalence,
)


def _render_cdcl_exam_format(sat_result, model, trace, clauses):
    """Render DPLL trace in CDCL exam style with decisions, UP chains, conflicts."""
    import re

    lit_fmt = lambda l: f"¬x{abs(l)}" if l < 0 else f"x{abs(l)}"

    # Group trace by decision level
    level_blocks = []
    cur_level = None
    cur_block = []
    for step in trace:
        m = re.match(r"L(\d+): (.+)", step)
        if m:
            lvl = int(m.group(1))
            msg = m.group(2)
            if lvl != cur_level:
                if cur_block:
                    level_blocks.append((cur_level, cur_block))
                cur_level = lvl
                cur_block = []
            cur_block.append(msg)
    if cur_block:
        level_blocks.append((cur_level, cur_block))

    st.markdown("**Klauseln:**")
    for c in clauses:
        st.markdown("  " + " ∨ ".join(lit_fmt(l) for l in c))

    st.markdown("")
    for lvl, msgs in level_blocks:
        decisions   = [m for m in msgs if m.startswith("Entscheidung")]
        ups         = [m for m in msgs if "Unit Propagation" in m]
        conflicts   = [m for m in msgs if "Konflikt" in m]
        backtracks  = [m for m in msgs if "Backtrack" in m]
        satisfied   = [m for m in msgs if "erfüllt" in m]

        st.markdown(f"**Entscheidungsebene {lvl}:**")
        for d in decisions:
            var_match = re.search(r"x(\d+)=(\w+)", d)
            if var_match:
                st.markdown(f"- Entscheidung: **x{var_match.group(1)} = {var_match.group(2)}**")
        if ups:
            st.markdown("- Unit Propagation:")
            for u in ups:
                m2 = re.search(r"setzt x(\d+)=(\w+)", u)
                if m2:
                    st.markdown(f"  - x{m2.group(1)} = {m2.group(2)}")
        for c in conflicts:
            st.markdown(f"- ❌ **Konflikt:** {c}")
            # Show which assignment caused it
            st.markdown("  → Backtrack zur letzten Entscheidung")
        for b in backtracks:
            st.markdown(f"- ↩️ {b}")
        for s in satisfied:
            st.markdown(f"- ✅ {s}")
        st.markdown("")

    if sat_result and model:
        st.markdown("**Erfüllende Belegung:**")
        cols = st.columns(min(len(model), 7))
        for i, (var, val) in enumerate(sorted(model.items())):
            with cols[i % len(cols)]:
                st.markdown(f"x{var} = **{'T' if val else 'F'}**")
        st.markdown("")
        # Count satisfying assignments note
        st.caption("Anzahl der erfüllenden Belegungen: mit DPLL-Enumeration bestimmbar "
                   "(hier nur 1 Lösung gezeigt).")
    elif not sat_result:
        st.markdown("**UNSAT** — kein Konfliktgraph darstellbar (DPLL-Trace oben zeigt alle Entscheidungsebenen).")


def render():
    st.header("SAT / Z3 Solver")
    st.caption("Löst SAT-Probleme, überprüft Formeln, macht EUF-Checks. Deterministisch — kein LLM.")

    solver_mode = st.radio(
        "Modus",
        [
            "SAT (Propositionale Logik)",
            "SMT / EUF (Gleichungslogik)",
            "CDCL-Trace simulieren",
            "Bounded Model Checking (Safety)",
        ],
    )

    if solver_mode == "SAT (Propositionale Logik)":
        st.markdown("""**Eingabe:** Python-Ausdrücke mit `z3`-Variablen.
Beispiel: `Or(And(p, q), Not(r))`""")

        vars_input = st.text_input("Variablen (kommagetrennt)", value="p, q, r")
        formula_input = st.text_area("Formel (z3-Syntax)", height=100,
                                      placeholder="Or(And(p, q), Not(r))")

        if st.button("Lösen (SAT)", type="primary"):
            try:
                from z3 import Bool, And, Or, Not, Implies, Xor, Solver, sat, unsat, BoolVal

                vars_dict = {}
                for v in vars_input.split(","):
                    v = v.strip()
                    if v:
                        vars_dict[v] = Bool(v)

                formula = eval(formula_input, {**vars_dict, "And": And, "Or": Or,
                                               "Not": Not, "Implies": Implies,
                                               "Xor": Xor, "True": BoolVal(True),
                                               "False": BoolVal(False)})
                s = Solver()
                s.add(formula)
                result = s.check()

                if result == sat:
                    st.success("✅ SATISFIABLE")
                    m = s.model()
                    st.subheader("Modell (erfüllende Belegung):")
                    for var_name, var_ref in vars_dict.items():
                        val = m.eval(var_ref)
                        st.write(f"  `{var_name}` = `{val}`")
                elif result == unsat:
                    st.error("❌ UNSATISFIABLE")
                else:
                    st.warning("UNKNOWN")

                from z3 import Not as Z3Not
                s2 = Solver()
                s2.add(Z3Not(formula))
                if s2.check() == unsat:
                    st.info("🔁 Die Formel ist eine **Tautologie** (immer wahr).")

            except Exception as e:
                st.error(f"Fehler: {e}")

    elif solver_mode == "SMT / EUF (Gleichungslogik)":
        st.markdown("""**EUF-Checks:** Überprüfe ob eine Menge von Gleichungen/Ungleichungen erfüllbar ist.
Beispiel: `x == f(y), y == z, f(z) != x`""")

        euf_input = st.text_area("Constraints (eine pro Zeile, Python-Syntax mit z3)", height=150,
                                   placeholder="x == f_y\ny == z\nf_z != x")
        int_vars = st.text_input("Integer-Variablen", value="x, y, z")
        func_vars = st.text_input("Funktionswerte als Variablen", value="f_y, f_z")

        if st.button("Lösen (EUF)", type="primary"):
            try:
                from z3 import Int, Solver, sat, unsat

                ns = {}
                for v in (int_vars + "," + func_vars).split(","):
                    v = v.strip()
                    if v:
                        ns[v] = Int(v)

                s = Solver()
                for line in euf_input.strip().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    constraint = eval(line.replace("==", "==").replace("!=", "!="), ns)
                    s.add(constraint)

                result = s.check()
                if result == sat:
                    st.success("✅ SATISFIABLE")
                    m = s.model()
                    for k, v in ns.items():
                        st.write(f"  `{k}` = `{m.eval(v)}`")
                else:
                    st.error("❌ UNSATISFIABLE")

            except Exception as e:
                st.error(f"Fehler: {e}")

        st.divider()
        st.subheader("🧩 EUF Congruence-Closure Explorer (zusätzlich)")
        st.caption("Zweites EUF-Tool: echte Term-Syntax mit f(a), g(a,b) und schrittweiser Kongruenzabschluss.")

        euf_cc_input = st.text_area(
            "EUF-Constraints (eine pro Zeile, mit == oder !=)",
            value="a == b\nf(a) == c\nf(b) != c",
            height=120,
            key="euf_cc_input",
        )

        if st.button("Congruence Closure ausführen", type="secondary", key="euf_cc_btn"):
            try:
                eqs, neqs = _euf_parse_constraints(euf_cc_input)
                if not eqs and not neqs:
                    st.warning("Bitte mindestens eine Gleichung oder Ungleichung eingeben.")
                else:
                    cc = _euf_congruence_closure(eqs, neqs)
                    st.subheader("Ergebnis")
                    if cc["sat"]:
                        st.success("✅ SATISFIABLE (keine verletzte Ungleichung nach Abschluss)")
                    else:
                        a, b = cc["conflict"]
                        st.error(
                            "❌ UNSATISFIABLE — Konflikt mit Ungleichung: "
                            f"`{_euf_term_to_str(a)} != {_euf_term_to_str(b)}`"
                        )

                    with st.expander("Äquivalenzklassen"):
                        for cls in cc["classes"]:
                            st.markdown(f"- `{{{', '.join(cls)}}}`")

                    with st.expander("Schritt-für-Schritt (Merges)"):
                        if not cc["steps"]:
                            st.info("Keine Merge-Schritte notwendig.")
                        for i, step in enumerate(cc["steps"], 1):
                            st.write(f"{i}. {step}")

            except Exception as e:
                st.error(f"Fehler: {e}")

    elif solver_mode == "CDCL-Trace simulieren":
        st.markdown("""**CDCL-Trace:** Gibt schrittweise die DPLL/CDCL-Lösungsschritte aus.""")

        clauses_input = st.text_area("Klauseln in CNF (eine pro Zeile, Variablen als Zahlen, negiert mit -)",
                                      height=150, placeholder="1 2 -3\n-1 3\n2 -3")

        if st.button("CDCL ausführen", type="primary"):
            try:
                from z3 import Bool, Or, Not, Solver, sat, unsat, BoolVal

                clauses = []
                var_set = set()
                for line in clauses_input.strip().splitlines():
                    lits = [int(x) for x in line.split() if x]
                    clauses.append(lits)
                    var_set.update(abs(l) for l in lits)

                vars_z3 = {i: Bool(f"x{i}") for i in var_set}
                s = Solver()
                for clause in clauses:
                    lits_z3 = [vars_z3[abs(l)] if l > 0 else Not(vars_z3[abs(l)]) for l in clause]
                    s.add(Or(*lits_z3) if len(lits_z3) > 1 else lits_z3[0])

                result = s.check()

                st.subheader("Klauseln:")
                for c in clauses:
                    st.write(f"  `({' ∨ '.join(('¬x'+str(abs(l)) if l < 0 else 'x'+str(abs(l))) for l in c)})`")

                if result == sat:
                    st.success("✅ SATISFIABLE")
                    m = s.model()
                    assignments = {i: str(m.eval(v)) for i, v in vars_z3.items()}
                    st.subheader("Belegung:")
                    for i in sorted(assignments):
                        st.write(f"  `x{i}` = `{assignments[i]}`")
                else:
                    st.error("❌ UNSATISFIABLE")

            except Exception as e:
                st.error(f"Fehler: {e}")

        st.divider()
        st.subheader("🌲 DPLL Trace Explorer (zusätzlich)")
        st.caption("Zweites Tool: deterministischer DPLL-Trace mit Unit Propagation, Pure Literal, Entscheidungen und Backtracking.")

        if st.button("DPLL Trace ausführen", type="secondary", key="dpll_trace_btn"):
            try:
                clauses = _parse_cnf_text(clauses_input)
                if not clauses:
                    st.warning("Bitte mindestens eine Klausel eingeben.")
                else:
                    sat_result, model, trace = _run_dpll_with_trace(clauses)
                    if sat_result:
                        st.success("✅ SATISFIABLE (DPLL)")
                    else:
                        st.error("❌ UNSATISFIABLE (DPLL)")

                    if model:
                        with st.expander("Gefundene Belegung (DPLL)"):
                            for var in sorted(model):
                                st.write(f"`x{var}` = `{model[var]}`")

                    with st.expander("Schritt-für-Schritt Trace"):
                        for i, step in enumerate(trace, 1):
                            st.write(f"{i}. {step}")

                    with st.expander("📝 Prüfungsformat (CDCL-Ablauf)", expanded=True):
                        st.caption("Formatierter Ablauf wie in der Prüfung gefordert.")
                        _render_cdcl_exam_format(sat_result, model, trace, clauses)

            except Exception as e:
                st.error(f"Fehler: {e}")

    else:  # BMC
        st.markdown("""**BMC (Safety):** Sucht einen Gegenbeispielpfad bis Tiefe `k`.
Gib ein endliches Zustandsmodell an und markiere "Bad States" (= Verletzung der Safety-Property).""")

        bmc_col_l, bmc_col_r = st.columns(2)
        with bmc_col_l:
            bmc_states_in = st.text_input("Zustände (kommagetrennt)", value="s0, s1, s2", key="bmc_states")
            bmc_init_in = st.text_input("Initialzustände (kommagetrennt)", value="s0", key="bmc_init")
            bmc_trans_in = st.text_area(
                "Übergänge (eine pro Zeile: src -> dst)",
                value="s0 -> s1\ns1 -> s1\ns1 -> s2\ns2 -> s2",
                height=120,
                key="bmc_trans",
            )
        with bmc_col_r:
            bmc_bad_in = st.text_input("Bad States (kommagetrennt)", value="s2", key="bmc_bad")
            bmc_k = st.number_input("Bound k", min_value=0, max_value=100, value=5, step=1, key="bmc_k")

        if st.button("BMC prüfen ✓", type="primary", key="bmc_btn"):
            try:
                from z3 import Int, And, Or, Solver, sat

                states = [s.strip() for s in bmc_states_in.split(",") if s.strip()]
                if not states:
                    raise ValueError("Mindestens ein Zustand erforderlich")
                states_set = set(states)

                init_states = [s.strip() for s in bmc_init_in.split(",") if s.strip()]
                if not init_states:
                    raise ValueError("Mindestens ein Initialzustand erforderlich")
                for s in init_states:
                    if s not in states_set:
                        raise ValueError(f"Unbekannter Initialzustand: '{s}'")

                bad_states = [s.strip() for s in bmc_bad_in.split(",") if s.strip()]
                if not bad_states:
                    raise ValueError("Mindestens ein Bad State erforderlich")
                for s in bad_states:
                    if s not in states_set:
                        raise ValueError(f"Unbekannter Bad State: '{s}'")

                transitions = []
                for line in bmc_trans_in.strip().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if "->" not in line:
                        raise ValueError(f"Ungültiger Übergang (kein '->'): '{line}'")
                    src, dst = line.split("->", 1)
                    src, dst = src.strip(), dst.strip()
                    if src not in states_set:
                        raise ValueError(f"Unbekannter Zustand im Übergang: '{src}'")
                    if dst not in states_set:
                        raise ValueError(f"Unbekannter Zustand im Übergang: '{dst}'")
                    transitions.append((src, dst))

                if not transitions:
                    raise ValueError("Mindestens ein Übergang erforderlich")

                state_to_id = {s: i for i, s in enumerate(states)}
                id_to_state = {i: s for s, i in state_to_id.items()}
                init_ids = [state_to_id[s] for s in init_states]
                bad_ids = [state_to_id[s] for s in bad_states]
                transition_ids = [(state_to_id[a], state_to_id[b]) for a, b in transitions]

                found_model = None
                found_depth = None

                for depth in range(int(bmc_k) + 1):
                    s = Solver()
                    xs = [Int(f"x_{i}") for i in range(depth + 1)]

                    for x in xs:
                        s.add(And(x >= 0, x < len(states)))

                    s.add(Or(*[xs[0] == idx for idx in init_ids]))

                    for i in range(depth):
                        s.add(Or(*[And(xs[i] == a, xs[i + 1] == b) for a, b in transition_ids]))

                    bad_hits = []
                    for i in range(depth + 1):
                        bad_hits.extend([xs[i] == b for b in bad_ids])
                    s.add(Or(*bad_hits))

                    if s.check() == sat:
                        found_model = s.model()
                        found_depth = depth
                        found_xs = xs
                        break

                st.subheader("Ergebnis")
                if found_model is None:
                    st.success(f"✅ Kein Gegenbeispiel bis Bound k={int(bmc_k)} gefunden")
                    st.caption("Interpretation: Safety-Property hält mindestens bis zur gewählten Tiefe.")
                else:
                    path_ids = [found_model.eval(x).as_long() for x in found_xs]
                    path_states = [id_to_state[i] for i in path_ids]
                    st.error(f"❌ Gegenbeispiel gefunden (Tiefe {found_depth})")
                    st.markdown(f"**Pfad:** `{' -> '.join(path_states)}`")

                    for i, st_name in enumerate(path_states):
                        marker = "💥" if st_name in bad_states else ""
                        st.write(f"t={i}: `{st_name}` {marker}")

                    with st.expander("BMC-Encoding (Kurzfassung)"):
                        st.markdown(f"- Zustände als Integer: `{state_to_id}`")
                        st.markdown(f"- Initiale Menge: `{init_states}`")
                        st.markdown(f"- Bad States: `{bad_states}`")
                        st.markdown(f"- Unrolling-Tiefe (gefunden): `{found_depth}`")

            except Exception as e:
                st.error(f"Fehler: {e}")

    st.divider()
    st.subheader("🧠 SMT Model Finder & UNSAT Core")
    st.caption("Negativ-Case Reasoning: zeigt Modell bei SAT oder Kernwiderspruch bei UNSAT.")

    smt_formula_input = st.text_area(
        "SMT-Formel (ein Ausdruck)",
        height=90,
        value="And(x > 0, x < 3)",
        key="smt_model_formula",
    )
    smt_constraints_input = st.text_area(
        "UNSAT-Core Constraints (eine Bedingung pro Zeile)",
        height=120,
        value="x > 0\nx < 0",
        key="unsat_core_constraints",
    )

    c_smt_1, c_smt_2 = st.columns(2)
    with c_smt_1:
        if st.button("SMT Modell suchen", key="smt_model_btn", type="secondary"):
            try:
                res = _find_smt_model(smt_formula_input)
                if res["result"] == "SAT":
                    st.success("✅ SAT")
                    for k, v in res["model"].items():
                        st.write(f"`{k} = {v}`")
                elif res["result"] == "UNSAT":
                    st.error("❌ UNSAT")
                else:
                    st.warning("UNKNOWN")
            except Exception as e:
                st.error(f"Fehler: {e}")
                st.code(traceback.format_exc())

    with c_smt_2:
        if st.button("UNSAT-Core berechnen", key="unsat_core_btn", type="secondary"):
            try:
                core_res = _analyze_unsat_core(smt_constraints_input)
                if core_res["result"] == "UNSAT":
                    st.error("❌ UNSAT")
                    st.markdown("**UNSAT-Core:**")
                    for line in core_res["core"]:
                        st.write(f"- `{line}`")
                elif core_res["result"] == "SAT":
                    st.success("✅ SAT (kein Widerspruch in den Constraints)")
                else:
                    st.warning("UNKNOWN")
            except Exception as e:
                st.error(f"Fehler: {e}")
                st.code(traceback.format_exc())

    st.divider()
    st.subheader("∃ Quantifier Elimination")
    qe_formula_input = st.text_area(
        "Formel mit Quantoren (Z3-Syntax)",
        height=100,
        value="Exists([x], And(x > 3, x < y))",
        key="qe_formula",
    )
    if st.button("Quantifier Elimination ausführen", key="qe_btn", type="secondary"):
        try:
            qe_res = _eliminate_quantifiers(qe_formula_input)
            st.markdown(f"**Original:** `{qe_res['original']}`")
            st.markdown(f"**QE-Ergebnis:** `{qe_res['qe']}`")
            st.markdown(f"**Simplified:** `{qe_res['simplified']}`")
        except Exception as e:
            st.error(f"Fehler: {e}")
            st.code(traceback.format_exc())

    st.divider()
    st.subheader("⚖️ Program Equivalence Checker")
    st.caption("Vergleicht zwei Implementierungen auf deinen Testausdrücken und liefert Gegenbeispiel bei Unterschied.")

    eq_col_l, eq_col_r = st.columns(2)
    with eq_col_l:
        eq_code_a = st.text_area("Programm A", height=120, value="def f(x):\n    return x + 1", key="eq_code_a")
    with eq_col_r:
        eq_code_b = st.text_area("Programm B", height=120, value="def f(x):\n    return 1 + x", key="eq_code_b")
    eq_tests = st.text_area("Testausdrücke (eine Zeile)", value="f(0)\nf(1)\nf(-3)", height=90, key="eq_tests")

    if st.button("Äquivalenz prüfen", key="eq_btn", type="secondary"):
        try:
            tests = [t.strip() for t in eq_tests.splitlines() if t.strip()]
            res = _check_equivalence(eq_code_a, eq_code_b, tests)
            if res["equivalent"]:
                st.success("✅ Auf den gegebenen Tests äquivalent.")
            else:
                st.error("❌ Nicht äquivalent.")
                st.write(f"Gegenbeispiel-Test: `{res['counterexample']}`")
                st.write(f"A: `{res['out_a']}`")
                st.write(f"B: `{res['out_b']}`")
        except Exception as e:
            st.error(f"Fehler: {e}")
            st.code(traceback.format_exc())

    with st.expander("📋 CDCL Vollständiger Algorithmus (Prüfungs-Format)"):
        st.markdown(r"""
**CDCL Schritt-für-Schritt (Prüfung):**

**1. Entscheidung + BCP an Level L:**
- Entscheide `xi = T/F` (Prüfung gibt Reihenfolge vor)
- **BCP:** Suche Unit-Klauseln = Klauseln mit genau 1 ungesetztem Literal, alle anderen False
  - Setze das ungesetzte Literal = True (erzwungen), notiere Antezedent-Klausel
  - Wiederhole bis keine Unit-Klauseln mehr → oder Konflikt

**2. Konflikt erkennen:**
- Eine Klausel ist VOLLSTÄNDIG False (alle Literale False) → KONFLIKT
- Notiere die **Konflikt-Klausel** K

**3. Konfliktgraph:**
- Zeige: Welche Entscheidungen/BCP-Schritte erzwingen die Literale in K?
- Kanten: `xi@Li —[Cj]→ xk@Lk` (Klausel Cj zwingt xk an Level Lk)

**4. Ersten UIP finden:**
- **1. UIP:** Das erste Literal auf ALLEN Pfaden vom Entscheidungs-Literal (aktuelles Level L) zum Konflikt
- Praktisch: Iteriere Resolution bis nur noch **1 Literal der Level L** in der Klausel übrig ist

**5. Lernklausel via Resolution:**
- Starte mit Konflikt-Klausel K
- Für jedes Literal `¬xi` in K mit Antezedent Ai (Level = aktuellem Level):
  - `K = resolve(K, Ai)` entfernt `xi` und `¬xi` (Resolvent)
- Stoppe wenn nur noch 1 Literal des aktuellen Levels übrig → das ist der UIP
- **Gelernte Klausel** = aktuelle K nach Auflösung

**6. Backjump-Level berechnen:**
- Backjump-Level = **Maximum der Entscheidungsebenen** aller Nicht-UIP-Literale in der gelernten Klausel
- (Bei nur 1 Nicht-UIP-Literal = dessen Level; bei Lernklausel ¬xi → Level 0)

**7. Backjump + Propagation:**
- Zurück auf Backjump-Level, entferne alle Assignments ab Level (Backjump-Level + 1)
- Gelernte Klausel wird Unit → UIP-Literal wird erzwungen (BCP)

---

**BCP-Checkliste für eine Klausel:**
- Alle Literale True: Klausel **erfüllt** (ignorieren)
- Genau 1 Literal ungesetzt, Rest False: **Unit** → setze das ungesetzte Literal = True
- Alle Literale False: **Konflikt** ❌
- Sonst: weiter beobachten

---

**EUF / Congruence Closure:**
- Gleichheiten: füge in Union-Find zusammen
- Kongruenz: `a=b → f(a)=f(b)` (für alle Terms mit gleichem Kopf)
- Dann: prüfe ob eine Ungleichung `a ≠ b` verletzt ist (a und b in gleicher Klasse)
- SAT = keine verletzte Ungleichung; UNSAT = mindestens eine verletzt
""")
