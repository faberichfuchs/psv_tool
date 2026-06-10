"""
Tab 0 — Coverage Analyzer
"""

import traceback

import streamlit as st

from tools.shared import (
    _c_to_python,
    _build_instrumented_code_for_decisions,
    _mcdc_result_for_decision,
    _run_tests_for_code,
    _generate_mutants,
    _analyze_dataflow,
    _trace_dataflow_coverage,
    _find_minimal_test_suite,
    _analyze_reachability,
    _detect_mutation_equivalence,
)


def render():
    st.header("Coverage Analyzer")
    st.caption("Python oder C — das Tool transpiliert C automatisch, korrigiert kleine Fehler und misst Coverage deterministisch.")

    lang = st.radio("Eingabesprache", ["Python", "C / C++"], horizontal=True, key="cov_lang")

    col1, col2 = st.columns([3, 2])

    C_PLACEHOLDER = """\
int fib(unsigned n) {
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

    PY_PLACEHOLDER = """\
def fib(n):
    a, b, i = 0, 1, 2
    while (i <= n) or (n == 0):
        c = a + b
        a = b
        b = c
        i += 1
        if n == 0:
            return 0
    return b"""

    with col1:
        label = "C-Code (wird automatisch nach Python transpiliert)" if lang == "C / C++" else "Python-Code"
        code_input = st.text_area(label, height=300,
                                  placeholder=C_PLACEHOLDER if lang == "C / C++" else PY_PLACEHOLDER,
                                  key="cov_code_input")

        if lang == "C / C++" and code_input.strip():
            py_out, transp_warns = _c_to_python(code_input)
            st.session_state["_cov_py"] = py_out
            with st.expander("🔄 Transpilierter Python-Code (wird analysiert)", expanded=True):
                st.code(py_out, language="python")
                if transp_warns:
                    for w in transp_warns:
                        st.warning(w)
        elif lang == "Python":
            st.session_state["_cov_py"] = code_input

        python_code_for_analysis = st.session_state.get("_cov_py", code_input)

    with col2:
        st.markdown("**Testfälle** (eine Zeile pro Aufruf, z.B. `fib(0)`, `fib(1)`)")
        test_cases_input = st.text_area("Testfälle", height=150, placeholder="fib(0)\nfib(1)", key="cov_test_cases")
        func_name = st.text_input("Funktionsname", value="", placeholder="fib")

    if st.button("Analysieren", type="primary"):
        if not code_input.strip() or not test_cases_input.strip():
            st.warning("Bitte Code und Testfälle eingeben.")
        else:
            try:
                import coverage as cov_module

                if lang == "C / C++":
                    python_code_for_analysis, _ = _c_to_python(code_input)
                else:
                    python_code_for_analysis = code_input

                import tempfile, os
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                    f.write(python_code_for_analysis)
                    tmp_path = f.name

                cov = cov_module.Coverage(branch=True)
                cov.start()

                namespace = {}
                exec(compile(python_code_for_analysis, tmp_path, 'exec'), namespace)

                results = []
                for tc in test_cases_input.strip().splitlines():
                    tc = tc.strip()
                    if not tc:
                        continue
                    try:
                        result = eval(tc, namespace)
                        results.append((tc, result, None))
                    except Exception as e:
                        results.append((tc, None, str(e)))

                cov.stop()
                cov.save()

                decision_meta = {}
                decision_log = {}
                decision_pass_error = None
                try:
                    instrumented_code, decision_meta = _build_instrumented_code_for_decisions(python_code_for_analysis)
                    ns2 = {}
                    current_rows = {}

                    def __psv_atom(decision_id, atom_id, value):
                        row = current_rows.setdefault(decision_id, {})
                        row[atom_id] = bool(value)
                        return value

                    def __psv_decision(decision_id, value):
                        out = bool(value)
                        entry = decision_log.setdefault(decision_id, {"true": 0, "false": 0, "evals": []})
                        if out:
                            entry["true"] += 1
                        else:
                            entry["false"] += 1
                        row = current_rows.pop(decision_id, {})
                        row["__result__"] = out
                        entry["evals"].append(row)
                        return value

                    def __psv_bool_op(decision_id, op, *values):
                        bool_vals = [bool(v) for v in values]
                        return any(bool_vals) if op == "or" else all(bool_vals)

                    ns2["__psv_atom"] = __psv_atom
                    ns2["__psv_decision"] = __psv_decision
                    ns2["__psv_bool_op"] = __psv_bool_op
                    exec(compile(instrumented_code, "<instrumented>", "exec"), ns2)

                    for tc in test_cases_input.strip().splitlines():
                        tc = tc.strip()
                        if not tc:
                            continue
                        current_rows.clear()
                        try:
                            eval(tc, ns2)
                        except Exception:
                            pass
                        current_rows.clear()
                except Exception as dec_err:
                    decision_pass_error = str(dec_err)

                import coverage
                analysis = cov.analysis2(tmp_path)
                executed_lines = set(analysis[1])
                missing_lines  = set(analysis[2])
                branch_stats   = cov.get_data().arcs(tmp_path) or []

                # Branch Coverage: true/false Branch je Decision (PSV-Definition)
                # Nicht CFG-Arcs (die zählen auch sequentielle Kanten → irreführend)
                branch_total = 0
                branch_covered = 0
                branch_missing = []   # list of (decision_id, "true"/"false") pairs
                _branch_err_msg = ""

                os.unlink(tmp_path)

                st.success("Ausführung abgeschlossen")

                st.subheader("Testfall-Ergebnisse")
                for tc, res, err in results:
                    if err:
                        st.error(f"`{tc}` → Fehler: {err}")
                    else:
                        st.write(f"`{tc}` → `{res}`")

                st.subheader("Annotierter Code")
                lines = python_code_for_analysis.splitlines()
                annotated = []
                for i, line in enumerate(lines, 1):
                    if i in executed_lines:
                        annotated.append(f"✅ {i:3d} | {line}")
                    elif i in missing_lines:
                        annotated.append(f"❌ {i:3d} | {line}")
                    else:
                        annotated.append(f"   {i:3d} | {line}")
                st.code("\n".join(annotated), language=None)

                total = len(executed_lines) + len(missing_lines)
                st.subheader("Coverage-Kriterien")

                sc_pct = len(executed_lines) / total * 100 if total else 0
                st.metric("Statement Coverage", f"{sc_pct:.0f}%",
                          delta="✓ erfüllt" if sc_pct == 100 else f"❌ {len(missing_lines)} Statement(s) fehlen")
                with st.expander("📝 Statement Coverage — Prüfungs-Erklärung"):
                    st.markdown("**Was ist Statement Coverage?**\nJede ausführbare Zeile (Statement) muss von mindestens einem Testfall ausgeführt werden.")
                    if sc_pct == 100:
                        st.success("✅ **Erfüllt** — alle Statements wurden ausgeführt. Begründung: Jede Zeile des Programms wurde von mindestens einem Testfall erreicht.")
                    else:
                        missing_stmts = sorted(missing_lines)
                        st.error(
                            f"❌ **Nicht erfüllt** — Zeile(n) {missing_stmts} wurden nie ausgeführt.\n\n"
                            f"Begründung: Die Test-Suite enthält keinen Testfall, der den Kontrollfluss zu "
                            f"{'dieser Zeile' if len(missing_stmts)==1 else 'diesen Zeilen'} führt. "
                            f"Um Statement Coverage zu erfüllen, wird ein Testfall benötigt, der "
                            f"{'Zeile ' + str(missing_stmts[0]) if len(missing_stmts)==1 else 'Zeilen ' + ', '.join(map(str,missing_stmts))} erreicht."
                        )

                if decision_meta:
                    covered_both = 0
                    for did in decision_meta:
                        entry = decision_log.get(did, {"true": 0, "false": 0})
                        if entry.get("true", 0) > 0 and entry.get("false", 0) > 0:
                            covered_both += 1
                        # Branch Coverage: true/false Branch je Decision erfassen
                        branch_total += 2
                        if entry.get("true", 0) > 0:
                            branch_covered += 1
                        else:
                            branch_missing.append((did, "true", decision_meta[did]))
                        if entry.get("false", 0) > 0:
                            branch_covered += 1
                        else:
                            branch_missing.append((did, "false", decision_meta[did]))
                    dc_pct = (covered_both / len(decision_meta)) * 100
                    st.metric(
                        "Decision Coverage",
                        f"{dc_pct:.0f}%",
                        delta=("✓ erfüllt" if covered_both == len(decision_meta)
                               else f"❌ {len(decision_meta) - covered_both} Decision(s) unvollständig"),
                    )

                    with st.expander("Decision-Details (True/False je Bedingung)"):
                        for did in sorted(decision_meta):
                            meta = decision_meta[did]
                            entry = decision_log.get(did, {"true": 0, "false": 0, "evals": []})
                            ok = entry["true"] > 0 and entry["false"] > 0
                            prefix = "✅" if ok else "❌"
                            st.markdown(
                                f"{prefix} **D{did}** (Zeile {meta['lineno']}): `{meta['expr']}`  "
                                f"→ true={entry['true']}, false={entry['false']}"
                            )

                    dc_incomplete = [(did, decision_meta[did], decision_log.get(did, {"true":0,"false":0}))
                                     for did in decision_meta
                                     if not (decision_log.get(did,{}).get("true",0) > 0
                                             and decision_log.get(did,{}).get("false",0) > 0)]
                    with st.expander("📝 Decision Coverage — Prüfungs-Erklärung"):
                        st.markdown("**Was ist Decision Coverage?**\nJede **Decision** (jede if/while-Bedingung) muss mindestens einmal als **True** und einmal als **False** ausgewertet werden.")
                        if not dc_incomplete:
                            st.success("✅ **Erfüllt** — jede Decision wurde sowohl als True als auch als False ausgewertet.")
                        else:
                            for did, meta, entry in dc_incomplete:
                                missing_dirs = []
                                if entry.get("true", 0) == 0: missing_dirs.append("True")
                                if entry.get("false", 0) == 0: missing_dirs.append("False")
                                st.error(
                                    f"❌ **Nicht erfüllt** — Decision `{meta['expr']}` (Zeile {meta['lineno']}) "
                                    f"wurde nie als {' und '.join(missing_dirs)} ausgewertet.\n\n"
                                    f"Begründung: Kein Testfall führt einen Programmpfad aus, bei dem diese "
                                    f"Bedingung {'den Wert ' + missing_dirs[0] if len(missing_dirs)==1 else 'die Werte True und False'} annimmt."
                                )

                    # Condition Coverage: jedes Atom in jeder Decision muss T und F gesehen haben
                    cc_ok_count = 0
                    cc_missing_atoms = []
                    for did in decision_meta:
                        meta = decision_meta[did]
                        evals = decision_log.get(did, {}).get("evals", [])
                        atoms = meta.get("atoms", [])
                        decision_cc_ok = True
                        for atom_id, atom_text in enumerate(atoms):
                            seen_t = any(e.get(atom_id) is True  for e in evals)
                            seen_f = any(e.get(atom_id) is False for e in evals)
                            if not (seen_t and seen_f):
                                decision_cc_ok = False
                                cc_missing_atoms.append((did, atom_id, atom_text, seen_t, seen_f, meta))
                        if decision_cc_ok:
                            cc_ok_count += 1
                    cc_pct = (cc_ok_count / len(decision_meta)) * 100 if decision_meta else 100
                    st.metric(
                        "Condition Coverage",
                        f"{cc_pct:.0f}%",
                        delta=("✓ erfüllt" if cc_ok_count == len(decision_meta)
                               else f"❌ {len(decision_meta) - cc_ok_count} Decision(s) mit fehlenden Atom-Werten"),
                    )
                    if cc_missing_atoms:
                        with st.expander("Fehlende Atom-Werte (Condition Coverage)"):
                            for did, atom_id, atom_text, seen_t, seen_f, meta_d in cc_missing_atoms:
                                missing_str = []
                                if not seen_t: missing_str.append("True fehlt")
                                if not seen_f: missing_str.append("False fehlt")
                                st.write(
                                    f"❌ D{did} (Z.{meta_d['lineno']}) atom[{atom_id}] "
                                    f"`{atom_text}`: {', '.join(missing_str)}"
                                )

                    mcdc_ok_count = 0
                    for did in decision_meta:
                        atom_count = len(decision_meta[did]["atoms"])
                        evals = decision_log.get(did, {}).get("evals", [])
                        ok, _ = _mcdc_result_for_decision(evals, atom_count)
                        if ok:
                            mcdc_ok_count += 1

                    mcdc_pct = (mcdc_ok_count / len(decision_meta)) * 100 if decision_meta else 100
                    st.metric(
                        "MC/DC (beobachtete Entscheidungen)",
                        f"{mcdc_pct:.0f}%",
                        delta=("✓ erfüllt" if mcdc_ok_count == len(decision_meta)
                               else f"❌ {len(decision_meta) - mcdc_ok_count} Decision(s) ohne vollständige Witnesses"),
                    )

                    mcdc_missing_atoms = []  # collect for explanation below
                    with st.expander("MC/DC-Details (Witness-Paare pro atomarer Bedingung)"):
                        for did in sorted(decision_meta):
                            meta = decision_meta[did]
                            evals = decision_log.get(did, {}).get("evals", [])
                            ok, witnesses = _mcdc_result_for_decision(evals, len(meta["atoms"]))
                            st.markdown(
                                f"{'✅' if ok else '❌'} **D{did}** (Zeile {meta['lineno']}): `{meta['expr']}`"
                            )
                            if not meta["atoms"]:
                                st.caption("Keine atomaren Bedingungen erkannt.")
                                continue
                            for atom_id, atom_text in enumerate(meta["atoms"]):
                                pair = witnesses.get(atom_id)
                                if pair is None:
                                    st.write(f"- ❌ atom[{atom_id}] `{atom_text}`: kein unabhängiges Paar gefunden")
                                    mcdc_missing_atoms.append((did, meta, atom_id, atom_text, witnesses, evals))
                                else:
                                    st.write(f"- ✅ atom[{atom_id}] `{atom_text}`: unabhängiges Paar gefunden")

                    # ── MC/DC Prüfungs-Erklärung ──────────────────────────────
                    with st.expander("📝 MC/DC — Prüfungs-Erklärung (Muster-Antwort)", expanded=bool(mcdc_missing_atoms)):
                      if not mcdc_missing_atoms:
                        st.success("✅ **Erfüllt** — für jedes Atom in jeder Decision existiert ein unabhängiges Witness-Paar.\n\nBegründung: Für jede atomare Bedingung gibt es zwei Testfälle, die sich nur im Wert dieses Atoms unterscheiden und bei denen sich das Decision-Ergebnis ändert.")
                      else:
                        with st.container():
                            st.markdown("""
