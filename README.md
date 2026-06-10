# PSV Prüfungsassistent

Streamlit-App zur Vorbereitung auf die Prüfung **Programm- und Systemverifikation (184.741)** an der TU Wien.  
Alle Berechnungen sind deterministisch (Z3, kein LLM) — das Tool löst keine Aufgaben für dich, aber verifiziert deine Antworten und erklärt warum etwas nicht stimmt.

## Features

| Tab | Was es macht |
|---|---|
| **Coverage** | C- oder Python-Code analysieren: Statement, Decision, Branch, Condition, MC/DC, Data-Flow (all-defs/c-uses/p-uses). Inkl. Prüfungs-Erklärung pro Kriterium. |
| **SAT / Z3** | SAT-Solver (DPLL), SMT/EUF-Satisfiability, CDCL-Cheatsheet mit Algorithmus-Schritten |
| **Hoare & Invariants** | Loop-Invariante prüfen (Init/Erhaltung/Konsequenz), WP-Kalkulator, VC-Generator für if/else-Programme |
| **Temporal Logic** | CTL-Formelauswertung auf Kripke-Strukturen (Tableau-Algorithmus) |
| **Theory Chat** | RAG-basierter Chat über Vorlesungsfolien (benötigt `chroma_db/`) |

---

## Setup

### Voraussetzungen

- Python 3.11+
- Git

### Installation

```bash
git clone https://github.com/faberichfuchs/psv_tool.git
cd psv_tool
pip install -r requirements.txt
```

### App starten

```bash
python -m streamlit run app.py
```

Öffnet sich automatisch unter `http://localhost:8501`.

---

## Verwendung

### Coverage (Aufgabe 1)

1. Sprache oben wählen: **Python** oder **C / C++**
2. Code einfügen (C-Code wird automatisch nach Python transpiliert)
3. Testfälle eingeben — eine pro Zeile, z.B.:
   ```
   is_coprime(0, 0)
   is_coprime(2, 3)
   ```
4. Funktionsname eingeben → **Analysieren**

Die App zeigt Statement/Decision/Branch/Condition/MC/DC-Prozentsätze und klappt automatisch eine **Prüfungs-Erklärung** auf, wenn ein Kriterium nicht erfüllt ist.

**C-Transpiler-Hinweis:** Mehrzeiligen C-Code eingeben (nicht alles in einer Zeile). Multi-Variablen-Deklarationen wie `unsigned a = n1, b = n2;` werden korrekt auf zwei Zeilen aufgeteilt.

### Hoare & Loop-Invarianten (Aufgabe 2 & 3)

Modus **"Loop-Invariante prüfen"**:

| Feld | Beispiel |
|---|---|
| Variablen | `m, n` |
| Vorbedingung Pre | `True` oder `n >= 0` |
| Loop-Invariante I | `(m + n) % 2 == 0` |
| Schleifenbedingung B | `And(m != 0, n != 0)` |
| Nachbedingung Q | `m % 2 == 0` |
| Init-Code | Zuweisungen **oder if/else** in Python-Syntax |
| Schleifenkörper | `m = m - 1` / `n = n - 1` |

**Syntax:** Z3-Ausdrücke — `And(...)`, `Or(...)`, `Not(...)`, `Implies(...)`, `True`, `False`.  
Init-Code für Z3-konforme Konstanten: `a = a - a + 1` statt `a = 1`.

Die App klassifiziert automatisch: **Inductive Invariant** / **Non-inductive** / **Neither**.

### Temporal Logic (Aufgabe 4)

Kripke-Struktur eingeben:
```
s0: a -> s0, s1
s1: a -> s2
s2: b -> s2
```
Danach CTL-Formeln eingeben, z.B. `EG(b)`, `AF(AG(b))`, `A(a U b)`.

### SAT / EUF (Aufgabe 5)

- **SAT:** Z3-Formel eingeben, z.B. `And(Or(x1, x2), Or(Not(x1), Not(x2)))`
- **EUF:** Gleichungen mit uninterpretierten Funktionen, z.B. `And(f(a) == f(b), a != b)`

### Theory Chat (optional — lokales LLM)

Der Theory-Chat-Tab beantwortet Theorie-Fragen über ein lokales LLM, das auf deinen Vorlesungsfolien basiert.

**Einmalige Einrichtung:**

**1. Ollama installieren:** https://ollama.com/download

**2. Modelle herunterladen**
```bash
ollama pull nomic-embed-text   # Embedding-Modell (~274 MB)
ollama pull qwen2.5:14b        # Chat-Modell (~9 GB, empfohlen)
# Alternativ kleiner: ollama pull qwen2.5:7b  (~4.5 GB)
```

**3. Zusätzliche Python-Pakete installieren**
```bash
pip install llama-index llama-index-vector-stores-chroma \
            llama-index-embeddings-ollama llama-index-llms-ollama
```

**4. Vorlesungsfolien ablegen**

PDFs in den Ordner `material/` legen (Unterordner erlaubt). Der Pfad ist in `tools/shared.py` als `MATERIAL_DIR` konfiguriert — bei Bedarf anpassen.

**5. Index aufbauen** *(einmalig, ~2–5 Min)*
```bash
python scripts/build_index.py
```
Erzeugt `chroma_db/` im Projektverzeichnis (in `.gitignore`, wird nicht gepusht).

**6. Ollama beim App-Start laufen lassen**
```bash
ollama serve   # im Hintergrund starten
python -m streamlit run app.py
```

---

## Tests ausführen

```bash
# Schnelle Unit-Tests (~3s)
pytest tests/ -m "not slow"

# Vollständige E2E-Tests gegen laufende App (~6min, App muss auf Port 8502 laufen)
python -m streamlit run app.py --server.port 8502 &
pytest tests/ -m slow
```

---

## Projektstruktur

```
app.py              # Streamlit-Einstiegspunkt, Sidebar-Cheatsheet
tools/
  coverage.py       # Coverage-Tab
  hoare.py          # Hoare & Invarianten-Tab
  sat.py            # SAT/Z3-Tab
  temporal.py       # Temporal Logic-Tab
  chat.py           # Theory Chat-Tab
  shared.py         # Gemeinsame Helpers: C-Transpiler, WP-Kalkül, Z3-Utils
tests/
  test_e2e_exams.py # 122 E2E-Tests (Playwright) gegen alle 7 Altprüfungen
  test_exam*.py     # Unit-Tests pro Prüfung
scripts/
  exam*_loesungen.md  # Händische Musterlösungen zu den Altprüfungen
```
