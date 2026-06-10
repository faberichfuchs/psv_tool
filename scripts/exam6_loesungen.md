# Exam 6 — June 2025 — Lösungen

## Aufgabe 1: Coverage — `perfect(a)`

```python
def perfect(a):
    n = a                          # L1
    if n <= 1:                     # D0: L2
        return False               # L3
    s = 1; i = n // 2             # L5
    while i > 1 and s <= n:       # D1: L6 (&&, nicht short-circuited)
        if n % i == 0:             # D2: L7
            s = s + i              # L8
        i = i - 1                  # L10
    return s == n                  # D3: L12 (p-use für s,n)
```

**Tests:** (1)→False, (4)→False

**Traces:**
- (1): n=1→D0:T→return False
- (4): n=4→D0:F→s=1,i=2; D1:T→D2:4%2=0=T→s=3; i=1; D1:(1>1)=F→L12:(3==4)=False

### 1a) Control-Flow Coverage

| Kriterium | Ergebnis | Begründung |
|---|---|---|
| Statement Coverage | ✅ | L3:(1)✓; L8:(4)✓; L10:(4)✓; L12:(4)✓ — alle Statements erreicht |
| Decision Coverage | ❌ | D2 (n%i==0) nur True: (4)→4%2=0. False-Branch nie. D3 (s==n) nur False: (3==4). True nie (kein perfektes n im Test-Set). |
| Condition Coverage | ❌ | D1-Atom B=(s≤n): T=(4)✓, F=never (s nie >n). D2=(n%i==0): F=never. D3=(s==n): True=never. |
| MC/DC | ❌ | Alle Probleme von Condition Coverage + Unabhängigkeits-Witnesses für D1 fehlen. |

**Fehlend:**
- D2-False: n%i≠0 nie evaluiert. Braucht z.B. (5): 5%2=1≠0.
- D3-True: perfekte Zahl braucht (6): 6==6=True.
- D1-B=False: s>n nie. Braucht Zahl mit überschießenden Divisoren z.B. (12): s=7+4+3=14>12.

### 1b) Data-Flow Coverage

Defs: n@L1, s@L5, i@L5, s@L8, i@L10. L12=p-use für s,n.

