# Exam 7 — October 2025 — Lösungen

## Aufgabe 1: Coverage — `cmp_bit_count(a, b)`

```python
def cmp_bit_count(a, b):
    x = a                                     # L1
    y = b                                     # L2
    c = 0                                     # L3
    while (x != 0 or y != 0) and (x != y):   # D_while: L4
        if x > y:                             # D_if: L5
            c = c + (x & 1)                   # L6
            x = x >> 1                        # L7
        else:
            c = c - (y & 1)                   # L9
            y = y >> 1                        # L10
    return c                                  # L13
```

**Tests:** (0,0)→0, (0,4)→-1, (2,1)→0. `&&` is NOT short-circuited!

**Traces:**
- (0,0): D_while: (0||0)=F → sofort exit. c=0 ✓
- (0,4): Loop x-branch: Nein (x=0<y). Drei Iterationen via y-branch: y=4→2→1→0. c=-1 ✓
- (2,1): iter1: x=2>y=1 → c=0+(0)=0; x=1. iter2: x=y=1 → D_while:(T&&F)=F → exit. c=0 ✓

**D_while Atome:** A=(x!=0), B=(y!=0), C=(x!=y). Compound: (A||B)&&C.
**D_if Atom:** D=(x>y).

### 1a) Control-Flow Coverage

| Kriterium | Ergebnis | Begründung |
|---|---|---|
| Statement Coverage | ✅ | L6,L7:(2,1)✓; L9,L10:(0,4)✓; L13: alle ✓ |
| Decision Coverage | ✅ | D_while: T=(0,4)✓, F=(0,0)✓; D_if: T=(2,1)✓, F=(0,4)✓ |
| Condition Coverage | ✅ | A=T:(2,1); A=F:(0,4); B=T:(0,4); B=F:(0,0); C=T:(2,1)iter1; C=F:(2,1)iter2; D=T:(2,1); D=F:(0,4) |
| MC/DC | ❌ | Strukturell unmöglich für A und B in D_while (siehe unten) |

**Warum MC/DC ❌:**
Für Atom A=(x!=0): Unabhängigkeits-Witness benötigt B=F, C=T. B=F bedeutet y=0. C=T bedeutet x≠y. Mit A=F: x=0 und y=0 → C=(0!=0)=F. **Widerspruch!** A=F, B=F, C=T ist unerreichbar. Analoges gilt für B. Atom C und D sind einzeln zeigbar (✓), aber A und B können ihren unabhängigen Einfluss auf D_while nicht demonstrieren.

### 1b) Data-Flow Coverage

Defs: x@L1, y@L2, c@L3, x@L7, y@L10, c@L6, c@L9.
L13 ist weder c-use noch p-use für c (per Aufgabe).

| Kriterium | Ergebnis | Begründung |
|---|---|---|
| all-defs | ❌ | c@L6: in (2,1) nach L6 läuft Loop nicht weiter → c@L6 erreicht keine c-use (L6 oder L9). L13 ausgenommen. |
| all-c-uses | ❌ | Fehlt: (x,L7,L6), (x,L7,L7): braucht 2 x-branch-Iter.; (c,L6,L6),(c,L6,L9): braucht x-dann-x oder x-dann-y Iter.; (c,L9,L6): braucht y-dann-x Iter. |
| all-p-uses | ❌ | Fehlt: (x,L7,D_if): x@L7 in `x>y` benutzt. Braucht Loop-Fortsetzung nach x-Branch, z.B. (3,2) — nicht in Tests. |
| all-p-uses/some-c-uses | ❌ | Alle obigen Fehler übernommen. |

**Fehlende Pairs im Detail:**
- `(c, L6, -)`: c@L6 hat keine Folge-c-use in den Tests. Braucht Loop mit x-Branch dann x oder y-Branch.
- `(x, L7, D_if)`: x@L7=1 in (2,1), aber Loop exits → D_if nicht evaluiert mit x@L7. Braucht z.B. (3,2).
- `(x, L7, L6)`, `(x, L7, L7)`: braucht zwei x-Branch-Iterationen. Braucht z.B. (4,1) oder (4,2).

### 1c) MC/DC — Augmentation

**MC/DC kann nicht vollständig erreicht werden** wegen struktureller Unmöglichkeit für Atome A und B in (A||B)&&C:

