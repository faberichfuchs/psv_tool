# Exam 1 (June 2023) — Vollständige Lösungen

## Aufgabe 1: Coverage (bereits gelöst via App)
**Testmenge: T = {n=0 (fib(0)=0), n=1 (fib(1)=1)}**

### 1a Control-Flow Coverage
| Kriterium | Erfüllt | Begründung |
|---|---|---|
| Statement Coverage | ✅ YES | Alle Zeilen werden ausgeführt (n=0 deckt while+if, n=1 deckt return b) |
| Decision Coverage | ❌ NO | Decision `(i<=n)||(n==0)` nur `true`-Zweig (n=0 immer true wegen n==0); while-Bedingung nie false für n=0. Decision `if(n==0)` nur true. |
| Branch Coverage | ❌ NO | while-false-Branch fehlt (n=0 loop nie verlassen), 3/4 = 75% |
| MC/DC | ❌ NO | Keine Independence Pair für Subausdrücke |

### 1b Data-Flow Coverage
| Kriterium | Erfüllt |
|---|---|
| all-defs | ❌ NO: (a,Z.7)→Z.6, (b,Z.8)→Z.13 nicht gedeckt (Loop nie iteriert mit n≥2) |
| all-c-uses | ❌ NO: 6/12 |
| all-p-uses | ❌ NO: 1/2 (i:Z.10→Z.6 fehlt) |
| all-c-uses/some-p-uses | ❌ NO |

### 1c Minimale Testmenge
- **all-p-uses/some-c-uses**: Ergänze mit fib(3) → alle Obligations gedeckt außer 1 infeasible
- **MC/DC**: Ergänze mit fib(2) als Independence-Witness für `(i<=n)` subexpression

### 1d Mutation Testing
- Mutant: `i = 1` statt `i = 2`
- **Killtest: n=2, erwarteter Output: fib(2)=1**
  - Original: i=2, Loop: 2≤2 → c=1, a=1, b=1, i=3 → 3≤2 false → return 1
  - Mutant: i=1, Loop: 1≤2 → c=1, a=1, b=1, i=2 → 2≤2 → c=2, a=1, b=2, i=3 → return 2 ≠ 1 ✓ killed

---

## Aufgabe 2: Hoare Logic

**Programm:**
```
{true}
if (s % 2 == 0) { s = s + 1; } else { skip; }
i = 0;
while (i != n) { i = i + 1; s = s + i; }
{s ≥ n + 1}
```

**Loop-Invariante: I = (s ≥ i + 1)**

### Herleitung

**Nach if/else-Block:**
- Falls s gerade: s → s+1 (ungerade), so s ≥ 1
- Falls s ungerade: skip, s ≥ 1 (da s ∈ N₀ und ungerade)
- Nachbedingung if/else: `s ≥ 1 ∧ s ungerade`
*Regel: if/else Hoare-Regel (Fallunterscheidung)*

**Nach i = 0:**
- s ≥ 1 ∧ i = 0 → s ≥ i + 1 = 1 ✓
*Regel: Zuweisungsregel rückwärts: {Q[0/i]} i=0 {Q}*

**Invariante I = s ≥ i + 1:**

**(1) Initiation** (Pre → I nach Prefix): 
- s ≥ 1 ∧ i = 0 ⊨ s ≥ 0 + 1 ✓

