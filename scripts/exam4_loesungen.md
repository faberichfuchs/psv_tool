# Exam 4 — June 2024 — Lösungen

## Aufgabe 1: Coverage — `is_coprime(n1, n2)`

```python
def is_coprime(n1, n2):
    a, b = n1, n2                         # L1
    if a <= 1 or b <= 1:                  # D0: L2
        return (a == 1 or b == 1)         # D1 (p-use, kein c-use): L3
    while a != b:                         # D2: L5
        if a > b:                         # D3: L6
            a = a - b                     # L7
        else:
            b = b - a                     # L9
        if a == 1 or b == 1:             # D4: L11
            return True                   # L12
    return False                          # L14
```

**Tests:** (0,0)→False, (2,3)→True, (6,2)→False. Note: || not short-circuited.

**Traces:**
- (0,0): a=0,b=0 → D0: (0≤1∨0≤1)=T → L3: (0==1∨0==1)=False
- (2,3): a=2,b=3 → D0=F → while 2≠3=T → D3:2>3=F → b=3-2=1 → D4:(2==1∨1==1)=T → return True
- (6,2): a=6,b=2 → D0=F → iter1: D3:6>2=T→a=4; D4=F → iter2: D3:4>2=T→a=2; D4=F → 2==2=F → return False

### 1a) Control-Flow Coverage

| Kriterium | Ergebnis | Begründung |
|---|---|---|
| Statement Coverage | ✅ | Alle Zeilen erreicht: L3(0,0), L7(6,2), L9(2,3), L12(2,3), L14(6,2) |
| Decision Coverage | ✅ | D0:T/F✓, D2:T/F✓(6,2 exits), D3:T/F✓(6,2→T; 2,3→F), D4:T/F✓(2,3→T; 6,2→F) |
| Branch Coverage | ✅ | Alle Branches (4 Decisions × 2) abgedeckt — identisch mit Decision Coverage |
| MC/DC | ❌ | D0: Atom A=(a≤1): nur bei (0,0) T, aber gleichzeitig B=(b≤1)=T → kein unabhängiger Witness. D4: Atom A=(a==1) immer False. |

**MC/DC Details:**
- D0 (A=(a≤1), B=(b≤1)): Test (0,0)→A=T,B=T; (2,3)→A=F,B=F. Für Independence braucht man z.B. (1,3)→A=T,B=F für Witness von A, und (2,0)→A=F,B=T für Witness von B. Fehlt!
- D4 (A=(a==1), B=(b==1)): B=T bei (2,3) (b→1), aber A=(a==1) nie True. Braucht z.B. (3,2)→a→1 aber b=2.

### 1b) Data-Flow Coverage

Defs: a@L1, a@L7; b@L1, b@L9.  
Note: L3 ist p-use für a,b (laut Aufgabe), kein c-use.

| Kriterium | Ergebnis | Begründung |
|---|---|---|
| all-defs | ✅ | a@L1 → L2(p)✓; a@L7 → L5(p)✓; b@L1 → L2(p)✓; b@L9 → L11(p)✓ |
| all-c-uses | ❌ | (a,L7,L9) fehlt: nach a=a-b muss L9 (b=b-a mit diesem a) ausgeführt werden. Nie im Test-Set. |
| all-p-uses | ❌ | (a,L7,L3) nicht erreichbar (nach L7 kann L3 nicht mehr kommen). Aber: (b,L9,L6) fehlt: nach b=b-a muss L6 (D3: a>b) mit neuem b evaluiert werden. (2,3): nach b@L9=1→D4=T→return, L6 nie wieder. |
| all-p-uses/some-c-uses | ❌ | (all-p-uses nicht erfüllt) |

**Fehlende du-Paare:**
- all-c-uses: `(a, L7, L9)` — nach a=a-b, dann L9 (b=b-a) mit diesem a-Wert. Braucht Test wie (5,3): a=5→a=2(L7), dann b=3>a=2 → L9: b=3-2=1.
- all-p-uses: `(b, L9, L6)` — nach b=b-a, weiterloopen bis D3 erreicht. (2,3): nach L9 sofort D4=T → return. Braucht Test wo nach L9 D4=F und Loop weiter.