| Kriterium | Ergebnis |
|---|---|
| all-defs | ✅ — n@L1→L5(c:i=n//2)✓; s@L5→L8(c:s=s+i)✓; i@L5→L10(c:i=i-1)✓; s@L8→L12(p)✓; i@L10→L6(p)✓ |
| all-c-uses | ❌ — (s,L8,L8) fehlt: s@L8 in zweitem L8 verwendet (2 Iter. wo D2=T). (i,L10,L10) fehlt: i@L10 in nächster i=i-1 (≥3 Iters.). |
| all-p-uses | ❌ — (i,L10,L7) fehlt: i@L10 (i=1 bei (4)) niemals in D2 (n%i) evaluiert, da D1 schon false wird. |
| all-p-uses/some-c-uses | ❌ |

**Fehlende Pairs:**
- `(s, L8, L8)`: benötigt mind. 2 Iterationen wo D2=True. Z.B. (12) hat 12%6=0, 12%4=0, 12%3=0 → L8 dreimal.
- `(i, L10, L10)`: i@L10 in nächster i=i-1 verwendet. Benötigt 3+ Loop-Iterationen. (12) deckt das.
- `(i, L10, L7)`: i@L10 in D2 (n%i) evaluiert. Benötigt Loop fortgesetzt nach i=i-1 mit D1=T. Bei (12) nach i@L10=5: D1:T→D2:12%5=2≠0.

### 1c) Minimale Ergänzung

**all-c-uses/some-p-uses:** 1 Test:
- **(12) → False** (12 ist nicht perfekt: 1+2+3+4+6=16≠12)
  - Deckt (s,L8,L8): s=1+6=7, dann +4=11, dann +3=14 (drei L8-Hits)
  - Deckt (i,L10,L10): i=6→5→4→3→...
  - Deckt (i,L10,L7): nach i=5(L10), D1:T→D2:12%5≠0

| Input | Output |
|---|---|
| 12 | false |

**condition/decision coverage:** 2 Tests:
- **(5) → False**: 5%2=1≠0 → D2=False ✓; s=1≠5 → D3=False ✓
- **(6) → True**: s=1+3+2=6=n → D3=True ✓. Und 6%2=0, 6%3=0 → D2=True ✓. D1-B=False? 6: s nach iter1 (i=3): s=4; i=2: s=6; i=1: D1=F(i>1). s nie >6. Hmm, D1-B=(s≤n) noch immer nur True. Für D1-B=False: brauche (12).

Also für vollständige condition/decision coverage: (5), (6), (12).

| Input | Output |
|---|---|
| 5 | false |
| 6 | true |
| 12 | false |

### 1d) Mutation: `(i > 1 && s <= n)` → `(i > 1)`

**Kein Killtest existiert — Mutant ist äquivalent.**

**Begründung:** Der `s <= n`-Zweig stoppt die Schleife frühzeitig wenn s > n. In diesem Fall gilt: s ist die Teilsumme der Divisoren und überschreitet n. Die vollständige Divisorensumme (was der Mutant berechnet) ist ≥ s > n. Daher: sowohl Original (return s_partial==n = False) als auch Mutant (return s_full==n = False) geben False zurück. Für perfekte Zahlen (s_full=n) ist s nie > n während der Schleife, also verlässt das Original die Schleife nie frühzeitig — kein Unterschied. **Kein Killtest möglich.**

---

## Aufgabe 2: Hoare Logic — Integer Square Root

```
{n ≥ 0}
l = 0; r = n + 1;
while (l ≠ r - 1) { m = (l+r)/2; if (m²≤n) l=m; else r=m; }
{l*l ≤ n < (l+1)*(l+1)}
```

**Invariante: I = (l * l ≤ n) ∧ (n < r * r)**

**Init:** l=0, r=n+1. l²=0≤n ✓ (n≥0). n<(n+1)²=n²+2n+1 für n≥0 ✓.

**Erhaltung:** {I ∧ l≠r-1} body {I}. Berechne m=(l+r)/2.
- Falls m²≤n: l=m → l_new²=m²≤n ✓; r unverändert → n<r² ✓
- Falls m²>n: r=m → n<r_new²=m² ✓; l unverändert → l²≤n ✓

**Konsequenz:** {I ∧ ¬(l≠r-1)} = {l²≤n<r² ∧ l=r-1}. Dann r=l+1 → n<(l+1)² ✓ und l²≤n ✓.

**Annotiertes Programm:**
```
{n ≥ 0}
l = 0;                          // Zuweisungsregel: I[l/0,r/(n+1)] wenn r=n+1
r = n + 1;
{l*l ≤ n ∧ n < r*r}            // Init gezeigt: 0≤n ✓, n<(n+1)² ✓
{I}
while (l ≠ r - 1) {
    {I ∧ l ≠ r-1}               // While-Regel
    m = (l + r) / 2;
    if (m * m ≤ n) {
        l = m;                   // Zuweisungsregel: l_new²=m²≤n ✓
        {(l*l ≤ n) ∧ (n < r*r)} // = I ✓
    } else {
        r = m;                   // Zuweisungsregel: n < r_new²=m² ✓
        {(l*l ≤ n) ∧ (n < r*r)} // = I ✓
    }
    {I}                          // If-Else-Regel ✓
}
{I ∧ l = r-1}                   // While-Regel
{l*l ≤ n < (l+1)*(l+1)}        // Konsequenz: r=l+1 ✓
```

---

## Aufgabe 3: Loop Invariants

**Programm nach Prefix:** Nach if-Blöcken gilt a>b und x>y (falls b≥a: a=b+1>b_new; falls y≥x: x=y+1>y_new). Loop: a-=1, y+=1 (b,x konstant).

**Invariante: a>b und x>y immer im Loop.**

| Formel | Typ | Begründung |
|---|---|---|
| `(b>x) ⇒ (a>y)` | **Inductive Invariant** | Init: a>b>x>y→a>y✓. Body: wenn b>x: a>b>x>y→a≥y+3; nach Body: a'=a-1≥y+2>y+1=y' ✓. Preservation ✅ |
| `(a≥b) ∧ (x≥y)` | **Inductive Invariant** | Init: a>b→a≥b✓; x>y→x≥y✓. Body: a≠b∧a≥b→a>b→a-1≥b=a'≥b✓; x≠y∧x≥y→x>y→x≥y+1=y'✓. |
| `(a≥y)` | **Neither** | CE: initial a=0,b=0,x=100,y=100. Prefix: a=1,b=0,x=101,y=100. Loop-Entry: a=1<y=100. Invariante verletzt. |

**CE für Neither (iii):** Wähle initiale Werte a=0,b=0,x=100,y=100:
- b≥a(0≥0)→ a=0+1=1, b=0; y≥x(100≥100)→ x=101, y=100.
- Loop entry: a=1 < y=100 → (a≥y)=False. ❌

---

## Aufgabe 4: Temporal Logic

**Kripke (4a):** s0(a)→s1(b)↔s2(a): s0→{s1}, s1→{s2}, s2→{s1}. Initial: s0.

### 4a) CTL Formeln

| Formula | Ergebnis | Begründung |
|---|---|---|
| i. AG F a = AG(AF a) | {s0,s1,s2} | AF a: alle Pfade von s0/s1/s2 treffen a (s2 ist immer erreichbar). AF a={all}. AG(all)={all}. |
| ii. AF G a = AF(AG a) | ∅ | AG a: s2→s1(b) verlässt a. AG a=∅. AF(∅)=∅. |
| iii. AG(b⇒AF a) | {s0,s1,s2} | b nur in s1. s1∈AF a (s1→s2(a)✓). Alle anderen: b=F→vakuös. AG({all})={all}. |
| iv. AG(AF(a∧AXb)) | {s0,s1,s2} | AXb={s0,s2} (beide haben s1 als einzigen Nachfolger mit b). a∧AXb={s0,s2}. AF({s0,s2})={all}. AG({all})={all}. |
| v. E(a∧AXb) = a∧EXb | {s0,s2} | EXb={s: ∃ Nachfolger mit b}={s0(→s1✓),s2(→s1✓)}. a∧EXb={s0,s2}. |

**Kripke (4b):** s0(a)→s1(b)↔s2(b): s0→{s1}, s1→{s2}, s2→{s1}. Initial: s0.

### 4b) Tableaux: EX(EG b)

**EG b** = νZ.(b ∩ EX Z):
- Z₀ = {s0,s1,s2}
- Z₁ = {s: b(s) ∧ ∃ succ in Z₀} = {s1,s2} ∩ {all} = {s1,s2}
- Z₂ = {s: b(s) ∧ ∃ succ in {s1,s2}}: EX{s1,s2}={s: succ∈{s1,s2}}: s0→s1✓, s1→s2✓, s2→s1✓ → {s0,s1,s2}. Z₂={s1,s2}∩{all}={s1,s2}
- **Fixpunkt: EG b = {s1, s2}**

**EX({s1,s2})**: s0→s1∈✓; s1→s2∈✓; s2→s1∈✓ → **EX(EG b) = {s0, s1, s2}**

---

## Aufgabe 5: Decision Procedures

### 5a) CDCL

**Entscheidungssequenz und BCP:**

**Level 1:** Decide x1=T.
- C2=(¬x1∨¬x2)=(F∨¬x2) → x2=F (BCP@L1)

**Level 2:** Decide x3=T.
- C6=(¬x3∨¬x4)=(F∨¬x4) → x4=F (BCP@L2)
- C3=(x2∨x4∨x5)=(F∨F∨x5) → x5=T (BCP@L2)

**Level 3:** Decide x6=T.
- C4=(x2∨¬x6∨x8)=(F∨F∨x8) → x8=T (BCP@L3)
- C7=(x4∨¬x6∨x7)=(F∨F∨x7) → x7=T (BCP@L3)
- C14=(¬x7∨¬x8∨x9)=(F∨F∨x9) → x9=T (BCP@L3)
- C9=(¬x5∨¬x9∨¬x10)=(F∨F∨¬x10) → x10=F (BCP@L3)
- C10=(¬x5∨¬x9∨¬x11)=(F∨F∨¬x11) → x11=F (BCP@L3)
- **C15=(x10∨x11)=(F∨F)=F → KONFLIKT!**

**Conflict Graph (Level 3):**
```
x6=T(L3) ──C7──> x7=T(L3) ──┐
x4=F(L2) ──────────────────> C14 ──> x9=T(L3) ──C9──> x10=F(L3) ──┐
x6=T(L3) ──C4──> x8=T(L3) ──┘         x5=T(L2) ──C10──> x11=F(L3)──┴──> C15=CONFLICT
```

**Erster UIP:** x9 (liegt auf ALLEN Pfaden von x6 zum Konflikt).

**Lernklausel (Resolution):**
- Resolve C15 mit C9 (via x10): C15∨C9 / x10 = {x11,¬x5,¬x9}
- Resolve mit C10 (via x11): {x11,¬x5,¬x9}∨C10 / x11 = **{¬x5, ¬x9}**
- Gelernte Klausel: **¬x5 ∨ ¬x9**

**Backjump:** Zurück auf Level 2 (max. Level der Nicht-UIP-Literale: x5@L2). Propagiere x9=F (aus ¬x5∨¬x9 mit x5=T).

### 5b) EUF

**Basis F:** x1=x2, x3=x4, f(f(x4))=f(x5), f(x2)=x5, f(x1)≠f(x5), f(x3)≠f(x5), x1≠x5.
**Folgerungen aus F:** x1=x2 → f(x1)=f(x2)=x5. f(x1)≠f(x5) → x5≠f(x5). x3=x4 → f(x3)=f(x4) → f(f(x3))=f(f(x4))=f(x5).

| Formel | Ergebnis | Begründung |
|---|---|---|
| **i.** F ∧ (f(x3)≠f(f(x5))) | **SAT** | Modell: x1=x2=0,x3=x4=2,x5=1; f(0)=1,f(1)=4,f(2)=3,f(3)=4,f(4)=5. Alle Constraints ✓. f(x3)=3≠5=f(f(x5))=f(f(1))=f(4)=5 ✓. |
| **ii.** F ∧ (f(x2)=f(f(x1))) | **UNSAT** | f(x2)=x5 (aus F). f(x1)=x5 (x1=x2). f(f(x1))=f(x5). Neue Bed.: f(x2)=f(f(x1)) → x5=f(x5). Aber f(x1)≠f(x5) (F) und f(x1)=x5 → x5≠f(x5). Widerspruch. |

---

## Aufgabe 6: True/False

| # | Aussage | Antwort | Begründung |
|---|---|---|---|
| 1 | all-p-uses ≡ all-p-uses/some-c-uses in Programm ohne c-uses | **TRUE** | Ohne c-uses: "some-c-uses"-Bedingung ist vakuös erfüllt. Beide Metriken reduzieren auf all-p-uses. |
| 2 | Für jede nicht-induktive Invariante ∃ mind. 1 unerreichbarer Zustand der die Invariante erfüllt | **TRUE** | Nicht-Induktivitäts-CE: Zustand S mit P∧Cond aber Body→¬P. S muss unerreichbar sein (wäre S erreichbar, würde Body-Folge-State ¬P haben, obwohl P Invariante ist → Widerspruch). S erfüllt P. ✓ |
| 3 | "Wenn p gilt, ist es möglich q zu erreichen" in LTL∩CTL ausdrückbar | **FALSE** | = AG(p→EF q). Enthält EF (existentiell), nicht in LTL. LTL würde AG(p→AF q) benötigen (universell). Verschiedene Semantiken. |
| 4 | Jede CNF-Formel mit genau 2 Literalen pro Klausel ist erfüllbar | **FALSE** | CE: (x₁∨x₂)∧(¬x₁∨¬x₂)∧(x₁∨¬x₂)∧(¬x₁∨x₂) = UNSAT. |
| 5 | Für nicht-terminierendes C: kein Hoare-Beweis von {true}C{false} möglich | **FALSE** | In partieller Korrektheit: {P}C{Q} gilt vakuös wenn C nicht terminiert. {true}C{false} für immer divergierendes C ist gültiges (und beweisbares) Tripel. |
