# Exam 3 — June 2021 — Lösungen

## Aufgabe 1: Coverage — `gcd(x, y)`

```python
def gcd(x, y):
    if x < y:        # D0
        min_v = x; max_v = y
    else:
        min_v = y; max_v = x
    t = min_v        # L8
    while t > 0:     # D2
        if x%t==0 and y%t==0:  # D1
            return t  # L11
        t = t - 1    # L12
    return max_v     # L13
```
**Tests:** gcd(0,1)=1, gcd(1,0)=1, gcd(2,3)=1

### 1a) Control-Flow Coverage

| Kriterium | Ergebnis | Begründung |
|---|---|---|
| Statement Coverage | ✅ | Alle Statements ausgeführt (gcd(0,1) → return max_v; gcd(2,3) → return t) |
| Decision Coverage | ✅ | D0 T/F ✓, D1 T/F ✓, D2 T/F ✓ |
| Branch Coverage | ✅ | Alle 6 Branches (D0✓, D1✓, D2✓) + beide Returns (return t und return max_v) abgedeckt |
| MC/DC | ❌ | Atom `x%t==0` in D1 immer True (x=2: 2%2=0 ✓, 2%1=0 ✓, nie False). Kein Witness-Paar. |

**Fehlend für MC/DC:** Test mit `x%t≠0` z.B. gcd(3,4): bei t=2 gilt 3%2=1≠0 → (x%t==0)=False.

### 1b) Data-Flow Coverage

| Kriterium | Ergebnis |
|---|---|
| all-defs | ✅ 6/6 |
| all-p-uses | ✅ 4/4 |
| all-c-uses | ❌ 6/8 — fehlend: `(t, L8, L11)` und `(t, L12, L12)` |
| all-c-uses/some-p-uses | ❌ (all-c-uses nicht erfüllt) |
| all-du-paths | ❌ (strengere Anforderung als all-c-uses) |

**Fehlende c-uses erklärt:**
- `(t, L8, L11)`: t@L8=min_v direkt in `return t` verwendet → benötigt Test wo erste Loop-Iteration sofort zurückgibt (t=min_v ist Divisor). Fehlt, da bei gcd(2,3) t=2 nicht sofort zurückgibt.
- `(t, L12, L12)`: t@L12 (nach t=t-1) in nächster Iteration wieder in t=t-1 verwendet → benötigt ≥2 Non-Return-Iterationen.

### 1c) Minimale Ergänzung

**all-c-uses:** Ergänze 2 Tests:
- `gcd(2,4)` → t=min=2: 2%2=0 ∧ 4%2=0 → return t=2 sofort (deckt `(t, L8, L11)`)
- `gcd(4,6)` → t=4: F, t=3: F, t=2: T → 2 Non-Return-Iterationen (deckt `(t, L12, L12)`)

**MC/DC:** Ergänze:
- `gcd(3,4)` → t=3: 3%3=0 ∧ 4%3=1≠0 → D1=F. t=2: 3%2=1≠0 → (x%t==0)=False ✓ MC/DC-Witness für x%t==0

### 1d) Implicit — kein Mutation-Task in diesem Exam

---

## Aufgabe 2: Hoare Logic

```
{true}
if ((m+n) % 2 != 0) { m = m + 1; } else { skip; }
while ((m != 0) && (n != 0)) { m = m-1; n = n-1; }
{(m % 2 == 0)}
```

**Beobachtung:** Nach if/else ist `(m+n)` immer gerade:
- Falls (m+n)%2≠0: m wird m+1 → neue Summe (m+1+n)=(m+n)+1 ist gerade ✓
- Falls (m+n)%2=0: skip → bleibt gerade ✓

**Loop-Invariante: I = (m + n) % 2 = 0**

Z3-Verifikation: alle 3 Checks ✅

**Beweis:**

**Init-Check:** `{true ∧ Prefix} I`
- Nach if/else: (m+n)%2=0 per Konstruktion. **✅**

**Erhaltungs-Check:** `{I ∧ m≠0 ∧ n≠0} m=m-1; n=n-1 {I}`
- Nach Body: (m-1+n-1)%2 = (m+n-2)%2 = (m+n)%2 = 0 **✅**

**Konsequenz-Check (Exit):** `{I ∧ (m=0 ∨ n=0)} → m%2=0`
- I: (m+n)%2=0. 
  - m=0: m%2=0 ✅
  - n=0: (m+0)%2=m%2=0 ✅
- **✅**

**Annotiertes Programm:**
```
{true}
if ((m+n)%2 != 0) { m = m+1; } else { skip; }   // if/else-Regel + Zuweisungsregel
{(m+n) % 2 = 0}   // = I[i=0,s=0... (Init)]
{I}
while ((m != 0) && (n != 0)) {
    {I ∧ m≠0 ∧ n≠0}
    m = m - 1; n = n - 1;
    {I}   // Erhaltung gezeigt
}
{I ∧ (m=0 ∨ n=0)}
{m % 2 = 0}   // Konsequenz-Regel ✅
```

---

## Aufgabe 3: Invariants

**Programm:**
```
if (x == y) { a = b; }
while (x < 42) { x = x+1; y = y+1; }
```