**Was ist MC/DC?** *(aus den Vorlesungsfolien)*
MC/DC (Modified Condition/Decision Coverage) verlangt, dass jede **Condition** (atomare Teilbedingung)
in jeder Decision das Decision-Ergebnis **unabhängig** beeinflussen kann:

> *"Fix the value of all conditions in a decision except for one —*
> *flipping that one condition must change the decision outcome."*

**Vorgehen:** Für jede Condition `c` in einer Decision mit Conditions `c, c₂, …`:
- Halte alle anderen Conditions (`c₂, …`) **fest** (gleicher Wert in beiden Testfällen)
- `c` = True in Testfall t₁ → Decision-Ergebnis = X
- `c` = False in Testfall t₂ → Decision-Ergebnis = **nicht X**
- → t₁ und t₂ bilden ein **unabhängiges Paar** für `c`

Jede Condition muss mindestens einmal als True und einmal als False das Decision-Ergebnis unabhängig beeinflusst haben.
""")
                            st.markdown("---")
                            st.markdown("**Fehlende unabhängige Paare in dieser Test-Suite:**")
                            for did, meta, atom_id, atom_text, witnesses, evals in mcdc_missing_atoms:
                                expr = meta["expr"]
                                lineno = meta["lineno"]
                                atoms = meta["atoms"]
                                n_atoms = len(atoms)

                                # Describe what's been seen for this atom
                                seen_t = any(e.get(atom_id) is True  for e in evals)
                                seen_f = any(e.get(atom_id) is False for e in evals)

                                if not seen_t and not seen_f:
                                    seen_desc = "nie ausgeführt"
                                elif not seen_t:
                                    seen_desc = f"`{atom_text}` nur als **False** gesehen"
                                elif not seen_f:
                                    seen_desc = f"`{atom_text}` nur als **True** gesehen"
                                else:
                                    seen_desc = f"`{atom_text}` als True und False gesehen, aber kein unabhängiges Paar (andere Atome ändern sich immer gleichzeitig)"

                                # Which atoms need to be fixed to provide the witness
                                other_atoms = [a for i, a in enumerate(atoms) if i != atom_id]
                                other_str = " und ".join(f"`{a}`" for a in other_atoms) if other_atoms else "—"

                                st.markdown(f"""