Die Unabhängigkeits-Witness-Paare für A erfordern:
- (A=T, B=F, C=T) → D=T: möglich, z.B. x≠0, y=0, x≠y. Test: (2,0)→?
- (A=F, B=F, C=T) → D=F: **unmöglich!** A=F und B=F bedeuten x=0 und y=0, was C=x!=y=0!=0=F erzwingt. Widerspruch zu C=T.

Kein Test-Set kann A oder B unabhängig zeigen → **MC/DC nicht erreichbar.**

(Falls trotzdem nach Maximum gefragt: D und C sind bereits abgedeckt.)

### 1d) Mutation: `(x != 0 || y != 0) && (x != y)` → `(x != 0 || y != 0)`

**Kein Killtest — Mutant ist äquivalent.**

**Beweis:** Wenn Original beim `x=y≠0`-Exit stoppt und c zurückgibt, läuft der Mutant weiter. Für x=y=v: Da x=y gilt x>y=False stets, also immer y-Branch. Dann wächst x>y zur nächsten Iteration → symmetrische Verarbeitung. Formal: nach jedem Paar von Iterationen (1x y-Branch: c-=LSB_y, y>>=1; dann 1x x-Branch: c+=LSB_x=LSB_y_alt) ist der Nettobeitrag 0. Da x und y gleich begonnen haben, werden sie zusammen auf 0 reduziert, ohne c netto zu verändern. Original und Mutant geben immer denselben Wert zurück. **Kein Killtest möglich.**

---

## Aufgabe 2: Hoare Logic

```
{k ≥ 0}
if k > 0 { n = k; } else { n = -k; }
m = -n;
while (m + n != 2*k) { m = m+1; n = n+1; }
{m = 0}
```

**Loop-Invariante: I = n - m = 2k**

**Schlüsselbeobachtung:** n = |k| = k (da k≥0). m = -n = -k. n-m = k-(-k) = 2k.

**Annotierter Beweis:**
```
{k ≥ 0}
  [If-Regel mit Konsequenz]
if k > 0 {
  {k≥0 ∧ k>0} ⊨ {k = |k|}
  n = k;
  {n = k}   [Zuweisungsregel]
} else {
  {k≥0 ∧ k≤0} ⊨ {k = 0 = |k|}
  n = -k;   [-(-0)=0=k]
  {n = k}   [Zuweisungsregel, da k=0: n=-0=0=k]
}
{n = k}     [If-Regel: beide Zweige liefern n=k (da k≥0)]

m = -n;
{m = -n ∧ n = k}    [Zuweisungsregel]
{n - m = 2k}        [Konsequenz: n-(-n)=2n=2k]
{I}

while (m + n != 2*k) {
  {I ∧ m+n ≠ 2k}
  m = m + 1;
  {n-(m-1) = 2k}    [Zuweisungsregel, d.h. n-m+1=2k]
  n = n + 1;
  {(n-1)-(m-1) = 2k}  [Zuweisungsregel → n-m=2k = I ✓]
  {I}
}

{I ∧ m+n = 2k}      [While-Regel]
{n-m = 2k ∧ m+n = 2k}
⊨ {m = 0}           [Konsequenz: 2m=(m+n)-(n-m)=2k-2k=0 → m=0]
{m = 0}   ✓
```

**Vollständige 3 Obligations:**
- **Init:** n=k, m=-k → n-m=2k ✓
- **Preservation:** {I ∧ m+n≠2k}: n'=n+1, m'=m+1. n'-m'=(n+1)-(m+1)=n-m=2k=I ✓
- **Consequence:** I ∧ ¬Cond: n-m=2k ∧ m+n=2k → 2m=0 → m=0 ✓

---

## Aufgabe 3: Loop Invariants

**Programm:** Nach Prefix: i=|i₀|≥0, x=y=a. Loop: x+=i, y-=i, i-=1.

