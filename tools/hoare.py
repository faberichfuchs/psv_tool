"""
Tab 2 — Hoare Logic & Loop Invariants
"""

import ast
import textwrap
import traceback

import streamlit as st

from tools.shared import (
    _wp_of_stmts,
    _find_hoare_counterexample,
    _falsify_loop_invariant,
    _generate_hoare_proof,
    _generate_invariant_ce_explanation,
    z3_parse_expr,
)


def _parse_triple(text: str):
    """Parse '{Pre} code {Post}' from exam text.
    Returns (pre, code, post) as strings, or raises ValueError."""
    import re
    # Extract {…} blocks — first = Pre, last = Post, middle = code
    blocks = re.split(r'\{([^}]*)\}', text)
    # blocks: ['before_pre', pre, 'code', post, 'after_post']
    # Find all {…} contents
    braces = re.findall(r'\{([^}]*)\}', text)
    if len(braces) < 2:
        raise ValueError("Mindestens zwei {…}-Blöcke erwartet: {Pre} code {Post}")
    pre  = braces[0].strip()
    post = braces[-1].strip()
    # Extract code between first and last {…}
    first_end = text.index('}') + 1
    last_start = text.rindex('{')
    code = text[first_end:last_start].strip()
    return pre, code, post


def _c_to_py_inline(code: str) -> str:
    """Convert C-like exam code to Python syntax."""
    import re

    # Step 1: normalise everything onto separate lines by inserting newlines
    # around { } and ; so every token is alone on its line
    code = re.sub(r'\}\s*else\s*\{', '\n__ELSE__\n', code)
    code = re.sub(r'\{', '\n{\n', code)
    code = re.sub(r'\}', '\n}\n', code)
    code = re.sub(r';', '\n', code)

    flat = [l.strip() for l in code.splitlines() if l.strip()]

    result_lines = []
    indent = 0

    for line in flat:
        if line == '{':
            indent += 1
            continue
        if line == '}':
            indent = max(0, indent - 1)
            continue
        if line == '__ELSE__':
            indent = max(0, indent - 1)
            result_lines.append('    ' * indent + 'else:')
            indent += 1
            continue

        # Convert control flow keywords — do NOT increment indent here; { does it
        m = re.match(r'^while\s*\((.+)\)\s*$', line)
        if m:
            result_lines.append('    ' * indent + f'while {_fix_cond(m.group(1))}:')
            continue
        m = re.match(r'^if\s*\((.+)\)\s*$', line)
        if m:
            result_lines.append('    ' * indent + f'if {_fix_cond(m.group(1))}:')
            continue

        result_lines.append('    ' * indent + line)

    raw_code = '\n'.join(result_lines)
    try:
        ast.parse(raw_code)
        return raw_code
    except SyntaxError:
        return raw_code


def _fix_cond(c: str) -> str:
    """Convert C condition to Python (&&→and, ||→or, !→not)."""
    import re
    c = c.strip()
    c = c.replace('&&', ' and ').replace('||', ' or ')
    c = re.sub(r'!(?!=)', 'not ', c)
    c = c.replace('!=', '!=')  # preserve !=
    return c.strip()


def _extract_vars(code: str, pre: str, post: str) -> list:
    """Heuristically extract variable names from code + conditions."""
    import re
    names = re.findall(r'\b([a-z_][a-z0-9_]*)\b', code + ' ' + pre + ' ' + post)
    keywords = {'and', 'or', 'not', 'if', 'else', 'while', 'return', 'true', 'false',
                'True', 'False', 'int', 'unsigned', 'void'}
    seen = []
    for n in names:
        if n not in keywords and n not in seen and not n.isdigit():
            seen.append(n)
    return seen