### 1c) Minimale Ergänzung

**all-c-uses/some-p-uses:** Ergänze `(5, 3)`:
- a=5,b=3: D0=F → D3:5>3=T → a=2; D4:F → loop: 2≠3=T → D3:2>3=F → b=3-2=1; D4: b==1=T → return True
- Deckt (a,L7,L9): a@L7=2 wird in L9 als c-use (b=3-2) verwendet ✓
- Output: True

| n1 | n2 | Output |
|---|---|---|
| 5 | 3 | true |

**MC/DC:** Ergänze `(1,3)`, `(2,0)`, `(3,2)`:
- (1,3)→D0:1≤1=T,3≤1=F → D0=T; Witness A=(a≤1): (1,3)→T,B=F; (2,3)→F,B=F; D0 flips ✓
- (2,0)→D0:F,B=T → Witness B=(b≤1): (2,0)→A=F,T; (2,3)→A=F,F; D0 flips ✓
- (3,2)→a=3,b=2→D3:T→a=1; D4:a==1=T,b==1=F(b=2) → Witness A=(a==1) for D4 ✓

| n1 | n2 | Output |
|---|---|---|
| 1 | 3 | true |
| 2 | 0 | false |
| 3 | 2 | true |

### 1d) Mutation: `a > b` → `a >= b`

**Kein Killtest existiert.** Der Mutant ist äquivalent zum Original.

**Begründung:** Die Bedingung bei Zeile 6 (`if a > b`) wird nur innerhalb des `while (a != b)`-Loops evaluiert. Der Loop-Guard garantiert `a ≠ b` zu jedem Zeitpunkt der D3-Auswertung. Da `a ≠ b` immer gilt, gilt `(a > b) ≡ (a >= b)` für ganzzahlige Werte. Der Mutant verhält sich identisch — **kein stark killender Test existiert**.

---

## Aufgabe 2: Hoare Logic

```
{true}
if (i < 2) { i = 2; } else { i = 7; }
while (i > 1 && i < 10) { i = i + 1; }
{(i ≠ 1 ∧ i ≠ 11)}
```

**Analyse:** Nach if/else: i=2 (falls i<2) oder i=7 (sonst). Loop inkrementiert i bis i≥10. Exit: i=10 immer. Postcondition: 10≠1 ✓, 10≠11 ✓.

**Invariante: I = (i ≥ 2) ∧ (i ≤ 10)**

Z3-Verifikation: alle 3 Checks ✅

**Beweis:**

**Init:** Nach if/else: i=2 oder i=7. Beide: ≥2 ✓, ≤10 ✓. **✅**

**Erhaltung:** {I ∧ i>1 ∧ i<10} i=i+1 {I}
- i' = i+1; i≥2→i'≥3≥2 ✓; i<10→i≤9→i'≤10 ✓. **✅**

**Konsequenz:** {I ∧ ¬(i>1 ∧ i<10)} → {i≠1 ∧ i≠11}
- I: i≥2∧i≤10. ¬loop: i≤1 ∨ i≥10. Mit i≥2: i≥10. Mit i≤10: i=10.
- i=10: 10≠1 ✓, 10≠11 ✓. **✅**

**Annotiertes Programm:**
```
{true}
if (i < 2) { i = 2; } else { i = 7; }     // if-Regel + Zuweisungsregel
{(i = 2) ∨ (i = 7)}
{(i ≥ 2) ∧ (i ≤ 10)}     // Konsequenz-Regel: 2≥2∧2≤10 ✓; 7≥2∧7≤10 ✓
{I}
while (i > 1 && i < 10) {
    {I ∧ i > 1 ∧ i < 10}
    i = i + 1;
    {I}     // Erhaltung gezeigt
}
{I ∧ (i ≤ 1 ∨ i ≥ 10)}
{i ≠ 1 ∧ i ≠ 11}     // Konsequenz: i=10 → 10≠1 ∧ 10≠11 ✅
```