**Nach Prefix:** x=y → a=b (garantiert). Also gilt: (x=y → a=b).

| Formel | Typ | Begründung |
|---|---|---|
| `(a-b) = (x-y)` | **Neither** | CE: x=1,y=2,a=5,b=3: a-b=2≠-1=x-y. (x≠y → kein Zwang auf a,b) |
| `(a≠b) ∨ (x=y)` | **Neither** | CE: x=1,y=2,a=0,b=0: (a≠b)=F ∧ (x=y)=F → False. Äquivalent: a=b→x=y, aber wenn x≠y und a=b: False |
| `(x≠y) ∨ (a=b)` | **Inductive Invariant** | Nach Prefix: x=y→a=b, so: x=y→(a=b)→True; x≠y→True (linke Disjunkt). Loop: x+=1,y+=1, x-y konstant → Invariante erhalten. Z3: Init ✅ Preservation ✅ |

---

## Aufgabe 4: Temporal Logic

**Kripke:** s0(a)→{s0,s1}, s1(a)→s2, s2(b)→s2. Initial: s0.

| Formula | Ergebnis | Begründung |
|---|---|---|
| i. AG a | ∅ | s2 hat b nicht a; von s0 ist s2 erreichbar |
| ii. EG a | {s0} | s0→s0→s0→... hat immer a; von s1: s1→s2(b) → verliert a |
| iii. AF G b | {s1, s2} | s0 hat Pfad s0→s0→... der nie zu s2 kommt → AF fails für s0 |
| iv. AF EG b | {s1, s2} | EG b={s2}; AF{s2}: s1→s2 ✓, s0→s0∞ never → {s1,s2} |
| v. EF G b | {s0, s1, s2} | s0→s1→s2→... → s2 erreichbar von überall via ∃-Pfad |
| vi. EX b | {s1, s2} | s1→s2(b)✓, s2→s2(b)✓; s0→s0,s1 (beide a) ✗ |
| vii. EG F a | {s0} | AF a={s0,s1}; νZ(AF_a ∩ EX Z): nur s0 hat ∞ Pfad durch {s0,s1} |
| viii. A(b U a) | {s0, s1} | s0,s1 haben a → U trivial. s2→s2→...b ∞, a nie → ❌ |
| ix. A(a U b) | {s1, s2} | s1→s2(b) auf allen Pfaden ✓; s0→s0→... b nie ❌ |
| x. E(a U b) | {s0, s1, s2} | s0→s1→s2: a,a,b→U ok; s2: b trivial |

---

## Aufgabe 5: Decision Procedures

### 5a) SAT

**Formel:** 10 Klauseln (at-least-one pairs + at-most-one constraints)

**Ergebnis: SAT** — Lösung: x1=T, x2=F, x3=F, x4=T, x5=F, x6=T

**Verifikation:**
- (x1∨x2)=T ✓, (x3∨x4)=T ✓, (x5∨x6)=T ✓
- (¬x1∨¬x3)=(F∨T)=T ✓, (¬x1∨¬x5)=(F∨T)=T ✓
- (¬x2∨¬x4)=(T∨F)=T ✓, (¬x2∨¬x6)=(T∨F)=T ✓
- (¬x3∨¬x5)=(T∨T)=T ✓, (¬x4∨¬x5)=(F∨T)=T ✓
- (x6∨¬x5∨x1)=(T∨T∨T)=T ✓

### 5b) EUF

| Formel | Ergebnis | Begründung |
|---|---|---|
| `i=j∧j=k∧k=l∧l≠m∧l≠n∧m=n∧o≠p∧o=q` | **SAT** | Klassen: {i,j,k,l}, {m,n}, {o,q}, {p}. Alle ≠-Bedingungen zwischen verschiedenen Klassen. Keine Kongruenz-Verletzung. |
| `i=j∧j=k∧k=l∧l≠n∧m=n∧g(i)≠g(m)∧f(i)≠f(l)` | **UNSAT** | i=j=k=l → f(i)=f(l) per Kongruenz → f(i)≠f(l) Widerspruch ❌ |

### 5c) OBDD für (x1⊕x2) ∧ x1

**Vereinfachung:** (x1⊕x2)∧x1 = ((x1∧¬x2)∨(¬x1∧x2))∧x1 = x1∧¬x2

**OBDD (Ordnung x1>x2):**
```
       x1
      /    \
   F=0     x2
           / \
          1   0
         (F) (T)
```
(x1=F → 0; x1=T,x2=F → 1; x1=T,x2=T → 0)

**Konstruktion:**
1. Baue BDD für x1⊕x2: Shannon-Expansion bzgl x1:
   - x1=T: T⊕x2 = ¬x2 → Branch auf x2: (F→1, T→0)
   - x1=F: F⊕x2 = x2 → Branch auf x2: (F→0, T→1)
2. Konjunktion mit x1:
   - x1=F: (x1⊕x2)∧F = F → leaf 0
   - x1=T: (T⊕x2)∧T = ¬x2 → Branch auf x2: (F→1, T→0)
3. Finales OBDD: 3 Knoten + 2 Blätter