def _render_triple_solver():
    st.markdown("""
**Füge den vollständigen Hoare-Triple aus der Angabe ein** — die App erkennt automatisch Pre, Code und Post,
extrahiert die Variablen und füllt die Felder für die Invariantenprüfung aus.

**Syntax-Hinweise:**
- Angabe-Format: `{Pre}` Code `{Post}` (geschwungene Klammern)
- C-Syntax im Code (`&&`, `||`, `!`) wird automatisch konvertiert

**Erlaubte Schreibweisen für Pre, Post und Invariante:**

| Operator | Schreibweisen |
|---|---|
| UND | `&&` · `and` · `And(a, b)` |
| ODER | `\|\|` · `or` · `Or(a, b)` |
| NICHT | `!x` · `not x` · `Not(x)` |
| IMPLIKATION | `A => B` · `A ⇒ B` · `A -> B` · `Implies(A, B)` |
| VERKETTUNG | `l*l <= n < r*r` → `And(l*l<=n, n<r*r)` |
| WAHR/FALSCH | `true` · `false` |
""")

    triple_input = st.text_area(
        "Hoare-Triple aus der Angabe (inkl. {Pre} und {Post})",
        height=200,
        placeholder="{true}\nif (i < 2) {\n  i = 2;\n} else {\n  i = 7;\n}\nwhile (i > 1 && i < 10) {\n  i = i + 1;\n}\n{i != 1 && i != 11}",
        key="triple_input",
    )

    parsed_ok = False
    pre_str = code_str = post_str = py_code = ""
    detected_vars = []

    if triple_input.strip():
        try:
            pre_str, code_str, post_str = _parse_triple(triple_input)
            py_code = _c_to_py_inline(code_str)
            detected_vars = _extract_vars(py_code, pre_str, post_str)
            parsed_ok = True
            with st.expander("✅ Geparstes Triple", expanded=True):
                col1, col2 = st.columns(2)
                col1.markdown(f"**Pre:** `{pre_str}`")
                col2.markdown(f"**Post:** `{post_str}`")
                st.code(py_code, language="python")
                st.caption(f"Erkannte Variablen: `{', '.join(detected_vars)}`")
        except Exception as e:
            st.error(f"Parse-Fehler: {e}")

    if parsed_ok:
        # Detect structure: does it have a while loop?
        has_while = 'while' in py_code
        has_if    = 'if' in py_code

        # Split into init-code (before while) and while body
        py_lines = py_code.splitlines()
        init_lines = []
        while_cond = ""
        body_lines = []
        in_while = False
        while_indent = 0
        for line in py_lines:
            stripped = line.strip()
            if not in_while and stripped.startswith('while ') and stripped.endswith(':'):
                while_cond = stripped[6:-1].strip()
                while_indent = len(line) - len(line.lstrip())
                in_while = True
            elif in_while:
                if stripped:
                    # Strip exactly while_indent+4 spaces (one level deeper)
                    body_lines.append(line[while_indent + 4:] if len(line) > while_indent + 4 else stripped)
            else:
                if stripped:
                    init_lines.append(line)  # keep original indentation

        import textwrap as _tw
        init_code_default = _tw.dedent('\n'.join(init_lines)).strip()
        body_code_default = '\n'.join(body_lines)

        st.divider()
        if has_while:
            st.markdown(f"**Erkannte Struktur:** {'if/else + ' if has_if else ''}while-Schleife")
            st.markdown(f"- Init-Code: `{init_code_default or '(leer)'}`")
            st.markdown(f"- While-Bedingung B: `{while_cond}`")
            st.markdown(f"- Loop-Body: `{body_code_default}`")
        else:
            st.markdown("**Erkannte Struktur:** if/else (keine Schleife) — WP-Kalkül wird direkt angewendet")

        # Invariant input (only needed for while)
        if has_while:
            inv_default = st.session_state.get("triple_inv_prefill", "")
            inv_I = st.text_input(
                "Loop-Invariante I (C: `i>=2 && i<10`, Implies: `(b>x) => (a>y)`, Z3: `And(...)`, Chained: `l*l<=n<r*r`)",
                value=inv_default,
                key="triple_inv",
                help="Tippe deine Vermutung ein — Z3 prüft Init, Erhaltung, Konsequenz."
            )
        else:
            inv_I = ""

        vars_str = ', '.join(detected_vars)

        if st.button("🔍 Beweisen / Prüfen", type="primary", key="triple_prove_btn"):
            try:
                import textwrap as _textwrap
                from z3 import Int, And, Or, Not, Solver, sat, unsat, substitute, Implies, BoolVal

                vars_dict = {v.strip(): Int(v.strip()) for v in detected_vars if v.strip()}
                z3ns = {**vars_dict, "And": And, "Or": Or, "Not": Not, "Implies": Implies,
                        "true": BoolVal(True), "false": BoolVal(False),
                        "True": BoolVal(True), "False": BoolVal(False)}

                def parse_z3(s):
                    return z3_parse_expr(s, z3ns)

                Pre  = parse_z3(pre_str)
                Post = parse_z3(post_str)

                if not has_while:
                    # Pure if/else: compute WP of entire code
                    import ast as _ast
                    tree = _ast.parse(py_code)
                    wp_steps = []
                    wp_pre_computed = _wp_of_stmts(tree.body, Post, vars_dict, z3ns, wp_steps)
                    s = Solver()
                    s.add(Pre, Not(wp_pre_computed))
                    ok = s.check() == unsat
                    if ok:
                        st.success("✅ Hoare-Triple **gültig** — Pre ⊨ WP(code, Post)")
                    else:
                        st.error("❌ Hoare-Triple **ungültig** — Gegenbeispiel gefunden")
                        m = s.model()
                        st.write({str(d.name()): str(m[d]) for d in m.decls()})
                    with st.expander("WP-Derivation (rückwärts)", expanded=True):
                        st.markdown(f"**Ziel:** `{Post}`")
                        for step in wp_steps:
                            st.markdown(step)
                        st.markdown(f"**WP(code, Post) = `{wp_pre_computed}`**")
                        st.markdown(f"**Pre = `{Pre}`**")
                        st.markdown(f"Zu zeigen: Pre ⊨ WP  → {'✅ gilt' if ok else '❌ gilt nicht'}")
                    return

                # While case
                if not inv_I.strip():
                    st.warning("Bitte Loop-Invariante I eingeben.")
                    return

                I = parse_z3(inv_I)
                B = parse_z3(while_cond)

                # Consequence: I ∧ ¬B ⊨ Post
                s1 = Solver()
                s1.add(I, Not(B), Not(Post))
                conseq_ok  = s1.check() == unsat
                conseq_cex = s1.model() if not conseq_ok else None

                # Preservation: I ∧ B ⊨ WP(body, I)
                import ast as _ast
                body_tree = _ast.parse(body_code_default)
                body_wp_steps = []
                wp_body = _wp_of_stmts(body_tree.body, I, vars_dict, z3ns, body_wp_steps)
                s2 = Solver()
                s2.add(And(I, B), Not(wp_body))
                pres_ok  = s2.check() == unsat
                pres_cex = s2.model() if not pres_ok else None

                # Init: Pre ⊨ WP(init, I)
                init_src = _textwrap.dedent(init_code_default.strip())
                init_wp_steps = []
                if init_src:
                    init_tree = _ast.parse(init_src)
                    wp_init = _wp_of_stmts(init_tree.body, I, vars_dict, z3ns, init_wp_steps)
                else:
                    wp_init = I
                s3 = Solver()
                s3.add(Pre, Not(wp_init))
                init_ok  = s3.check() == unsat
                init_cex = s3.model() if not init_ok else None

                # Results
                st.subheader("Ergebnis")
                c1, c2, c3 = st.columns(3)
                (c1.success if init_ok   else c1.error)(("✅" if init_ok   else "❌") + " Init\nPre ⊨ WP(init, I)")
                (c2.success if pres_ok   else c2.error)(("✅" if pres_ok   else "❌") + " Erhaltung\nI ∧ B ⊨ WP(body, I)")
                (c3.success if conseq_ok else c3.error)(("✅" if conseq_ok else "❌") + " Konsequenz\nI ∧ ¬B ⊨ Post")

                all_ok = init_ok and pres_ok and conseq_ok
                if all_ok:
                    st.success("🎉 **Beweis vollständig** — I ist eine gültige Loop-Invariante.")
                elif not init_ok:
                    st.error("❌ **Init schlägt fehl** — I gilt nach dem Init-Code nicht. Stärke I oder ändere Init.")
                elif not pres_ok:
                    st.warning("⚠ **Erhaltung schlägt fehl** — I wird im Loop-Body verletzt. Ändere I.")
                elif not conseq_ok:
                    st.error("❌ **Konsequenz schlägt fehl** — I ∧ ¬B impliziert Post nicht. Stärke I.")

                # WP expanders
                with st.expander("WP-Derivation: Loop-Body → I"):
                    st.markdown(f"**Ziel (I):** `{I}`")
                    for step in body_wp_steps:
                        st.markdown(step)
                    st.markdown(f"**WP(body, I) = `{wp_body}`**")

                with st.expander("WP-Derivation: Init-Code → I"):
                    st.markdown(f"**Ziel (I):** `{I}`")
                    for step in init_wp_steps:
                        st.markdown(step)
                    st.markdown(f"**WP(init, I) = `{wp_init}`**")

                # Counterexamples
                for label, model in [("Init schlägt fehl", init_cex),
                                      ("Erhaltung schlägt fehl", pres_cex),
                                      ("Konsequenz schlägt fehl", conseq_cex)]:
                    if model:
                        with st.expander(f"Gegenbeispiel: {label}"):
                            st.json({str(d.name()): str(model[d]) for d in model.decls()})

                # Annotated proof
                with st.expander("📝 Annotierter Beweis (Prüfungs-Format)", expanded=all_ok):
                    proof_lines = _generate_hoare_proof(
                        code=init_code_default + "\nwhile " + while_cond + ":\n" +
                             "\n".join("    " + l for l in body_code_default.splitlines()),
                        invariant_str=inv_I,
                        pre_str=pre_str,
                        post_str=post_str,
                        vars_str=vars_str,
                    )
                    for ln in proof_lines:
                        st.markdown(ln)

            except Exception as e:
                st.error(f"Fehler: {e}")
                st.code(traceback.format_exc())