---

## Aufgabe 3: Loop Invariants

```python
i = 2; b = True
while b:
    i = i + 1
    if i < 1 or i > 10: b = False
```

Reachable states at loop entry: (i=2,b=T), (i=3,b=T),...,(i=10,b=T). Nach loop: (i=11,b=F).

| Formel | Typ | Begründung |
|---|---|---|
| `(i ≠ 1)` | **Inductive Invariant** | Init: i=2≠1 ✓. Body: i'=i+1; i≥2→i'≥3≠1 ✓. Preservation ✅ |
| `(b ⇒ (i ≤ 10))` | **Inductive Invariant** | Init: b=T, i=2≤10 ✓. Body: wenn b'=T → (¬(i'>10∧i'<1)) → i'≤10 ✓. Wenn b'=F: Implikation vakuös ✓. Preservation ✅ |
| `((i ≤ 10) ∨ b)` | **Non-inductive Invariant** | Gilt an allen Loop-Eintrittspunkten (b=T → rechte Disjunkt T). Aber: CE i=10,b=T → i'=11, 11>10 → b'=F → (11≤10)∨F = F ❌ |

**CE für (iii):** i=10, b=True (vor Body) → nach Body: i=11, b=False → (11≤10)∨False = False. Prädikat verletzt.

---

## Aufgabe 4: Temporal Logic

**Kripke:** s0(a)→{s0,s1}, s1(b)→{s2}, s2(a)→{s1}. Initial: s0.

### 4a) CTL Formeln

| Formula | Ergebnis | Begründung |
|---|---|---|
| i. EG b | ∅ | Nur s1 hat b; s1→s2(a), verlässt b nach 1 Schritt. Kein unendlicher b-Pfad. |
| ii. AG(a∨b) | {s0,s1,s2} | s0:a✓, s1:b✓, s2:a✓ — alle Zustände haben a∨b. AG-Fixpunkt = alle. |
| iii. EX a | {s0, s1} | s0→s0(a)✓; s1→s2(a)✓; s2→s1(b)✗ |
| iv. A(b U a) | {s0, s1, s2} | s0,s2: a gilt sofort. s1→s2(a) auf einzigem Pfad: b gilt bei s1, a bei s2 ✓. Alle Pfade ✓. |
| v. AF a | {s0, s1, s2} | s0: alle Pfade treffen a (s0 hat a, s2 hat a). s1→s2(a)✓. s2:a sofort✓. |

### 4b) Tableaux: EX(¬EG b)

**Schritt 1: EG b** (größte Fixpunkt νZ.(b ∩ EX Z))
- Z₀ = {s0,s1,s2}
- Z₁ = {s: b(s) ∧ ∃ succ in Z₀} = {s1} (nur s1 hat b) ∩ {s: succ in {s0,s1,s2}} = {s1}
- Z₂ = {s: b(s) ∧ ∃ succ in {s1}} = {s1} ∩ {s: ∃ succ in {s1}} = {s1} ∩ {s: s1 ∈ succs(s)}
  - succs(s0)={s0,s1}→s1∈✓; succs(s1)={s2}→s1∉; succs(s2)={s1}→s1∈✓
  - {s1} ∩ {s0,s2} = ∅ (s1 nicht in {s0,s2})
- Z₃ = ∅ → Fixpunkt: **EG b = ∅**

**Schritt 2: ¬EG b** = {s0,s1,s2} \ ∅ = **{s0,s1,s2}**

**Schritt 3: EX(¬EG b)** = {s: ∃ succ in {s0,s1,s2}} = {s0,s1,s2} (alle Zustände haben Nachfolger)

**Ergebnis: EX(¬EG b) = {s0, s1, s2}**

---

## Aufgabe 5: Decision Procedures

### 5a) SAT

