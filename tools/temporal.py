"""
Tab 3 — Temporal Logic (CTL / LTL)
"""

import traceback

import streamlit as st

from tools.shared import (
    CHROMA_DIR,
    COLLECTION,
    _ctl_check,
    _ctl_tableaux_explain,
    _parse_ctl,
    _tokenize_ctl,
    _parse_ltl,
    _ltl_check_lasso,
)


def render():
    st.header("Temporal Logic (CTL / LTL)")

    with st.expander("📋 Temporal Logic Cheatsheet", expanded=True):
        st.markdown(r"""
**CTL-Operatoren:**
| Op | Bedeutung |
|---|---|
| `EX φ` | Es gibt einen Nachfolger wo φ gilt |
| `AX φ` | In allen Nachfolgern gilt φ |
| `EF φ` | Es gibt einen Pfad wo φ irgendwann gilt |
| `AF φ` | Auf allen Pfaden gilt φ irgendwann |
| `EG φ` | Es gibt einen Pfad wo φ immer gilt |
| `AG φ` | Auf allen Pfaden gilt φ immer |
| `E[φ U ψ]` | Es gibt Pfad: φ gilt bis ψ |
| `A[φ U ψ]` | Alle Pfade: φ gilt bis ψ |

**Eingabe-Syntax für den Checker:**
- Atome: kleingeschriebene Namen, z.B. `p`, `q`, `ready`
- Operatoren: `!` (not), `&` (and), `|` (or), `->` (implies)
- Modale Ops: `EX`, `AX`, `EF`, `AF`, `EG`, `AG`, `E[φ U ψ]`, `A[φ U ψ]`
- Beispiele: `AG(p -> EF q)`, `EG !p`, `A[p U q]`, `AX(EF p)`

**Deterministischer LTL-Trace-Checker (Lasso-Pfad):**
- Operatoren: `X` (next), `F` (eventually), `G` (globally), `U` (until), plus `!`, `&`, `|`, `->`
- Semantik auf einem letztlich periodischen Pfad (Loop-Start einstellbar)
- Beispiele: `G(p -> F q)`, `X p`, `(p U q)`

**Kripke-Struktur:** M = (S, S₀, R, L)
- S: Zustandsmenge
- S₀: Anfangszustände
- R: Übergangsrelation (total: jeder Zustand braucht mind. einen Nachfolger)
- L: Labeling-Funktion
""")

    # ── Deterministic CTL Model Checker ──────────────────────────────────
    st.subheader("🔧 Deterministischer CTL Model Checker")
    st.caption("Kein LLM — 100% deterministisch. Fixed-point Algorithmen, state-by-state Auswertung.")

    col_l, col_r = st.columns(2)

    with col_l:
        ctl_states_in = st.text_input(
            "Zustände (kommagetrennt)",
            value="s0, s1, s2",
            key="ctl_states"
        )
        ctl_init_in = st.text_input(
            "Anfangszustände (kommagetrennt)",
            value="s0",
            key="ctl_init"
        )
        ctl_trans_in = st.text_area(
            "Übergänge (eine pro Zeile: src -> dst)",
            value="s0 -> s1\ns1 -> s2\ns2 -> s0",
            height=110,
            key="ctl_trans"
        )

    with col_r:
        ctl_labels_in = st.text_area(
            "Labels (eine pro Zeile: state: ap1, ap2 — leer lassen wenn keine)",
            value="s0: p\ns1: q\ns2:",
            height=110,
            key="ctl_labels"
        )
        ctl_formula_in = st.text_input(
            "CTL-Formel",
            value="AG(p → EF q)",
            key="ctl_formula"
        )

    if st.button("Formel prüfen ✓", type="primary", key="ctl_check_btn"):
        try:
            states_list = [s.strip() for s in ctl_states_in.split(",") if s.strip()]
            states_set  = set(states_list)
            init_list   = [s.strip() for s in ctl_init_in.split(",") if s.strip()]

            transitions = []
            for line in ctl_trans_in.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                if "->" not in line:
                    raise ValueError(f"Ungültiger Übergang (kein '->'): '{line}'")
                a, b = line.split("->", 1)
                a, b = a.strip(), b.strip()
                if a not in states_set:
                    raise ValueError(f"Unbekannter Zustand in Übergang: '{a}'")
                if b not in states_set:
                    raise ValueError(f"Unbekannter Zustand in Übergang: '{b}'")
                transitions.append((a, b))

            succ_count = {s: 0 for s in states_set}
            for a, _ in transitions:
                succ_count[a] += 1
            deadlocks = [s for s in states_list if succ_count[s] == 0]
            if deadlocks:
                raise ValueError(
                    "Übergangsrelation ist nicht total. "
                    f"Folgende Zustände haben keinen Nachfolger: {deadlocks}"
                )

            labels = {}
            for line in ctl_labels_in.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                if ":" not in line:
                    raise ValueError(f"Ungültige Label-Zeile (kein ':'): '{line}'")
                state, aps = line.split(":", 1)
                state = state.strip()
                ap_set = {ap.strip() for ap in aps.split(",") if ap.strip()}
                labels[state] = ap_set

            for s in states_set:
                if s not in labels:
                    labels[s] = set()

            tokens = _tokenize_ctl(ctl_formula_in)
            ast_node = _parse_ctl(tokens)

            steps = []
            evaluate_fn, _, _ = _ctl_check(states_set, transitions, labels, init_list)
            sat_set = evaluate_fn(ast_node, steps)

            st.subheader("Ergebnis")

            cols = st.columns(len(states_list))
            for i, s in enumerate(states_list):
                holds = s in sat_set
                is_init = s in init_list
                label_str = ", ".join(sorted(labels[s])) if labels[s] else "∅"
                badge = "✅" if holds else "❌"
                init_badge = " ★" if is_init else ""
                with cols[i]:
                    if holds:
                        st.success(f"{badge} **{s}**{init_badge}\nL={{{label_str}}}")
                    else:
                        st.error(f"{badge} **{s}**{init_badge}\nL={{{label_str}}}")

            st.caption("★ = Anfangszustand")

            init_ok = all(s in sat_set for s in init_list)
            if init_ok:
                st.success(f"✅ **Formel gilt** in allen Anfangszuständen: {init_list}")
            else:
                failed = [s for s in init_list if s not in sat_set]
                st.error(f"❌ **Formel gilt NICHT** in Anfangszustand(en): {failed}")

            with st.expander("Schritt-für-Schritt Auswertung (Fixed-point)"):
                for op_label, result_set in steps:
                    sorted_states = sorted(result_set)
                    st.markdown(f"**{op_label}** → gilt in: `{{{', '.join(sorted_states) if sorted_states else '∅'}}}`")

            with st.expander("📝 Tableaux-Beweis (Prüfungsformat)", expanded=False):
                st.caption("Vollständige Tableaux-Herleitung mit Fixpunkt-Schritten — direkt für Prüfungsantwort.")
                try:
                    _, tableau_lines = _ctl_tableaux_explain(
                        states_list, transitions, labels, ctl_formula_in
                    )
                    for ln in tableau_lines:
                        st.markdown(ln)
                except Exception as te:
                    st.error(f"Tableaux-Fehler: {te}")

            with st.expander("Kripke-Struktur (Zusammenfassung)"):
                st.markdown(f"**Zustände:** {sorted(states_set)}")
                st.markdown(f"**Anfangszustände:** {init_list}")
                st.markdown(f"**Übergänge:** {transitions}")
                for s in states_list:
                    ap_str = ", ".join(sorted(labels[s])) if labels[s] else "∅"
                    st.markdown(f"  L({s}) = {{{ap_str}}}")

        except Exception as e:
            st.error(f"Fehler: {e}")
            st.code(traceback.format_exc())

    st.divider()
    st.subheader("🔧 Deterministischer LTL Trace Checker (Lasso)")
    st.caption("Kein LLM — 100% deterministisch. Prüft LTL auf einem gegebenen Pfad mit Loop-Start.")

    ltl_col_l, ltl_col_r = st.columns(2)
    with ltl_col_l:
        ltl_path_in = st.text_input(
            "Pfad (Zustandsnamen in Reihenfolge, kommagetrennt)",
            value="s0, s1, s2",
            key="ltl_path",
        )
        ltl_loop_start = st.number_input(
            "Loop-Start-Index (für unendliche Fortsetzung)",
            min_value=0,
            value=0,
            step=1,
            key="ltl_loop_start",
        )

    with ltl_col_r:
        ltl_labels_in = st.text_area(
            "Labels pro Zustand (eine Zeile: state: ap1, ap2)",
            value="s0: p\ns1:\ns2: q",
            height=110,
            key="ltl_labels",
        )
        ltl_formula_in = st.text_input(
            "LTL-Formel",
            value="G(p -> F q)",
            key="ltl_formula",
        )

    if st.button("LTL prüfen ✓", type="primary", key="ltl_check_btn"):
        try:
            path_states = [s.strip() for s in ltl_path_in.split(",") if s.strip()]
            if not path_states:
                raise ValueError("Pfad ist leer")

            state_labels = {}
            for line in ltl_labels_in.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                if ":" not in line:
                    raise ValueError(f"Ungültige Label-Zeile (kein ':'): '{line}'")
                state, aps = line.split(":", 1)
                state = state.strip()
                ap_set = {ap.strip() for ap in aps.split(",") if ap.strip()}
                state_labels[state] = ap_set

            labels_by_pos = [state_labels.get(s, set()) for s in path_states]

            tokens = _tokenize_ctl(ltl_formula_in)
            ltl_ast = _parse_ltl(tokens)
            steps = []
            evaluate_ltl = _ltl_check_lasso(labels_by_pos, int(ltl_loop_start))
            sat_positions = evaluate_ltl(ltl_ast, steps)

            st.subheader("Ergebnis")
            if 0 in sat_positions:
                st.success("✅ Formel gilt am Pfadstart (Position 0)")
            else:
                st.error("❌ Formel gilt NICHT am Pfadstart (Position 0)")

            with st.expander("Positionen im Pfad"):
                for idx, state in enumerate(path_states):
                    labels_str = ", ".join(sorted(labels_by_pos[idx])) if labels_by_pos[idx] else "∅"
                    marker = "★" if idx == int(ltl_loop_start) else ""
                    holds = "✅" if idx in sat_positions else "❌"
                    st.markdown(f"{holds} `[{idx}] {state}`{(' ' + marker) if marker else ''} mit L={{{labels_str}}}")
                st.caption("★ = Loop-Start")

            with st.expander("Schritt-für-Schritt Auswertung (Fixpunkte auf Lasso)"):
                for op_label, pos_set in steps:
                    pos_txt = ", ".join(str(i) for i in sorted(pos_set)) if pos_set else "∅"
                    st.markdown(f"**{op_label}** → gilt an Positionen: `{{{pos_txt}}}`")

        except Exception as e:
            st.error(f"Fehler: {e}")
            st.code(traceback.format_exc())

    st.divider()
    st.subheader("💬 LLM-Hilfe für Temporal Logic")
    st.caption("Für Erklärungen, Tableaux, LTL — wenn der deterministsche Checker nicht reicht")

    if CHROMA_DIR.exists():
        tl_q = st.text_area("Aufgabe (Kripke-Struktur + Formel):", height=150,
                             placeholder="Kripke-Struktur: S={s0,s1,s2}, R={(s0,s1),(s1,s2),(s2,s0)}, L(s0)={p}, L(s1)={q}, L(s2)={}\nPrüfe: AG(p → EF q)")
        debug_tl = st.checkbox("Debug: Quellen anzeigen", key="tl_debug")

        if st.button("LLM Analysieren", type="primary", key="tl_btn"):
            with st.spinner("Analysiere..."):
                try:
                    from chromadb import PersistentClient
                    from llama_index.core import VectorStoreIndex, Settings
                    from llama_index.vector_stores.chroma import ChromaVectorStore
                    from llama_index.embeddings.ollama import OllamaEmbedding
                    from llama_index.llms.ollama import Ollama

                    Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text")
                    Settings.llm = Ollama(model="qwen2.5:14b", request_timeout=180.0,
                                         system_prompt="""Du bist ein PSV-Experte für Temporallogik.
Bei CTL/LTL-Aufgaben:
1. Identifiziere die Kripke-Struktur explizit
2. Evaluiere die Formel state-by-state (zeige für jeden Zustand ob φ gilt)
3. Wende die semantischen Regeln korrekt an
4. Gib ein klares Ja/Nein mit Begründung""")
                    client = PersistentClient(path=str(CHROMA_DIR))
                    collection = client.get_or_create_collection(COLLECTION)
                    vector_store = ChromaVectorStore(chroma_collection=collection)
                    index = VectorStoreIndex.from_vector_store(vector_store)
                    qe = index.as_query_engine(similarity_top_k=5)

                    response = qe.query(f"Temporal Logic Aufgabe:\n{tl_q}")
                    st.markdown(str(response))

                    if debug_tl and hasattr(response, "source_nodes"):
                        with st.expander("Abgerufene Quellen (Rohtext)"):
                            for i, node in enumerate(response.source_nodes):
                                st.markdown(f"**Quelle {i+1}** — {node.metadata.get('folder')}/{node.metadata.get('source')} (Score: {node.score:.3f})")
                                st.text(node.text[:800])
                                st.divider()

                except Exception as e:
                    st.error(f"Fehler: {e}")
    else:
        st.warning("Kein Index gefunden.")