def render():
    st.header("Hoare Logic & Loop Invariants")

    with st.expander("📋 Hoare-Logik Cheatsheet (immer sichtbar)", expanded=True):
        st.markdown(r"""
**Hoare-Tripel:** `{P} S {Q}` — wenn P gilt vor S und S terminiert, gilt Q danach.

**Axiome & Regeln:**
| Regel | Form |
|---|---|
| Assignment | `{Q[x←e]} x := e {Q}` — WP rückwärts substituieren |
| Sequence | `{P} S1 {R}`, `{R} S2 {Q}` → `{P} S1;S2 {Q}` |
| If-Then-Else | `{P∧B} S1 {Q}`, `{P∧¬B} S2 {Q}` → `{P} if B then S1 else S2 {Q}` |
| While | `{I∧B} S {I}` → `{I} while B do S {I∧¬B}` |
| Consequence | P'⊨P, `{P} S {Q}`, Q⊨Q' → `{P'} S {Q'}` |

**Loop-Invariante I muss 3 Eigenschaften erfüllen:**
1. **Init:** `Pre ⊨ WP(init_code, I)` — I gilt nach der Initialisierung
2. **Erhaltung:** `I ∧ B ⊨ WP(body, I)` — ein Schleifendurchlauf erhält I
3. **Konsequenz:** `I ∧ ¬B ⊨ Q` — nach der Schleife folgt die Nachbedingung

**WP-Kalkül (rückwärts):** WP(x:=e, Q) = Q[x←e]  (ersetze x durch e in Q)
""")

    st.subheader("🔧 Deterministische Verifikation mit Z3")
    st.caption("Kein LLM — 100% deterministisch. Gib Invariante ein, Z3 prüft alle 3 Bedingungen.")

    wp_mode = st.radio("Modus", ["Prüfungs-Triple lösen", "Loop-Invariante prüfen", "WP-Kalkulator (Zuweisung)"], key="wp_mode",
                       horizontal=True)

    if wp_mode == "Prüfungs-Triple lösen":
        _render_triple_solver()
    elif wp_mode == "Loop-Invariante prüfen":
        st.info("""
**Erlaubte Syntax für alle Ausdrucks-Felder (Pre, I, B, Q):**

| Operator | Erlaubte Schreibweisen |
|---|---|
| UND | `&&` · `and` · `And(a, b)` |
| ODER | `\\|\\|` · `or` · `Or(a, b)` |
| NICHT | `!x` · `not x` · `Not(x)` |
| IMPLIKATION | `A => B` · `A ⇒ B` · `A -> B` · `Implies(A, B)` |
| VERKETTUNG | `l*l <= n < r*r` → wird zu `And(l*l<=n, n<r*r)` |
| WAHR/FALSCH | `true` · `false` · `True` · `False` |
""")

        # ── Code direkt einfügen (optional) ─────────────────────────────────
        with st.expander("📋 Code direkt einfügen (auto-parsen)", expanded=False):
            st.caption("Füge den Programm-Code (C- oder Python-Syntax, ohne {Pre}/{Post}) ein — die App extrahiert Init, B und Body automatisch.")
            raw_code_inv = st.text_area(
                "Programm-Code",
                height=160,
                key="inv_raw_code",
                placeholder="if (b >= a) { tmp = a; a = b + 1; b = tmp; }\nwhile (a != b && x != y) { a = a - 1; y = y + 1; }",
            )
            if st.button("Code analysieren →", key="inv_parse_btn") and raw_code_inv.strip():
                try:
                    py_code = _c_to_py_inline(raw_code_inv)
                    import ast as _ast_inv
                    _tree_inv = _ast_inv.parse(py_code)
                    _loop_inv = next((s for s in _ast_inv.walk(_tree_inv) if isinstance(s, _ast_inv.While)), None)
                    if _loop_inv:
                        _prefix_inv = []
                        _in_while = False
                        for _line in py_code.splitlines():
                            _s = _line.strip()
                            if not _in_while and _s.startswith("while ") and _s.endswith(":"):
                                _in_while = True
                            elif not _in_while and _s:
                                _prefix_inv.append(_line)
                        import textwrap as _tw_inv
                        _init_default = _tw_inv.dedent("\n".join(_prefix_inv)).strip()
                        _cond_default = _ast_inv.unparse(_loop_inv.test)
                        _body_lines = []
                        for _bs in _loop_inv.body:
                            _body_lines.append(_ast_inv.unparse(_bs))
                        _body_default = "\n".join(_body_lines)
                        _vars_found = sorted({n.id for n in _ast_inv.walk(_tree_inv)
                                              if isinstance(n, _ast_inv.Name)
                                              and n.id not in ("True","False","And","Or","Not","Implies","tmp")})
                        st.session_state["inv_vars"]  = ", ".join(_vars_found)
                        st.session_state["inv_init"]  = _init_default
                        st.session_state["inv_B"]     = _cond_default
                        st.session_state["inv_body"]  = _body_default
                        st.success(f"Erkannt: Variablen `{', '.join(_vars_found)}` · B: `{_cond_default}`")
                        st.rerun()
                    else:
                        st.error("Keine while-Schleife gefunden.")
                except Exception as _e:
                    st.error(f"Parse-Fehler: {_e}")

        col1, col2 = st.columns(2)
        with col1:
            inv_vars   = st.text_input("Integer-Variablen (kommagetrennt)", value="n, y, i", key="inv_vars")
            inv_pre    = st.text_input("Vorbedingung Pre", value="n >= 0", key="inv_pre")
            inv_I      = st.text_input("Loop-Invariante I", value="And(y == i, i >= 0, i <= n)", key="inv_I")
            inv_B      = st.text_input("Schleifenbedingung B", value="i < n", key="inv_B")
        with col2:
            inv_Q      = st.text_input("Nachbedingung Q", value="y == n", key="inv_Q")
            inv_init   = st.text_area("Init-Code (vor Schleife, Python-Syntax)",
                                      value="y = 0\ni = 0", height=80, key="inv_init")
            inv_body   = st.text_area("Schleifenkörper (eine Zuweisung pro Zeile: var = expr)",
                                      value="y = y + 1\ni = i + 1", height=80, key="inv_body")

        if st.button("Invariante prüfen ✓", type="primary", key="inv_check"):
            try:
                import textwrap as _textwrap
                from z3 import Int, And, Or, Not, Solver, sat, unsat, substitute, Implies, BoolVal

                vars_dict = {}
                for v in inv_vars.split(","):
                    v = v.strip()
                    if v:
                        vars_dict[v] = Int(v)
                z3ns = {**vars_dict, "And": And, "Or": Or, "Not": Not, "Implies": Implies,
                        "True": BoolVal(True), "False": BoolVal(False)}

                def parse(s):
                    return z3_parse_expr(s, z3ns)

                def wp_of_assignments(stmts_text, post):
                    assignments = []
                    for line in stmts_text.strip().splitlines():
                        line = line.strip()
                        if not line or "=" not in line:
                            continue
                        lhs, rhs = line.split("=", 1)
                        assignments.append((lhs.strip(), rhs.strip()))
                    current = post
                    steps = []
                    for var_name, expr_str in reversed(assignments):
                        var_z3  = vars_dict[var_name]
                        expr_z3 = eval(expr_str, z3ns)
                        new     = substitute(current, (var_z3, expr_z3))
                        steps.append((var_name, expr_str, new))
                        current = new
                    return current, list(reversed(steps))

                I   = parse(inv_I)
                B   = parse(inv_B)
                Q   = parse(inv_Q)
                Pre = parse(inv_pre)

                s1 = Solver()
                s1.add(I, Not(B), Not(Q))
                conseq_ok    = s1.check() == unsat
                conseq_cex   = s1.model() if not conseq_ok else None

                wp_body, body_steps = wp_of_assignments(inv_body, I)
                s2 = Solver()
                s2.add(And(I, B), Not(wp_body))
                pres_ok      = s2.check() == unsat
                pres_cex     = s2.model() if not pres_ok else None

                # Init-Code: supports if/else via _wp_of_stmts
                init_src = _textwrap.dedent(inv_init.strip())
                if init_src:
                    import ast as _ast
                    init_tree = _ast.parse(init_src)
                    init_wp_steps = []
                    wp_init = _wp_of_stmts(init_tree.body, I, vars_dict, z3ns, init_wp_steps)
                    init_steps = init_wp_steps
                else:
                    wp_init = I
                    init_steps = []
                s3 = Solver()
                s3.add(Pre, Not(wp_init))
                init_ok      = s3.check() == unsat
                init_cex     = s3.model() if not init_ok else None

                st.subheader("Ergebnis")
                c1, c2, c3 = st.columns(3)
                with c1:
                    (st.success if init_ok    else st.error)(("✅" if init_ok    else "❌") + " Init\nPre ⊨ WP(init, I)")
                with c2:
                    (st.success if pres_ok    else st.error)(("✅" if pres_ok    else "❌") + " Erhaltung\nI ∧ B ⊨ WP(body, I)")
                with c3:
                    (st.success if conseq_ok  else st.error)(("✅" if conseq_ok  else "❌") + " Konsequenz\nI ∧ ¬B ⊨ Q")

                # ── Prüfungs-Klassifizierung (Aufgabe 3) ───────────────────
                if init_ok and pres_ok and conseq_ok:
                    st.success("🎉 **Inductive Invariant** — alle 3 Checks ✅. Hoare-Beweis vollständig.")
                elif not init_ok:
                    st.error(
                        "❌ **Neither (kein Invariant)** — Init-Check fehlgeschlagen.\n\n"
                        "Der Gegenbeispiel-Zustand erfüllt Pre, aber I gilt nicht nach dem Init-Code → "
                        "I ist FALSCH an einem erreichbaren Zustand."
                    )
                elif not pres_ok:
                    st.warning(
                        "⚠️ **Non-inductive Invariant** (wahrscheinlich) — Erhaltungs-Check fehlgeschlagen.\n\n"
                        "Init ✅ — I gilt am Anfang. Erhaltung ❌ — Gegenbeispiel-Zustand existiert.\n\n"
                        "👉 Prüfe manuell: Ist der Gegenbeispiel-Zustand **erreichbar**?\n"
                        "- Nicht erreichbar → **Non-inductive Invariant** (I gilt für alle erreichbaren Zustände)\n"
                        "- Erreichbar → **Neither** (I ist an einem erreichbaren Zustand falsch)"
                    )

                # ── Prüfungsbeweis ──────────────────────────────────────────
                with st.expander("📝 Prüfungsbeweis generieren (Hoare-Annotierung)", expanded=(init_ok and pres_ok and conseq_ok)):
                    st.caption("Erzeugt den vollständigen Beweis mit Regelangaben — direkt für Prüfungsantwort.")
                    full_prog = (inv_init.strip() + "\n" + f"while {inv_B}:\n" +
                                 "\n".join("    " + l for l in inv_body.strip().splitlines()))
                    proof_lines = _generate_hoare_proof(
                        code=full_prog,
                        invariant_str=inv_I,
                        pre_str=inv_pre,
                        post_str=inv_Q,
                        vars_str=inv_vars,
                    )
                    for ln in proof_lines:
                        st.markdown(ln)

                with st.expander("WP-Derivation: Schleifenkörper → I"):
                    st.write(f"**Start (I):** `{I}`")
                    for var_name, expr_str, result in body_steps:
                        st.write(f"← `{var_name} := {expr_str}` → `{result}`")
                    st.markdown(f"**WP(body, I) = `{wp_body}`**")

                with st.expander("WP-Derivation: Init-Code → I"):
                    st.write(f"**Start (I):** `{I}`")
                    for step in init_steps:
                        st.markdown(step)
                    st.markdown(f"**WP(init, I) = `{wp_init}`**")

                def show_cex(label, model):
                    if model:
                        with st.expander(f"Gegenbeispiel: {label}"):
                            for d in model.decls():
                                st.write(f"  `{d.name()}` = `{model[d]}`")

                show_cex("Init schlägt fehl", init_cex)
                show_cex("Erhaltung schlägt fehl", pres_cex)
                show_cex("Konsequenz schlägt fehl", conseq_cex)

            except Exception as e:
                st.error(f"Fehler: {e}")
                st.code(traceback.format_exc())

    else:  # WP-Kalkulator
        st.markdown("**Berechnet WP schrittweise (rückwärts) für eine Folge von Zuweisungen.**")
        col1, col2 = st.columns(2)
        with col1:
            wp_vars = st.text_input("Integer-Variablen", value="x, y", key="wp_vars")
            wp_pre  = st.text_input("Vorbedingung Pre", value="x >= 1", key="wp_pre")
        with col2:
            wp_post = st.text_input("Nachbedingung Q", value="y >= 1", key="wp_post")
        wp_code = st.text_area("Anweisungen (eine Zuweisung pro Zeile: var = expr)",
                               value="y = x\nx = x - 1", height=120, key="wp_code")

        if st.button("WP berechnen", type="primary", key="wp_calc"):
            try:
                from z3 import Int, And, Or, Not, Solver, sat, unsat, substitute, Implies

                vars_dict = {}
                for v in wp_vars.split(","):
                    v = v.strip()
                    if v:
                        vars_dict[v] = Int(v)
                z3ns = {**vars_dict, "And": And, "Or": Or, "Not": Not, "Implies": Implies}

                Q   = eval(wp_post, z3ns)
                Pre = eval(wp_pre,  z3ns)

                assignments = []
                for line in wp_code.strip().splitlines():
                    line = line.strip()
                    if not line or "=" not in line:
                        continue
                    lhs, rhs = line.split("=", 1)
                    assignments.append((lhs.strip(), rhs.strip()))

                st.subheader("WP-Derivation (rückwärts)")
                current = Q
                st.markdown(f"**Q = `{Q}`**")
                steps = []
                for var_name, expr_str in reversed(assignments):
                    var_z3  = vars_dict[var_name]
                    expr_z3 = eval(expr_str, z3ns)
                    new     = substitute(current, (var_z3, expr_z3))
                    steps.append((var_name, expr_str, new))
                    current = new

                for var_name, expr_str, result in reversed(steps):
                    st.markdown(f"← `{var_name} := {expr_str}` → **`{result}`**")

                st.divider()
                st.markdown(f"**WP(S, Q) = `{current}`**")

                s = Solver()
                s.add(Pre, Not(current))
                if s.check() == unsat:
                    st.success(f"✅ Pre ⊨ WP(S,Q) — Beweis korrekt!")
                else:
                    st.error("❌ Pre ⊭ WP(S,Q)")
                    m = s.model()
                    st.markdown("Gegenbeispiel:")
                    for d in m.decls():
                        st.write(f"  `{d.name()}` = `{m[d]}`")

            except Exception as e:
                st.error(f"Fehler: {e}")
                st.code(traceback.format_exc())

    st.divider()
    st.subheader("🧮 Hoare VC-Generator für if/else-Programme")
    st.caption(
        "Kein LLM — 100% deterministisch. Berechnet WP(S, Post) rückwärts für "
        "Sequenzen und if/else-Verzweigungen und prüft `Pre ⊨ WP(S, Post)` mit Z3."
    )

    vc_col_l, vc_col_r = st.columns([1, 1])
    with vc_col_l:
        vc_vars  = st.text_input("Integer-Variablen (kommagetrennt)", value="x, y, z", key="vc_vars")
        vc_pre   = st.text_input("Vorbedingung Pre", value="x >= 0", key="vc_pre")
        vc_post  = st.text_input("Nachbedingung Post", value="y >= 0", key="vc_post")
    with vc_col_r:
        vc_prog  = st.text_area(
            "Programm (Python-Syntax: Zuweisungen + if/else, keine while-Schleifen)",
            value=textwrap.dedent("""\
                if x >= 0:
                    y = x
                else:
                    y = -x
            """),
            height=140,
            key="vc_prog",
        )

    if st.button("VCs erzeugen & prüfen ✓", type="primary", key="vc_btn"):
        try:
            from z3 import Int, And, Or, Not, Solver, sat, unsat, Implies

            vars_dict = {}
            for v in vc_vars.split(","):
                v = v.strip()
                if v:
                    vars_dict[v] = Int(v)
            z3ns = {**vars_dict, "And": And, "Or": Or, "Not": Not, "Implies": Implies}

            prog_tree = ast.parse(textwrap.dedent(vc_prog))
            post_z3 = eval(vc_post, z3ns)
            pre_z3  = eval(vc_pre,  z3ns)

            steps = []
            steps.append(f"**Post = `{post_z3}`**")
            wp_result = _wp_of_stmts(prog_tree.body, post_z3, vars_dict, z3ns, steps, depth=0)

            st.subheader("WP-Derivation (rückwärts)")
            for s in steps:
                st.markdown(s)
            st.markdown(f"---\n**WP(S, Post) = `{wp_result}`**")

            solver = Solver()
            solver.add(pre_z3, Not(wp_result))
            check = solver.check()

            st.divider()
            st.subheader("Verifikationsbedingung (VC)")
            st.markdown(f"**VC:** `Pre ⊨ WP(S, Post)`  ≡  `{pre_z3}  ⊨  {wp_result}`")

            if check == unsat:
                st.success("✅ VC gilt — Hoare-Tripel `{Pre} S {Post}` ist korrekt!")
            elif check == sat:
                st.error("❌ VC gilt NICHT")
                cex = solver.model()
                with st.expander("Gegenbeispiel"):
                    for d in cex.decls():
                        st.write(f"  `{d.name()}` = `{cex[d]}`")
            else:
                st.warning("Z3 konnte VC nicht entscheiden (UNKNOWN)")

        except Exception as e:
            st.error(f"Fehler: {e}")
            st.code(traceback.format_exc())

    with st.expander("ℹ️ Syntaxhinweise & Beispiele für den VC-Generator"):
        st.markdown(r"""
**Unterstützte Konstrukte:**
- Einfache Zuweisungen: `x = expr`, `y = x + 1`, `z = x * y`
- If-then-else: `if B: ... else: ...`
- Geschachtelte if/else (beliebige Tiefe)
- Sequenzen davon (Zeile für Zeile)

**Nicht unterstützt:** `while`, Funktionen, `for` (dafür den Loop-Invarianten-Checker verwenden)

**WP-Regeln die angewendet werden:**
| Konstrukt | WP-Regel |
|---|---|
| `x = e` | `WP(x:=e, Q) = Q[x←e]` |
| `S1; S2` | `WP(S1;S2, Q) = WP(S1, WP(S2, Q))` |
| `if B: S1 else: S2` | `WP = (B→WP(S1,Q)) ∧ (¬B→WP(S2,Q))` |
| `if B: S1` (kein else) | `WP = (B→WP(S1,Q)) ∧ (¬B→Q)` |

**Beispiel 1 — Absolutwert:**
```python
if x >= 0:
    y = x
else:
    y = -x
```
Pre: `True`, Post: `y >= 0`

**Beispiel 2 — Maximum:**
```python
if x >= y:
    m = x
else:
    m = y
```
Pre: `True`, Post: `And(m >= x, m >= y)`

**Beispiel 3 — Sequenz mit Verzweigung:**
```python
t = x + y
if t > 0:
    r = t
else:
    r = 0
```
Pre: `True`, Post: `r >= 0`
""")

    st.divider()
    st.subheader("🚨 Hoare Triple Counterexample Finder")
    st.caption("Sucht automatisch ein Gegenbeispiel für `{Pre} S {Post}` über WP + Z3.")

    cex_col_l, cex_col_r = st.columns(2)
    with cex_col_l:
        cex_pre = st.text_input("Precondition", value="x >= 0", key="cex_pre")
        cex_post = st.text_input("Postcondition", value="y >= 0", key="cex_post")
    with cex_col_r:
        cex_code = st.text_area(
            "Programm S (Zuweisung/if/else)",
            height=130,
            value="if x >= 0:\n    y = x\nelse:\n    y = -x",
            key="cex_code",
        )

    if st.button("Counterexample suchen", key="hoare_cex_btn", type="secondary"):
        try:
            out = _find_hoare_counterexample(cex_code, cex_pre, cex_post)
            if out.get("found"):
                st.error("❌ Hoare-Tripel verletzt.")
                st.markdown(f"**WP(S, Post):** `{out['wp']}`")
                st.markdown("**Gegenbeispiel:**")
                for k, v in out["counterexample"].items():
                    st.write(f"- `{k} = {v}`")
            else:
                st.success("✅ Kein Gegenbeispiel gefunden (für die unterstützte Fragment-Semantik).")
                st.markdown(f"**WP(S, Post):** `{out['wp']}`")
        except Exception as e:
            st.error(f"Fehler: {e}")
            st.code(traceback.format_exc())

    st.divider()
    st.subheader("🧨 Invariant Falsifier")
    st.caption("Prüft die drei Invarianten-Obligationen und liefert das erste Gegenbeispiel.")

    inv_f_col_l, inv_f_col_r = st.columns(2)
    with inv_f_col_l:
        invf_pre = st.text_input("Pre", value="n >= 0", key="invf_pre")
        invf_inv = st.text_input("Invariant I", value="And(i >= 0, i <= n)", key="invf_inv")
        invf_post = st.text_input("Post", value="i == n", key="invf_post")
    with inv_f_col_r:
        invf_code = st.text_area(
            "Programm mit while",
            height=140,
            value="i = 0\nwhile i < n:\n    i = i + 1",
            key="invf_code",
        )

    if st.button("Invariant falsifizieren", key="inv_falsify_btn", type="secondary"):
        try:
            import ast as _ast, textwrap as _tw
            out = _falsify_loop_invariant(invf_code, invf_inv, invf_pre, invf_post)
            if out.get("error"):
                st.error(out["error"])
            elif out.get("falsified"):
                which = out["which"]
                ce    = out["counterexample"]
                if which == "Erhaltung":
                    st.error(f"❌ Invariante verletzt: **{which}** — I ist nicht induktiv.")
                    # Extract loop body for CE explanation
                    try:
                        tree = _ast.parse(_tw.dedent(invf_code))
                        loop = next(s for s in tree.body if isinstance(s, _ast.While))
                        body_str = "\n".join(_ast.unparse(s) for s in loop.body)
                        cond_str = _ast.unparse(loop.test)
                        exp_lines = _generate_invariant_ce_explanation(
                            body_str, invf_inv, cond_str, ce
                        )
                        for ln in exp_lines:
                            st.markdown(ln)
                    except Exception:
                        for k, v in ce.items():
                            st.write(f"- `{k} = {v}`")
                else:
                    st.error(f"❌ Invariante verletzt: **{which}**.")
                    st.markdown("**Gegenbeispiel:**")
                    for k, v in ce.items():
                        st.write(f"- `{k} = {v}`")
                    if which == "Konsequenz":
                        st.markdown(
                            "_Tipp: I ∧ ¬B ⊭ Post — Invariante zu schwach. "
                            "Stärke I damit Post daraus folgt._"
                        )
                    elif which == "Init":
                        st.markdown(
                            "_Tipp: Pre ⊭ WP(init, I) — Invariante gilt nach der "
                            "Initialisierung nicht. Schwäche I oder passe Pre an._"
                        )
            else:
                st.success("✅ Keine Verletzung gefunden — Invariante korrekt.")
                # Also show the proof
                with st.expander("📝 Prüfungsbeweis anzeigen", expanded=True):
                    proof_lines = _generate_hoare_proof(
                        code=invf_code,
                        invariant_str=invf_inv,
                        pre_str=invf_pre,
                        post_str=invf_post,
                    )
                    for ln in proof_lines:
                        st.markdown(ln)
        except Exception as e:
            st.error(f"Fehler: {e}")
            st.code(traceback.format_exc())
