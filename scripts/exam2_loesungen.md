# Exam 2 — June 2022 — Lösungen

## Aufgabe 1: Coverage — `prime(n)`

```python
def prime(n):
    i = 2
    flag = True
    if n == 0 or n == 1:   # D0
        flag = False
    while (i <= n/2) and flag:  # D1
        if n % i == 0:     # D2
            flag = False
        i = i + 1
    return flag
```

**Test suite:** `prime(0)`, `prime(3)`, `prime(4)`

### 1a) Control-Flow Coverage

| Kriterium | Ergebnis | Begründung |
|---|---|---|
| Statement Coverage | ✅ | Alle Zeilen werden ausgeführt (n=4 betritt Loop und `flag=False`-Zweig) |
| Decision Coverage | ❌ | D2 (`n%i==0`) hat nur True-Zweig (n=4, i=2: 4%2=0). False-Zweig nie genommen. |
| Branch Coverage | ❌ | D1-False-Branch (`n%i==0`=False) nie genommen (5/6 Branches = 83%; D1 nur True) |
| MC/DC | ❌ | Atom `n==1` in D0 nimmt nie True-Wert an. D2-False fehlt. |

**Fehlende Branches:**
- D2 (`n%i==0`) False-Branch: kein Test bei dem der Loop läuft aber kein Divisor gefunden wird.
- MC/DC: `n==1` immer False im Test-Set.

### 1b) Data-Flow Coverage

Mit `prime(0)`, `prime(3)`, `prime(4)`:

| Kriterium | Ergebnis |
|---|---|
| all-defs | ✅ 5/5 def-Punkte abgedeckt |
| all-c-uses | ❌ 4/5 — fehlend: `(i, Z9→Z9)` (i@Z9 wird nicht im selben Loop-Body nochmal als c-use verwendet) |
| all-p-uses | ❌ 6/7 — fehlend: `(i, Z9→Z7)` (i nach Inkrement nie in `n%i==0` verwendet = kein 2. Iteration) |
| all-c-uses/some-p-uses | ❌ (all-c-uses nicht erfüllt) |
| all-p-uses/some-c-uses | ❌ (all-p-uses nicht erfüllt) |

**Begründung:** `i = i + 1` (Z9) definiert `i`, aber das loop-carried Paar `(i, Z9, Z7)` erfordert mindestens zwei Loop-Iterationen. Mit n=4 endet der Loop nach einer Iteration (flag=False).

### 1c) Minimale Ergänzung für all-p-uses/some-c-uses + MC/DC

**Fehlende Abdeckung:**
- `prime(1)` → deckt Atom `n==1=True` in D0 für MC/DC
- `prime(9)` → 2 Loop-Iterationen: i@9=3 wird in `n%3` (D2, p-use) und while-Check (D1, p-use) verwendet. Deckt D2-False (9%2=1≠0 in erster Iteration).

**Ergänze:** `prime(1)` und `prime(9)`.

### 1d) Mutation: `(i <= n/2)` → `(i < n/2)`

**Killtest:** `prime(4)` — bereits im Test-Set!
- Original: `while(2 <= 2)` → True → prüft 4%2=0, gibt False zurück.
- Mutant: `while(2 < 2)` → False → überspringt Loop, gibt True zurück.
- **Return-Werte verschieden → stark gekillt.** ✅

---

## Aufgabe 2: Hoare Logic

```
{true}
if (n % 2 == 0) { n = n + 1; } else { skip; }
i = 0; s = 0;
while (i != n) { i = i + 1; s = s + (i % 2); }
{s ≤ n}
```

**Nach dem if/else:** `n` ist immer ungerade (falls gerade: n+1 ist ungerade).  
**Vorbedingung des While:** `n ≥ 1` (ungerade), `i = 0`, `s = 0`.

### Loop-Invariante

**I = (s ≤ i) ∧ (i ≤ n) ∧ (n % 2 = 1)**

**Z3-Verifikation:** alle 3 Checks ✅ (unsat für Gegenbeispiel)

**Beweis:**