**(2) Erhaltung** `{I ∧ (i≠n)} i=i+1; s=s+i {I}`:
- WP(s=s+i, s≥i+1) = s+i≥i+1 (nach i=i+1 gilt i'=i+1)
  → s + (i+1) ≥ (i+1) + 1 = i+2 ↔ s ≥ 1
- WP(i=i+1, s≥1) = s≥1
- Zu zeigen: I ∧ i≠n ∧ i≥0 ⊨ s≥1
  - Aus I: s ≥ i+1 ≥ 0+1 = 1 (da i ≥ 0 in N₀) ✓
*Regel: Sequenz- und Zuweisungsregel*

**(3) Konsequenz** (Exit: I ∧ ¬(i≠n) → Post):
- I ∧ i=n ⊨ s ≥ i+1 = n+1 ✓
*Regel: Konsequenzregel (Stärkung der Vorbedingung)*

**Z3-Verifikation:** Alle 3 Checks bestätigt (keine Gegenbeispiele gefunden).

---

## Aufgabe 3: Invariants

**Programm:** `i=0; s=1; while (i≠n) { i=i+1; s=s+i; }`
**Reachable states:** i=k, s=1+k(k+1)/2 nach k Iterationen.

### (s ≥ 2·i) → **Non-inductive Invariant**
- **Invariant:** s=1+k(k+1)/2 ≥ 2k für alle k≥0 ✓ (per Induktion)
- **Nicht induktiv:** CE mit i=0, s=0 (0≥0 ✓), n=1, i≠n ✓.
  Nach Body: i=1, s=1. Check: 1≥2*1=2? **NEIN** ✗
  (Zustand i=0,s=0 ist nicht erreichbar, daher Invariante korrekt, aber nicht induktiv)

### (s ≠ i) → **Non-inductive Invariant**
- **Invariant:** s=i hätte 1+k(k+1)/2=k → k²-k+2=0, Diskriminante -7<0. Kein k-Lösung ✓
- **Nicht induktiv:** CE mit i=1, s=0 (0≠1 ✓), n=0 (Fehler: n=0 aber i=1≠0=n → Loop läuft).
  Nach Body: i=2, s=0+2=2. Check: 2≠2? **NEIN** ✗
  (i=1,s=0 nicht erreichbar)

### (2·i < s) → **Neither (kein Invariant)**
- **Kein Invariant:** Reachable state i=2, s=4: 2·2=4 < 4? **NEIN** ✗
  (nach 2 Iterationen: i=2, s=1+1+2=4; 4<4 false)

---

## Aufgabe 4: Temporal Logic

**Kripke-Struktur:** s0(a)→s1, s1(b)→{s1,s2}, s2(a)→s1
(Inititalzustand s0; s1 hat Selbstschleife)

### 4a: CTL-Formeln (von App bestätigt)

| Formel | Gültig in |
|---|---|
| **EG a** | {} (leer) — jeder Pfad trifft irgendwann s1(b), daher kein unendlicher Pfad mit immer a |
| **EG F a** | {s0, s1, s2} — von jedem Zustand gibt es Pfad s→s1→s2(a)→... der a unendlich oft sieht |
| **A(a ∧ X b)** | {s0, s2} — a gilt in s0 und s2; alle Nachfolger haben b (nur Nachfolger: s1 mit b) |
| **A(a U b)** | {s0, s1, s2} — s1 hat b (trivial); s0,s2 haben a und nächster Schritt ist s1(b) |
| **E(b U a)** | {s0, s1, s2} — s0,s2 haben a (trivial mit i=0); s1→s2(a) mit b@s1 ✓ |

### 4b: Tableaux für EG(EX a)

**Subformel 1: EX a** = {s: ∃t∈succ(s): a∈L(t)}
- s0: succ={s1}, L(s1)={b}, a∉L(s1) → **NEIN**
- s1: succ={s1,s2}, L(s2)={a} → **JA**
- s2: succ={s1}, a∉L(s1) → **NEIN**
- **EX a = {s1}**

**Subformel 2: EG(EX a)** = νZ. (EX a) ∩ {s: ∃t∈succ(s): t∈Z}

Fixpunkt-Iteration:
- Z₀ = {s0,s1,s2} (alle Zustände)
- Z₁ = {s1} ∩ EX(Z₀) = {s1} ∩ {s0,s1,s2} = **{s1}**
- Z₂ = {s1} ∩ EX(Z₁) = {s1} ∩ {s0,s1,s2} = **{s1}** (EX{s1}=alle, da s0→s1, s1→s1, s2→s1)
- Z₂ = Z₁ → **Fixpunkt erreicht**

**EG(EX a) = {s1}**

---

## Aufgabe 5: Decision Procedures

### 5a: SAT (von App bestätigt)
**Formel:** XOR-Kette (x1⊕x2, x2⊕x3, ..., x6⊕x7) + 4 Klauseln für x1,x6,x7

**Analyse:** Die ersten 12 Klauseln erzwingen genau-ein-true in jedem aufeinanderfolgenden Paar.
Das ergibt 2 mögliche Belegungen:
- x1=T: x2=F, x3=T, x4=F, x5=T, x6=F, x7=T → Spezialklauseln: (-T∨-T∨F)=F ✗
- x1=F: x2=T, x3=F, x4=T, x5=F, x6=T, x7=F → alle 4 Spezialklauseln erfüllt ✓

**SATISFIABLE** — einzige Lösung:
| x1 | x2 | x3 | x4 | x5 | x6 | x7 |
|----|----|----|----|----|----|----|
| F  | T  | F  | T  | F  | T  | F  |

**DPLL-Trace:**
- L0: Entscheide x1=T
- L1: Unit Propagation → x2=F,x3=T,x4=F,x5=T,x6=F,x7=T
- L1: Konflikt (¬x1∨¬x7∨x6) = F
- L0: Backtrack, versuche x1=F
- L1: Unit Propagation → x2=T,x3=F,x4=T,x5=F,x6=T,x7=F → SAT ✓

### 5b: BDD für (¬(a⇔b)) ∧ (¬(b⇔c)) ∧ (¬(c⇔d))
= (a XOR b) AND (b XOR c) AND (c XOR d)

Nur 2 erfüllende Belegungen: (T,F,T,F) und (F,T,F,T)

BDD mit Variablenordnung a,b,c,d:
```
        a
      /   \
    F       T
    |       |
    b       b
   / \     / \
  T   F   F   T
  |   |   |   |
  c   c   c   c
 / \ / \ / \ / \
F  T T  F T  F F  T
|  | |  | |  | |  |
d  d d  d d  d d  d
↓  ↓ ↓  ↓ ↓  ↓ ↓  ↓
0  1 0  0 0  0 0  0
(F,T,F,T)=1, (T,F,T,F)=1, rest=0
```

Kompakt (Shared BDD, Größe O(n)):
- Root: a
- a=F → b=T → c=F → d=T → **1** (else → **0**)
- a=T → b=F → c=T → d=F → **1** (else → **0**)

Größe: 4 innere Knoten + 2 terminale = **O(n)** ✓

---

## Aufgabe 6: General Questions
| Statement | Antwort | Begründung |
|---|---|---|
| Any assertion implied by an invariant is also an invariant | **TRUE** | Invariant hält in allen erreichbaren Zuständen; wenn P Invariante und P⊨Q, dann Q ebenfalls in allen erreichbaren Zuständen |
| Any CTL formula with only A quantifiers can be reformulated as LTL | **TRUE** | A-CTL Formeln entsprechen LTL-Formeln (AGp↔Gp, AFp↔Fp, AXp↔Xp, A[pUq]↔pUq) |
| If program terminates on all inputs, statement coverage can always be achieved | **FALSE** | Totes Code (z.B. `if(false){...}`) ist nie ausführbar, auch wenn Programm terminiert |