| Formel | Typ | Begründung |
|---|---|---|
| `x - y >= 2*i` | **Neither** | CE: i₀=1, a=0 → i=1,x=0,y=0 bei Loop-Entry. x-y=0 < 2*1=2. Nicht-Invariante. Reachable. |
| `x + y >= 2*a` | **Inductive Invariant** | x+y=(x+i)+(y-i)=x+y: invariant durch Body! Init: x=y=a → x+y=2a≥2a ✓. Body: x'+y'=x+y≥2a ✓. |
| `x + x >= 2*a` | **Inductive Invariant** | x≥a: Init x=a ✓. Body: x'=x+i, i>0 (da i≠0∧i≥0→i≥1) → x'=x+i≥a+1>a ✓. Stark genug da i≥1 immer. |

**CE für Neither (i):** i=1, a=5, x=5, y=5 (Loop-Entry nach Prefix mit i₀=1,a=5). x-y=0, 2*i=2. 0<2 → Formel False. ❌

---

## Aufgabe 4: Temporal Logic

**Kripke 4a:** s0(a)→{s0,s1}; s1(b)→{s1,s2}; s2(c)→{s2}. Initial: s0.

| Formula | Ergebnis | Begründung |
|---|---|---|
| i. AX a | ∅ | s0→{s0,s1}: a(s1)=F ✗; s1,s2 auch ✗ |
| ii. AF EG b | {s1} | EG b=νZ: Z₀=all→Z₁={s1}→Fixpunkt {s1}. AF{s1}: s1✓, s0∉(Pfad s0→s0→...), s2∉(bleibt bei s2). |
| iii. EG(EX b) | {s0, s1} | EX b={s:∃succ mit b}={s0(→s1✓),s1(→s1✓)}. EG{s0,s1}: Z₀→Z₁={s0,s1}(s0→s0✓,s1→s1✓)→Fixpunkt. |
| iv. AG(b∨c) | {s1, s2} | {b∨c}={s1,s2}. s0 kann s0(a only) erreichen ✗. s1,s2: alle erreichbaren in {s1,s2}. |
| v. A(Gb ∨ Gc) | {s2} | s0: Pfad s0→s0→... hat weder Gb noch Gc. s1: Pfad s1→s2: bei s1 kein c, bei s2 kein b → weder Gb noch Gc. s2: alle Pfade bleiben bei s2 mit c → Gc ✓. |

**Kripke 4b:** s0(a)→{s0,s1}; s1(a)→{s2}; s2(b)→{s3}; s3(b)→{s3}. Initial: s0.

### 4b) Tableaux: E(a U (¬EX b))

**Schritt 1: EX b**
= {s: ∃ Nachfolger mit b}:
- s0→{s0,s1}: b(s0)=F, b(s1)=F ✗
- s1→{s2}: b(s2)=T ✓
- s2→{s3}: b(s3)=T ✓
- s3→{s3}: b(s3)=T ✓
**EX b = {s1, s2, s3}**

**Schritt 2: ¬EX b**
= {s0}

**Schritt 3: E[a U {s0}] = μZ.(¬EXb ∪ (a ∩ EX Z))**
- Z₀ = ∅
- Z₁ = {s0} ∪ (a ∩ EX∅) = {s0} ∪ ∅ = {s0}
- Z₂ = {s0} ∪ (a ∩ EX{s0}): EX{s0}={s:∃succ∈{s0}}={s0}(→s0✓). a∩{s0}={s0,s1}∩{s0}={s0}. Z₂={s0}.
- Fixpunkt: **E(a U ¬EX b) = {s0}**

---

## Aufgabe 5: Decision Procedures

### 5a) CDCL

Klauseln: C1=¬x1∨x2, C2=x1∨¬x2, C3=¬x2∨¬x4∨x5, C4=¬x2∨¬x6∨x7,
C5=x3∨x5∨x8, C6=¬x3∨x4, C7=¬x4∨¬x6∨x7, C8=x5∨x6∨¬x7,
C9=¬x5∨¬x6∨x8, C10=¬x7∨¬x8.

**Level 1:** Decide x1=T.
- C1=(F∨x2) → x2=T (BCP@L1)
- C2 satisfied.

**Level 2:** Decide x3=T.
- C6=(F∨x4) → x4=T (BCP@L2)
- C3=(F∨F∨x5) → x5=T (BCP@L2, via x2=T,x4=T)

**Level 3:** Decide x6=T.
- C4=(F∨F∨x7) → x7=T (BCP@L3, via x2=T,x6=T)
- C7=(F∨F∨x7) → x7=T (redundant, via x4=T,x6=T)
- C10=(F∨¬x8) → x8=F (BCP@L3, via x7=T)
- **C9=(F∨F∨F)=CONFLICT!** (x5=T,x6=T,x8=F)