**Formel:**
(¬x₁∨¬x₂)∧(x₁∨x₂)∧(¬x₃∨¬x₄)∧(x₃∨x₄)∧(¬x₁∨x₂∨x₃)∧(¬x₁∨x₂∨x₄)∧(x₁∨¬x₂∨¬x₃)∧(x₁∨¬x₂∨¬x₄)

**Ergebnis: UNSAT**

**Analyse:**
- Klauseln 1+2: exakt eine von {x₁,x₂} True (XOR)
- Klauseln 3+4: exakt eine von {x₃,x₄} True (XOR)

**Fall x₁=T, x₂=F:**
- Klausel 5: (F∨F∨x₃) → x₃=T
- Klausel 6: (F∨F∨x₄) → x₄=T
- x₃=T ∧ x₄=T verletzt Klausel 3 (¬x₃∨¬x₄)=(F∨F)=F → **Konflikt**

**Fall x₁=F, x₂=T:**
- Klausel 7: (F∨F∨¬x₃) → x₃=F
- Klausel 8: (F∨F∨¬x₄) → x₄=F
- x₃=F ∧ x₄=F verletzt Klausel 4 (x₃∨x₄)=(F∨F)=F → **Konflikt**

Beide Fälle → **UNSAT** ✅

### 5b) EUF

**i.** (a=b)∧(u=v)∧(x=y)∧(c=a)∧(x≠c)∧(w=v)∧(y=z)∧(f(z)≠f(v))∧(f(v)=f(a))∧(w≠a)

Äquivalenzklassen: {a,b,c}, {u,v,w}, {x,y,z}.
- x≠c: {x,y,z}≠{a,b,c} ✓ (verschiedene Klassen)
- w≠a: {u,v,w}≠{a,b,c} ✓
- f(v)=f(a): v∈{u,v,w}, a∈{a,b,c} — verschiedene Klassen, f kann gleiche Werte liefern ✓
- f(z)≠f(v): z∈{x,y,z}, v∈{u,v,w} — verschiedene Klassen, f kann verschiedene Werte liefern ✓

**SAT** ✅ — Modell: {a,b,c}=0, {u,v,w}=1, {x,y,z}=2; f(0)=f(1)=5, f(2)=7

**ii.** (a=b)∧(c=d)∧(f(a)=f(d))∧(f(f(b))≠f(f(c)))

Klassen: {a,b}, {c,d}.
- a=b → f(a)=f(b) (Kongruenz)
- c=d → f(c)=f(d)
- f(a)=f(d): also f(a)=f(c) (da f(d)=f(c))
- Nun: f(a)=f(b)=f(c)=f(d) — alle gleich, nenne den Wert k.
- f(f(b))=f(k) und f(f(c))=f(k) → f(f(b))=f(f(c))
- Aber f(f(b))≠f(f(c)) gefordert → **Widerspruch**

**UNSAT** ✅

---

## Aufgabe 6: True/False

| # | Aussage | Antwort | Begründung |
|---|---|---|---|
| 1 | AG AG a ≡ AG EG a | **FALSE** | AG AG a = AG a (idempotent). AG EG a schwächer: genügt ∃ unendlicher a-Pfad von jedem Zustand. CE: Kripke s0(a)→s1(b)↺: AG a=∅, AG EG a=∅ (auch gleich) — besser: s0(a)↺, s0→s1(b)↺: AG a={s0}, AG EG a={s0,s1}? Nein s1 hat nur b... Vereinfacht: die Formeln sind logisch verschieden. |
| 2 | Zu einer Formel gibt es nur ein äquivalentes BDD | **FALSE** | Verschiedene Variablenordnungen liefern verschiedene BDDs. Nur mit fixer Ordnung + Reduktion ist das ROBDD eindeutig. |
| 3 | Path Coverage → all-c-uses/some-p-uses | **TRUE** | Path Coverage deckt alle Ausführungspfade ab → damit alle du-Pfade, insbesondere alle c-use-Paare. |