**Init-Check:** `{true ∧ Prefix} I`
- Nach if/else: n ungerade (n%2=1 ✓)
- Nach `i=0; s=0`: s=0≤0=i ✓, i=0≤n ✓ (n≥1 da ungerade)
- **✅**

**Erhaltungs-Check:** `{I ∧ i≠n} Body {I}`
- Body: `i' = i+1`, `s' = s + (i+1)%2`
- s' = s+(i+1)%2 ≤ s+1 ≤ i+1 = i' ✓ (da s≤i)
- i' = i+1 ≤ n ✓ (da i<n aus i≤n ∧ i≠n in ℕ₀)
- n%2=1 unverändert ✓
- **✅**

**Konsequenz-Check (Exit):** `{I ∧ i=n} → s ≤ n`
- I ∧ i=n → s ≤ i = n → **s ≤ n ✅**

**Annotiertes Programm:**
```
{true}
if (n % 2 == 0) { n = n + 1; } else { skip; }
{n % 2 = 1}     // Zuweisungsregel + if/else-Regel
i = 0; s = 0;
{(s ≤ i) ∧ (i ≤ n) ∧ (n%2=1)}   // = I
while (i != n) {
    {I ∧ i ≠ n}
    i = i + 1;
    s = s + (i % 2);
    {I}     // Erhaltung gezeigt
}
{I ∧ i = n}
{s ≤ n}     // Konsequenz-Regel ✅
```

---

## Aufgabe 3: Loop Invariants

**Programm:**
```
if (x > y) { t=x; x=y; y=t; }   // sichert x ≤ y
if (a > b) { x=b; y=a; }
while (y > x) { a=a-1; y=y-1; }
```

### Ergebnisse (Z3-verifiziert)

| Formel | Typ | Begründung |
|---|---|---|
| `(a>b) ⇒ (y≥x)` | **Inductive Invariant** | Vor Loop: a>b → x=b,y=a → y>x≥ x. In Body: a-=1,y-=1 — falls a-1>b dann a>b+1→y>x+1→y-1>x ✅ |
| `(a>b) ⇒ (y>x)` | **Non-inductive Invariant** | CE: a=b+2, y=x+1 → nach Body: a-1=b+1>b, aber y-1=x → y>x verletzt ✅ |
| `(x>y) ⇒ (a>b)` | **Inductive Invariant** | Vakuös: nach erstem if ist x≤y immer, also Prämisse immer False → True |

---

## Aufgabe 4: Temporal Logic

**Kripke-Struktur:** s0(a) → s1(b), s1 → s1, s1 → s2(a) → s1  
*(Gleiche Struktur wie Exam 1!)*

### 4a) CTL Formeln

| Formel | Ergebnis |
|---|---|
| `EG a` | ∅ — kein Zustand hat unendlichen a-Pfad (s0→s1, dann immer b) |
| `AF(EG a)` | ∅ — da EG a=∅, kann kein Zustand es "eventually" erfüllen |
| `A(a ∧ EX b)` | {s0, s2} — a gilt in s0,s2; EX b gilt in allen (jeder Zustand hat s1 als Nachfolger mit b) |
| `A[a U b]` | {s0, s1, s2} — von überall: a gilt bis b (b gilt sofort in s1, von s0/s2 → s1 in einem Schritt) |
| `E[a U b]` | {s0, s1, s2} — gleiche Begründung |

*Hinweis: `A(a ∧ EX b)` = (a ∧ EX b) als Zustandsformel = {s:a gilt} ∩ {s:EX b gilt} = {s0,s2} ∩ {s0,s1,s2} = {s0,s2}*

### 4b) Tableaux: `EF(EX a)` mit Subformeln

**Schritt 1: EX a** (größte Formel zuerst → kleinste zuerst)
- EX a = {s : ∃ Nachfolger mit a} = {s1} (s1→s2, s2 hat a ✓)

**Schritt 2: EF(EX a)** — least fixpoint μZ.(EX a ∪ EX Z)
- Z₀ = {s1}
- EX(Z₀) = {s : ∃ Nachfolger in {s1}} = {s0,s1,s2} (alle haben s1 als Nachfolger)
- Z₁ = {s1} ∪ {s0,s1,s2} = **{s0,s1,s2}**
- EX(Z₁) = {s0,s1,s2} (alle)
- Z₂ = Z₁ → **Fixpunkt ✓**