**❌ Zeile {lineno} — Decision `{expr}` — Atom `{atom_text}`**

Beobachtung: {seen_desc}.

Für ein unabhängiges Paar wird benötigt:
- t₁: `{atom_text}` = **True**{f', {other_str} = fester Wert' if other_atoms else ''} → Decision-Ergebnis = X
- t₂: `{atom_text}` = **False**{f', {other_str} = **gleicher** fester Wert wie in t₁' if other_atoms else ''} → Decision-Ergebnis = **nicht X**

→ Die aktuelle Test-Suite hat {"keinen Testfall der `" + atom_text + "` als True auswertet" if not seen_t else "keinen Testfall der `" + atom_text + "` als False auswertet" if not seen_f else "kein Paar wo nur `" + atom_text + "` sich ändert (andere Conditions ändern sich gleichzeitig)"}.
""")

                            st.markdown("---")
                            st.markdown("**Fazit für die Prüfungsantwort:**")
                            lines_affected = sorted(set(meta['lineno'] for _, meta, _, _, _, _ in mcdc_missing_atoms))
                            atoms_affected = [f"`{atom_text}` (Zeile {meta['lineno']})"
                                              for _, meta, _, atom_text, _, _ in mcdc_missing_atoms]
                            st.markdown(
                                f"MC/DC ist **nicht erfüllt**, weil für "
                                f"{', '.join(atoms_affected)} kein unabhängiges Paar existiert. "
                                f"Ein unabhängiges Paar erfordert zwei Testfälle, bei denen sich nur der "
                                f"Wert dieser einen Condition ändert (alle anderen Conditions bleiben gleich) "
                                f"und dabei das Decision-Ergebnis wechselt — "
                                f"die vorhandene Test-Suite deckt diese Kombination nicht ab."
                            )

                if decision_pass_error:
                    st.warning(f"Decision/MC-DC Analyse teilweise fehlgeschlagen: {decision_pass_error}")

                if missing_lines:
                    st.info(f"Nicht ausgeführte Zeilen: {sorted(missing_lines)}")

                # Branch Coverage als eigene Metrik (PSV: true/false je Decision)
                if branch_total > 0:
                    branch_pct = 100 * branch_covered / branch_total
                    st.metric(
                        "Branch Coverage",
                        f"{branch_pct:.0f}%",
                        delta=("✓ erfüllt" if not branch_missing
                               else f"❌ {len(branch_missing)} Branch(es) fehlen"),
                    )
                    if branch_missing:
                        with st.expander("Fehlende Branches"):
                            for did, direction, meta in branch_missing:
                                st.write(f"  ❌ D{did} (Z.{meta['lineno']}) `{meta['expr']}` — {direction}-Branch nie genommen")
                    with st.expander("📝 Branch Coverage — Prüfungs-Erklärung"):
                        st.markdown("**Was ist Branch Coverage?**\nJeder **Zweig** (true-Zweig und false-Zweig) jeder Decision muss mindestens einmal genommen werden. Entspricht bei if/while genau Decision Coverage.")
                        if not branch_missing:
                            st.success("✅ **Erfüllt** — alle Branches (true und false) jeder Decision wurden genommen.")
                        else:
                            for did, direction, meta in branch_missing:
                                st.error(
                                    f"❌ **Nicht erfüllt** — {direction.capitalize()}-Branch von `{meta['expr']}` (Zeile {meta['lineno']}) wurde nie genommen.\n\n"
                                    f"Begründung: Kein Testfall wertet `{meta['expr']}` als {direction.capitalize()} aus, "
                                    f"daher wird der {'then' if direction=='true' else 'else'}-Zweig nie ausgeführt."
                                )

                st.info("Decision/Branch/MC/DC: Prüfe anhand der annotierten Zeilen und der Branch-Übergänge oben. Die ❌-Zeilen und fehlenden Branches zeigen dir genau was nicht abgedeckt ist.")

                # ── Auto-run schnelle Tools (Dataflow + Reachability) ─────────
                _py_auto = python_code_for_analysis
                _tests_auto = [t.strip() for t in test_cases_input.strip().splitlines() if t.strip()]
                st.session_state["_main_tests"] = _tests_auto
                # Widget-State direkt setzen, damit value= nicht ignoriert wird (Streamlit bevorzugt key-State)
                st.session_state["min_existing_input"] = "\n".join(_tests_auto)
                if _py_auto.strip() and _tests_auto:
                    # Data-flow (~instant, pure tracing)
                    try:
                        import sys as _sys
                        _sys.settrace(None)  # coverage-Modul kann settrace hinterlassen
                        st.session_state["_df_result"] = _trace_dataflow_coverage(_py_auto, _tests_auto)
                        st.session_state["_df_tests"] = _tests_auto
                        st.session_state["_df_static"] = _analyze_dataflow(_py_auto)
                    except Exception as _df_err:
                        st.warning(f"⚠ Dataflow-Analyse fehlgeschlagen: {_df_err}")
                        st.code(traceback.format_exc())
                    # Reachability (~instant, static CFG)
                    try:
                        st.session_state["_reach_result"] = _analyze_reachability(_py_auto)
                    except Exception as _reach_err:
                        st.warning(f"⚠ Reachability-Analyse fehlgeschlagen: {_reach_err}")
                        st.code(traceback.format_exc())
                # Mutation: bleibt hinter eigenem Button (60 Mutanten × Tests = langsam)

            except ImportError:
                st.error("coverage-Paket fehlt. Führe aus: `pip install coverage`")
            except Exception as e:
                st.error(f"Fehler: {e}")
                st.code(traceback.format_exc())

    st.divider()
    st.subheader("🧪 Mutation Testing (deterministisch)")
    st.caption("Erzeugt First-Order Mutanten und berechnet den Mutation Score auf Basis deiner Testfälle.")
    max_mutants = st.number_input("Max. Mutanten", min_value=1, max_value=300, value=20, step=1, key="mutation_max",
                                  help="Exam-Code hat typisch 5-15 Operatoren. 20 reicht für alle First-Order Mutanten.")

    # Show auto-result if available
    _mut_auto = st.session_state.get("_mut_result")
    if _mut_auto:
        _total = _mut_auto["total"]
        _killed_n = len(_mut_auto["killed"])
        _survived_n = len(_mut_auto["survived"])
        _score = int(100 * _killed_n / _total) if _total else 0
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Gesamt", str(_total))
        c2.metric("Getötet", str(_killed_n))
        c3.metric("Überlebt", str(_survived_n))
        c4.metric("Mutation Score", f"{_score}%")
        with st.expander("Überlebende Mutanten"):
            if not _mut_auto["survived"]:
                st.success("Keine.")
            for m in _mut_auto["survived"]:
                st.markdown(f"- ❌ M{m['id']} (Z.{m['lineno']}): `{m['operator']}`")

    if st.button("Mutation Score berechnen", key="mutation_btn", type="secondary"):
        _py = st.session_state.get("_cov_py", code_input)
        if not _py.strip() or not test_cases_input.strip():
            st.warning("Bitte Code und Testfälle eingeben.")
        else:
            try:
                tests = [tc.strip() for tc in test_cases_input.strip().splitlines() if tc.strip()]
                baseline = _run_tests_for_code(_py, tests)
                baseline_failures = [i for i, (ok, _) in enumerate(baseline) if not ok]
                if baseline_failures:
                    st.error(
                        "Baseline-Tests schlagen bereits fehl. "
                        f"Bitte zuerst korrigieren (fehlgeschlagene Testzeilen: {[i + 1 for i in baseline_failures]})."
                    )
                else:
                    mutants = _generate_mutants(_py, max_mutants=int(max_mutants))
                    if not mutants:
                        st.info("Keine mutierbaren Operatoren gefunden (And/Or, +/-, */ //, Vergleichsoperatoren).")
                    else:
                        killed = []
                        survived = []
                        for m in mutants:
                            try:
                                mutant_out = _run_tests_for_code(m["code"], tests)
                                if mutant_out != baseline:
                                    killed.append(m)
                                else:
                                    survived.append(m)
                            except Exception as exc:
                                m2 = dict(m)
                                m2["crash"] = f"{type(exc).__name__}: {exc}"
                                killed.append(m2)

                        total = len(mutants)
                        killed_n = len(killed)
                        score = 100.0 * killed_n / total if total else 0.0

                        st.metric(
                            "Mutation Score",
                            f"{score:.1f}%",
                            delta=("✓ stark" if score >= 80 else "Ausbaufähig"),
                        )
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Mutanten gesamt", str(total))
                        c2.metric("Getötet", str(killed_n))
                        c3.metric("Überlebt", str(len(survived)))

                        with st.expander("Überlebende Mutanten (höchste Priorität für neue Tests)"):
                            if not survived:
                                st.success("Keine überlebenden Mutanten.")
                            for m in survived:
                                st.markdown(f"- ❌ M{m['id']} (Zeile {m['lineno']}): `{m['operator']}`")

                        with st.expander("Getötete Mutanten"):
                            if not killed:
                                st.info("Keine getöteten Mutanten.")
                            for m in killed:
                                extra = f" — Crash: `{m['crash']}`" if "crash" in m else ""
                                st.markdown(f"- ✅ M{m['id']} (Zeile {m['lineno']}): `{m['operator']}`{extra}")

            except Exception as e:
                st.error(f"Fehler: {e}")
                st.code(traceback.format_exc())

    # ── Data-flow Coverage ────────────────────────────────────────────────────
    st.divider()
    st.subheader("🧭 Data-flow Coverage (deterministisch)")

    _df_res = st.session_state.get("_df_result")
    _df_tests = st.session_state.get("_df_tests", [])
    _df_static = st.session_state.get("_df_static")

    if _df_res and _df_tests:
        def _show_df_coverage(label, cov_data, is_def_level=False):
            """is_def_level=True: obligations are (var,def) 2-tuples (all-defs/some-* criteria)."""
            covered = sorted(cov_data["covered"])
            missing = sorted(cov_data["missing"])
            total = len(covered) + len(missing)
            pct = int(100 * len(covered) / total) if total else 0
            ok = "✅" if not missing else "❌"
            st.markdown(f"**{ok} {label}** — {len(covered)}/{total} ({pct}%)")
            if is_def_level:
                for var, d in covered:
                    st.markdown(f"  ✅ `{var}`: def@Z.{d} → (mind. 1 Use abgedeckt)")
                for var, d in missing:
                    st.markdown(f"  ❌ `{var}`: def@Z.{d} → **keine Use abgedeckt**")
            else:
                for var, d, u in covered:
                    st.markdown(f"  ✅ `{var}`: Z.{d} → Z.{u}")
                for var, d, u in missing:
                    st.markdown(f"  ❌ `{var}`: Z.{d} → Z.{u} ← **fehlt**")

        st.caption(f"Testfälle: `{'`, `'.join(_df_tests)}`")
        _show_df_coverage("all-defs", _df_res["all_defs"], is_def_level=True)
        st.divider()
        _show_df_coverage("all-c-uses", _df_res["all_c_uses"])
        st.divider()
        _show_df_coverage("all-p-uses", _df_res["all_p_uses"])

        if _df_static:
            with st.expander("Statische Obligationen (alle möglichen Def-Use Kanten)"):
                df_s = _df_static
                for var in sorted(set(df_s["defs"]) | set(df_s["c_uses"]) | set(df_s["p_uses"])):
                    st.markdown(f"- `{var}`: defs={df_s['defs'].get(var,[])} c-uses={df_s['c_uses'].get(var,[])} p-uses={df_s['p_uses'].get(var,[])}")
    else:
        st.info("Führe zuerst oben **Analysieren** aus — Data-flow wird automatisch mitberechnet.")

    st.divider()
    st.subheader("🎯 Minimale Testmenge (deterministisch)")
    st.caption("Wähle Criterion + bestehende Testfälle → sofortige Berechnung. Kandidaten werden automatisch generiert (n=0..N).")

    import ast as _ast

    def _extract_func_name(py_src):
        """Extract the first function name from Python source."""
        try:
            tree = _ast.parse(py_src)
            for node in _ast.walk(tree):
                if isinstance(node, _ast.FunctionDef):
                    return node.name
        except Exception:
            pass
        return None

    def _auto_candidates(func_name, n_max):
        return [f"{func_name}({i})" for i in range(n_max + 1)]

    def _run_minimal_analysis():
        _py = st.session_state.get("_cov_py", code_input)
        existing_raw = st.session_state.get("min_existing_input", "")
        criterion = st.session_state.get("min_criterion", "all-defs")
        n_max = st.session_state.get("min_n_max", 10)

        if not _py.strip():
            return

        existing = [t.strip() for t in existing_raw.strip().splitlines() if t.strip()]
        func_name = _extract_func_name(_py)
        if not func_name:
            st.warning("Funktionsname konnte nicht erkannt werden.")
            return

        candidates = _auto_candidates(func_name, n_max)
        # Remove existing from candidates pool to avoid overlap
        extra_candidates = [c for c in candidates if c not in existing]
        all_candidates = existing + extra_candidates

        try:
            res = _find_minimal_test_suite(_py, all_candidates, criterion, fixed=existing)
            selected_new = res["selected"]
            uncovered = res["uncovered"]
            total = len(res["total_obligs"])
            already = res["already_covered"]

            st.markdown(f"**Bestehende Testfälle** `{', '.join(existing) or '–'}` decken **{len(already)}/{total}** Obligationen")

            if total == 0:
                st.info("Keine Obligationen für dieses Criterion gefunden.")
                return

            if not uncovered:
                if not selected_new:
                    st.success(f"✅ Bereits vollständig abgedeckt — keine Ergänzung nötig.")
                else:
                    st.success(f"✅ Vollständige Abdeckung mit **{len(selected_new)}** zusätzlichem Testfall:")
                    for i, tc in enumerate(selected_new, 1):
                        extra = res["tc_coverage"][tc] - already
                        st.markdown(f"**+T{i}:** `{tc}` — deckt zusätzlich {len(extra)} Obligation(en)")
            else:
                # Check if uncovered is due to infeasibility (no candidate covers it)
                coverable_by_any = set()
                for tc, cov in res["tc_coverage"].items():
                    coverable_by_any |= cov
                truly_infeasible = uncovered - coverable_by_any
                fixable_with_more = uncovered & coverable_by_any

                if selected_new:
                    st.warning(f"⚠ Mit {len(selected_new)} Ergänzung(en): {total - len(uncovered)}/{total} abgedeckt.")
                    for i, tc in enumerate(selected_new, 1):
                        extra = res["tc_coverage"][tc] - already
                        st.markdown(f"**+T{i}:** `{tc}` — deckt zusätzlich {len(extra)} Obligation(en)")

                if truly_infeasible:
                    st.error(f"❌ {len(truly_infeasible)} Obligation(en) **nicht erreichbar** (infeasible path — kein Kandidat n=0..{n_max} deckt sie):")
                    for var, d, u in sorted(truly_infeasible):
                        st.markdown(f"  ❌ `{var}`: Z.{d} → Z.{u}")
                if fixable_with_more:
                    st.info(f"ℹ {len(fixable_with_more)} Obligation(en) bräuchten n>{n_max} — Range erhöhen.")

            with st.expander("Details: Coverage pro Testfall"):
                for tc in existing + selected_new:
                    cov = res["tc_coverage"].get(tc, set())
                    label = "📌" if tc in existing else "➕"
                    parts = []
                    for item in sorted(cov):
                        if len(item) == 2:
                            parts.append(f"`{item[0]}`:def@Z.{item[1]}")
                        else:
                            parts.append(f"`{item[0]}`:Z.{item[1]}→Z.{item[2]}")
                    st.markdown(f"{label} `{tc}`: " + (", ".join(parts) or "–"))

        except Exception as e:
            st.error(f"Fehler: {e}")
            st.code(traceback.format_exc())

    col_min1, col_min2, col_min3 = st.columns([2, 2, 1])
    with col_min1:
        st.selectbox(
            "Criterion",
            ["all-defs", "all-c-uses", "all-p-uses", "all-uses", "all-c-uses/some-p-uses", "all-p-uses/some-c-uses", "some-c-uses", "some-p-uses"],
            key="min_criterion",
        )
    with col_min2:
        # Wert wird via st.session_state["min_existing_input"] aus dem Analysieren-Handler gesetzt.
        # value= würde von Streamlit ignoriert sobald der key in session_state existiert.
        st.text_area(
            "Bestehende Testfälle (aus Analysieren übernommen)",
            height=80,
            placeholder="fib(0)\nfib(1)",
            key="min_existing_input",
        )
    with col_min3:
        st.number_input("Max n", min_value=2, max_value=50, value=10, step=1, key="min_n_max",
                        help="Kandidaten fib(0)..fib(n) werden automatisch generiert")

    # Auto-run when code + tests available (after Analysieren or on criterion change)
    if st.session_state.get("_cov_py") and st.session_state.get("_main_tests"):
        _run_minimal_analysis()
    else:
        if st.button("▶ Berechnen", key="min_suite_btn", type="primary"):
            _run_minimal_analysis()

    st.divider()
    st.subheader("🧱 Reachability & Dead-Code Analyzer")
    _reach = st.session_state.get("_reach_result")
    if _reach:
        c1, c2 = st.columns(2)
        c1.metric("Erreichbare Zeilen", str(len(_reach["reachable"])))
        c2.metric("Unerreichbare Zeilen", str(len(_reach["unreachable"])))
        if _reach["unreachable"]:
            st.error(f"Unerreichbar: {_reach['unreachable']}")
        else:
            st.success("Keine unerreichbaren Statements.")
        with st.expander("CFG-Kanten"):
            for src, dst, kind in _reach["cfg"]["edges"]:
                st.write(f"- `{src} -> {dst}` ({kind})")
    else:
        st.info("Wird nach **Analysieren** automatisch berechnet.")

    st.divider()
    st.subheader("🧬 Mutation Equivalence Detector")
    st.caption("Prüft, ob ein überlebender Mutant evtl. semantisch äquivalent ist.")

    mutant_code_input = st.text_area(
        "Mutanten-Code (zum Vergleich mit Original-Code oben)",
        height=140,
        placeholder="def f(x):\n    return x + 1",
        key="mutation_equiv_code",
    )

    if st.button("Äquivalenz Original vs Mutant prüfen", key="mutation_equiv_btn", type="secondary"):
        _py = st.session_state.get("_cov_py", code_input)
        if not _py.strip() or not mutant_code_input.strip() or not test_cases_input.strip():
            st.warning("Bitte Original-Code, Mutanten-Code und Testfälle eingeben.")
        else:
            try:
                tests = [tc.strip() for tc in test_cases_input.splitlines() if tc.strip()]
                eq = _detect_mutation_equivalence(_py, mutant_code_input, tests)
                if eq.get("equivalent"):
                    st.info("⚠ Auf den gegebenen Tests äquivalent (kein Gegenbeispiel gefunden).")
                else:
                    st.success("✅ Nicht äquivalent — Gegenbeispiel gefunden.")
                    st.write(f"Test: `{eq['counterexample']}`")
                    st.write(f"Original: `{eq['out_a']}`")
                    st.write(f"Mutant: `{eq['out_b']}`")
            except Exception as e:
                st.error(f"Fehler: {e}")
                st.code(traceback.format_exc())

    with st.expander("📋 Manuelle Checkliste (für Prüfung ohne Tool)"):
        st.markdown("""
**Schritt 1 — Statements identifizieren:** Nummeriere jede ausführbare Zeile.

**Schritt 2 — Decisions identifizieren:** Finde alle booleschen Ausdrücke (while, if, for).

**Schritt 3 — Für jeden Testfall tracen:** Welche Zeilen werden ausgeführt?

**Schritt 4 — Coverage prüfen:**
- **Statement Coverage** ✓ wenn: alle Zeilen von mindestens einem Testfall ausgeführt
- **Decision Coverage** ✓ wenn: jede Decision (while/if) sowohl true als auch false annimmt
- **Branch Coverage** ✓ wenn: jeder true- UND false-Zweig jeder Decision genommen wird
- **MC/DC** ✓ wenn: jede atomare Bedingung unabhängig das Gesamtergebnis beeinflusst
  → Für `A || B`: brauche Testfall wo nur A=T entscheidet, und einen wo nur B=T entscheidet
- **All-defs** ✓ wenn: jede Variable-Definition von mind. einem Testfall bis zu einer Verwendung verfolgt wird
- **All-c-uses** ✓ wenn: jede def→c-use Kante abgedeckt
- **All-p-uses** ✓ wenn: jede def→p-use Kante abgedeckt
""")
