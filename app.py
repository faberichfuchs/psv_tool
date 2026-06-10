"""
PSV Prüfungsassistent — Multi-Tool Streamlit App
Run: python -m streamlit run app.py
"""

import streamlit as st

from tools.shared import MATERIAL_DIR, CHROMA_DIR, COLLECTION
from tools import coverage, sat, hoare, temporal, chat

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="PSV Prüfungsassistent", page_icon="🔍", layout="wide")
st.title("PSV Prüfungsassistent")

# ── Sidebar: Prüfungstheorie-Cheatsheet ────────────────────────────────────
with st.sidebar:
    with st.expander("📚 Prüfungs-Theorie (Aufg. 6)", expanded=False):
        st.markdown("""
**Coverage-Hierarchie (Subsumption):**
`MC/DC ⊃ Condition ⊃ Decision = Branch ⊃ Statement`

**Data-Flow-Hierarchie:**
- `all-p-uses/some-c-uses` ⊃ `all-defs`
- `all-c-uses/some-p-uses` ⊃ `all-defs`
- `all-p-uses/some-c-uses` **KEIN** fixes Verhältnis zu `all-c-uses/some-p-uses`
- Ohne c-uses: `all-p-uses` ≡ `all-p-uses/some-c-uses` (vakuös gleich)

---

**Hoare Partielle Korrektheit:**
- `{P}C{Q}` vakuös wahr wenn C **nicht terminiert** (P nie als Vorbedingung für Q geprüft)
- `{false}C{Q}`: **immer** wahr (Vorbedingung nie erfüllbar)
- `{P}C{false}`: wahr **gdw. C divergiert** wenn P gilt
- Totale Korrektheit verlangt zusätzlich Terminierung

---

**Induktive Invarianten:**
- Zu jeder (auch nicht-induktiven) Invariante I existiert eine **induktive** Verstärkung I* ⊆ I (z.B. erreichbare Zustände ∩ I)
- *Ausnahme:* `while(false){}` — alle Formeln sind induktiv (Erhaltung vakuös, da Loop-Body nie ausgeführt)
- Nicht-induktive Invariante I: Gegenbeispiel-Zustand ist **nicht erreichbar**

---

**LTL vs CTL:**
- `GFp` ("infinitely often p") ✅ LTL, ≈ `AG(AF p)` in CTL
- `AG(p → EF q)` ❌ **nicht** in LTL (EF = existentieller Pfadquantor)
- `AG(p → AF q)` ✅ in LTL als `G(p → F q)`
- "p tritt unendlich oft auf" = `GF p` in LTL ✅
- LTL ∩ CTL: nur Formeln ohne EX/EF/EG/EU oder AX/AF/AG/AU allein; Mischung eingeschränkt

---

**EUF / Gleichheitslogik:**
- Kongruenz: `a = b → f(a) = f(b)` (immer!)
- **Kleine Modell-Eigenschaft:** n Variablen → Modellgröße ≤ n
- Entscheidbar in polynomieller Zeit

---

**SAT / CDCL:**
- 2-CNF (max 2 Literale/Klausel) lösbar in O(n) — aber **nicht alle** 2-CNF sind SAT: `(x) ∧ (¬x)` ist UNSAT
- CDCL = DPLL + gelernte Klauseln + **nicht-chronologisches** Backtracking
- **1. UIP:** erstes Literal das auf **allen** Pfaden von der Entscheidung zum Konflikt liegt
- Lernklausel via Resolution: iteriere Konflikrklausel, resolvier gegen Antezedenten bis nur 1 Literal der aktuellen Ebene übrig
- Backjump-Level = max. Entscheidungsebene der **Nicht-UIP**-Literale in der Lernklausel

---

**Äquivalente Mutanten:**
- Kein Killtest existiert wenn Mutant **semantisch äquivalent** ist
- Oft bei: `a - b` → `a % b` (bei Euklidischem Algorithmus), `s ≤ n` als zusätzliche Loop-Bedingung (frühzeitiger Abbruch hat gleiche Ausgabe)
""")
    with st.expander("🗺️ Prüfungs-Workflow", expanded=False):
        st.markdown("""
**Aufg. 1 (Coverage):** Code + Tests → Tab Coverage → Statement/Branch/Decision/Condition/MC/DC ablesen + Data-Flow

**Aufg. 2 (Hoare):** Invariante vorschlagen → Tab Hoare → Invariante prüfen → alle 3 Checks ✅ = fertig

**Aufg. 3 (Loop-Invarianten):** Jede Formel einzeln → Hoare Tab → Init+Erhaltung+Konsequenz → Klassifizierung:
- Alle 3 ✅ = Inductive Invariant
- Init ✅, Erhaltung ❌ (CE nicht erreichbar) = Non-inductive Invariant
- Init ❌ (CE erreichbar) = Neither

**Aufg. 4 (CTL):** Kripke eingeben → Tab Temporal → Formel eingeben → gilt/gilt nicht + Tableau-Schritte

**Aufg. 5a (SAT/CDCL):** Klauseln → Tab SAT/Z3 → CDCL-Trace → SAT/UNSAT + Belegung verifizieren (Trace manuell)

**Aufg. 5b (EUF):** Constraints → Tab SAT/Z3 → SMT/EUF oder Congruence Closure → SAT/UNSAT

**Aufg. 6 (T/F):** Theorie-Cheatsheet oben ↑ verwenden
""")

tabs = st.tabs(["📊 Coverage", "🔢 SAT / Z3", "📐 Hoare & Invariants", "⏱ Temporal Logic", "💬 Theory Chat"])

with tabs[0]:
    coverage.render()

with tabs[1]:
    sat.render()

with tabs[2]:
    hoare.render()

with tabs[3]:
    temporal.render()

with tabs[4]:
    chat.render()