**Konfliktgraph:**
```
x1=T(L1)──C1──>x2=T(L1)──┐
                           ├──C3──>x5=T(L2)──────────────┐
x3=T(L2)──C6──>x4=T(L2)──┘                              │
                                                          ├──C9→CONFLICT
x6=T(L3)──C4──>x7=T(L3)──C10──>x8=F(L3)────────────────┘
```

**Erster UIP:** x6 (der einzige Entscheidungs-Literal auf L3; x6 ist direkt in C9, kein Dominator außer x6 selbst).

**Lernklausel via Resolution:**
1. Resolve Konflikt C9={¬x5,¬x6,x8} mit Antezedent von x8=F (C10={¬x7,¬x8}):
   → {¬x5, ¬x6, ¬x7}
2. Resolve {¬x5,¬x6,¬x7} mit Antezedent von x7=T (C4={¬x2,¬x6,x7}):
   → {¬x5, ¬x6, ¬x2}
3. Noch zwei L3-Literale? Nein: ¬x6(L3), ¬x5(L2), ¬x2(L1). Ein L3-Literal. Fertig.

**Gelernte Klausel: ¬x2 ∨ ¬x5 ∨ ¬x6**

**Backjump:** max(Level(x2)=1, Level(x5)=2) = Level 2. x6=F aus gelernter Klausel propagiert@L2.

### 5b) EUF

F: x1=x2, x3=x4, f(x4)=f(x5), f(x2)=x5.

**Folgerungen aus F:**
- x1=x2 → f(x1)=f(x2)=x5 (via f(x2)=x5)
- x3=x4 → f(x3)=f(x4)=f(x5)

| Formel | Ergebnis | Begründung |
|---|---|---|
| **i.** F ∧ f(x3)≠f(f(x2)) | **UNSAT** | f(x2)=x5 → f(f(x2))=f(x5). x3=x4 → f(x3)=f(x4)=f(x5). Also f(x3)=f(x5)=f(f(x2)). Widerspruch zu f(x3)≠f(f(x2)). Kette: f(x3)=f(x4)=f(x5)=f(f(x2)). |
| **ii.** F ∧ f(x3)=f(f(x1)) | **SAT** | f(f(x1))=f(f(x2))=f(x5) (via x1=x2, f(x2)=x5). f(x3)=f(x5) (aus F). Also f(x3)=f(f(x1)) gilt immer in F! Modell: x1=x2=0,x3=x4=1,x5=2; f(0)=2,f(1)=3,f(2)=3. ✓ |

---

## Aufgabe 6: True/False

| # | Aussage | Antwort | Begründung |
|---|---|---|---|
| 1 | all-p-uses ≡ all-p-uses/some-c-uses wenn jede Def eine p-use hat | **FALSE** | all-p-uses/some-c-uses verlangt zusätzlich mind. 1 c-use pro Def (falls c-uses existieren). Wenn ein Def hat p-use UND c-use: gleiche Test-Suite deckt nicht automatisch auch c-use. |
| 2 | ∀ induktive Invariante I ∃ nicht-induktive Invariante P' mit P'⇒I, P'≢I | **FALSE** | CE: while(false){}: alle Invarianten sind induktiv (Body nie ausgeführt → Erhaltung vakuös). Keine nicht-induktive Invariante existiert. |
| 3 | "e tritt unendlich oft auf" in LTL ausdrückbar | **TRUE** | G(F e) = "immer irgendwann e" = e infinitely often. Gültige LTL-Formel. |
| 4 | ∀ unerfüllbare CNF-Formel ∃ erfüllungs-äquivalente 2-CNF mit genau 2 Literalen/Klausel | **TRUE** | (x∨x)∧(¬x∨¬x) = x∧¬x ist unerfüllbar, hat genau 2 Literale/Klausel, und ist erfüllungs-äquivalent zu jeder UNSAT-Formel (beide UNSAT). |
| 5 | {false}C{true} gilt für beliebiges C | **TRUE** | Partielle Korrektheit: Vorbedingung false ist nie erfüllt → Tripel vakuös wahr für jedes C und jedes Q. |