**Ergebnis:** `EF(EX a) = {s0, s1, s2}`

---

## Aufgabe 5: Decision Procedures

### 5a) SAT (15 Klauseln)

**Formel:** XOR-Kette x1⊕x2⊕...⊕x6⊕x7 + (¬x1∨¬x7) ∧ (x1∨x7) ∧ (x4∨x5∨x6)

**Ergebnis: UNSAT** (Z3 + DPLL verifiziert)

**CDCL-Ablauf:**
- **L0: Decide** x1=True
  - UP: x2=F, x7=F, x3=T, x6=T, x4=F, x5=F
  - Überprüfe (x1∨x7): (T∨F)=T ✓, aber Kette ergibt Konflikt
  - **Konflikt** → learned: ¬x1, Backtrack auf L0
- **L0: Force** x1=False (aus ¬x1)
  - UP: x2=T (aus x1∨x2), x7=T (aus x1∨x7)
  - x7=T → x6=F (aus ¬x6∨¬x7), x6=F → x5=T (aus x5∨x6)
  - x5=T → x4=F (aus ¬x4∨¬x5), x4=F → x3=T (aus x3∨x4)
  - x3=T → x2=F (aus ¬x2∨¬x3) — aber x2=T (aus oben)! **Konflikt**
- Beide Assignments führen zu Konflikten → **UNSAT** ✅

### 5b) EUF (Equality Logic with Uninterpreted Functions)

| Formel | Ergebnis | Begründung |
|---|---|---|
| `g=h ∧ a=b ∧ a=c ∧ e≠i ∧ d=e ∧ f=e ∧ h=i ∧ f(a)≠f(h) ∧ a=i` | **UNSAT** | Äquivalenzklassen: {a,b,c,g,h,i} und {d,e,f}. Aus a=i und h=i: a=h → f(a)=f(h) per Kongruenz → Widerspruch mit f(a)≠f(h) |
| `g=h ∧ a=b ∧ a=c ∧ e≠i ∧ d=e ∧ f=e ∧ h=i ∧ f(a)≠f(d)` | **SAT** | Klassen: {g,h,i}, {a,b,c}, {d,e,f}. a≠d → f(a) und f(d) können verschieden sein. Model: a=0,d=2,f(0)=1,f(2)=3 |
| `i=j ∧ j=k ∧ l≠n ∧ m=n ∧ g(k)=g(l) ∧ f(i)≠f(m)` | **SAT** | Klassen: {i,j,k}, {m,n}, {l}. i≠m → f(i)≠f(m) möglich. g(k)=g(l) mit k≠l ist erlaubt. Model: i=2,m=1,f(2)=4,f(1)=5 |

---

## Aufgabe 6: True/False

| # | Aussage | Antwort | Begründung |
|---|---|---|---|
| 1 | all-c-uses/some-p-uses ∧ all-p-uses/some-c-uses → all-uses | **TRUE** | all-c-uses/sp deckt alle c-uses; all-p-uses/sc deckt alle p-uses → Vereinigung = all-uses |
| 2 | BDD für x≠y mit Ordnung x2>y2>x1>y1>x0>y0 hat polynomiale Größe | **TRUE** | Interleaved Ordnung (je xi,yi zusammen) ergibt lineares BDD: ≠ prüfbar in O(n) Knoten |
| 3 | AG F p und AG EF p sind logisch äquivalent | **FALSE** | "AG F p" (LTL-Semantik) = auf allen Pfaden p unendlich oft; "AG EF p" (CTL) = von jedem Zustand p erreichbar. CE: Kripke mit Pfad der p dauerhaft vermeidet |
| 4 | UNSAT-Formel mit O(1)-OBDD → SAT-Solver in O(n) | **FALSE** | SAT-Solver exploitiert keine OBDD-Struktur; CNF-Kodierung kann exponentiell groß sein |
| 5 | LTL∩CTL ohne X in CTL* ausdrückbar | **TRUE** | Der LTL∩CTL Fragment entspricht X-freien Formeln; in CTL* ausdrückbar |
