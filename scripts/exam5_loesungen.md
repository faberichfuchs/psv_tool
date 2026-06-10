# Exam 5 — October 2024 — Lösungen

## Aufgabe 1: Coverage — `is_coprime` (v2)

```python
def is_coprime(n1, n2):
    a, b = n1, n2                              # L1
    while a != b and a > 1 and b > 1:         # D0: L2
        if a > b:                              # D1: L3
            a = a - b                         # L4
        else:
            b = b - a                         # L6
    return (a == 1 or b == 1)                 # D2: L9 (p-use, kein c-use)
```

**Tests:** (0,0)→False, (2,3)→True, (6,2)→False. Note: ||/&& nicht short-circuited.

**Traces:**
- (0,0): a=0,b=0 → D0: (0≠0)=F → L9: (0==1 or 0==1)=False
- (2,3): D0:T → D1:F → b=1 → D0:(2≠1∧T∧F)=F → L9:(2==1 or 1==1)=True
- (6,2): D0:T→D1:T→a=4; D0:T→D1:T→a=2; D0:F→L9:False

### 1a) Control-Flow Coverage

| Kriterium | Ergebnis | Begründung |
|---|---|---|
| Statement Coverage | ✅ | L4:(6,2); L6:(2,3); L9: alle. Alle Statements erreicht. |
| Decision Coverage | ✅ | D0:T/F✓; D1:T(6,2)/F(2,3)✓; D2:T(2,3)/F(0,0)✓ |
| Condition Coverage | ❌ | D2-Atom (a==1): immer False in Test-Set. (0,0)→a=0; (2,3)→a=2; (6,2)→a=2. Niemals a=1 am Ende. |
| MC/DC | ❌ | D0 Atoms (a≠b),(a>1),(b>1) brauchen unabhängige Witnesses. D2 Atom (a==1) nie True. |

**MC/DC Details:**
- D0: Atom A=(a≠b): T: (2,3)✓, F: (0,0)✓. Aber für Independence: B=(a>1) und C=(b>1) müssen dabei konstant sein. Kein Test mit A=F∧B=T∧C=T (z.B. (3,3)). Fehlt!
- D2: (a==1) braucht Test wo a=1 am Ende (z.B. gcd=1 via a-Seite): (3,2)→a=1.

### 1b) Data-Flow Coverage

Defs: a@L1, a@L4; b@L1, b@L6. L9 = p-use (laut Aufgabe).

| Kriterium | Ergebnis |
|---|---|
| all-defs | ✅ — a@L1→L2(p)✓; a@L4→L2(p)✓; b@L1→L2(p)✓; b@L6→L2(p)✓ |
| all-c-uses | ❌ — (a,L4,L6) fehlt: nach a=a-b muss L6 mit neuem a ausgeführt werden |
| all-p-uses | ❌ — (b,L6,L3) fehlt: nach b=b-a muss Loop fortgesetzt und L3 erreicht werden. Nie im Test-Set (nach b→1 exitiert Loop sofort). |
| all-p-uses/some-c-uses | ❌ — (all-p-uses nicht erfüllt) |

**Fehlende c-use Paare:**
- `(a, L4, L6)`: nach a=a-b, dann Loop fortgesetzt mit D1=False → L6. Test: (5,3).
- `(b, L6, L4)`: nach b=b-a, dann D1=True → L4. Test: (3,5).
- `(b, L6, L6)`: b@L6 in nächster L6-Iteration verwendet. Test: (2,7) oder (3,7).

### 1c) Minimale Ergänzung

**all-c-uses/some-p-uses:** Ergänze 3 Tests:
- (5,3): deckt (a,L4,L6) — a=5-3=2(L4), dann b=3-2=1(L6)
- (3,5): deckt (b,L6,L4) — b=5-3=2(L6), dann a=3-2=1(L4)
- (2,7): deckt (b,L6,L6) — b=7-2=5(L6), dann b=5-2=3(L6)

| n1 | n2 | Output |
|---|---|---|
| 5 | 3 | true |
| 3 | 5 | true |
| 2 | 7 | true |

**condition/decision coverage:** Ergänze 1 Test:
- (3,2): a=3→D1:T→a=1; D0:F→L9:(a==1)=True. Deckt D2-Atom (a==1)=True ✓.
- (3,3): deckt D0-Atom (a≠b)=F mit a>1,b>1. Deckt auch MC/DC-Witness für A.

| n1 | n2 | Output |
|---|---|---|
| 3 | 2 | true |

### 1d) Mutation: `a - b` → `a % b`

**Kein Killtest existiert — Mutant ist äquivalent.**

**Begründung:** Die Funktion ist_coprime basiert auf dem Euklidischen Algorithmus. Die Variante mit a=a-b (wiederholte Subtraktion) ist mathematisch äquivalent zu a=a%b (direkte Modulo-Reduktion), da beide denselben ggT berechnen. Die Funktion gibt True zurück gdw. ggT(n1,n2)=1. Da beide Varianten denselben ggT liefern und die Abbruchbedingung korrekt ist (a=0 nach a%b → b>1 → b==1 false; b=gcd), ist keine andere Ausgabe möglich.

---

## Aufgabe 2: Hoare Logic

Beweis dass I = **(b ⇒ i ≤ 10)** eine induktive Invariante ist:

```
{(b ⇒ i ≤ 10)}
i = 2;    // Zuweisungsregel: I[i/2] = (b ⇒ 2≤10) = T ✓  
b = true;  // Zuweisungsregel: I[b/true] = (true ⇒ i≤10) = (i≤10)
{(i = 2) ∧ (b = true)}
{(b ⇒ i ≤ 10)}  // Konsequenz: i=2, b=true → (true⇒2≤10)=T ✓
while (b) {
    {(b ⇒ i ≤ 10) ∧ b}   // While-Regel Vorbedingung
    {i ≤ 10}              // Konsequenz: I ∧ b → b=T ∧ (T⇒i≤10) → i≤10
    i = i + 1;
    {i ≤ 11}              // Zuweisungsregel: (i+1)≤11 ← i≤10 ✓
    if (i < 1 || i > 10) {
        b = false;
        {(false ⇒ i ≤ 10)}  // Zuweisungsregel: I[b/false] = T ✓
        {I}
    } else {
        skip;
        {i ≤ 11 ∧ ¬(i<1 ∨ i>10)}
        {1 ≤ i ≤ 10}      // Aus ¬(i<1 ∨ i>10): 1≤i≤10; b unverändert=true
        {(b ⇒ i ≤ 10)}    // b=true ∧ i≤10 → T⇒T=T ✓
        {I}
    }
    {I}  // If-Else-Regel: beide Branches liefern I ✓
}
{I ∧ ¬b}
{true ⇒ i ≤ 10 ∧ b=false} ← nachher verlassen
```

**Init:** {true} → i=2; b=true; → (true⇒2≤10)=T ✅
**Erhaltung:** {I ∧ b} body {I} gezeigt oben ✅

---

## Aufgabe 3: Loop Invariants

**Programm:** c=b%2; a=b+c; while(b>0) { b=b-1; a=a+1; c=c+1; }

**Analyse:** Nach k Iterationen (b₀=initialer b-Wert):
- b = b₀ - k
- a = b₀ + (b₀%2) + k  
- c = (b₀%2) + k
- **Key:** b+c = (b₀-k)+(b₀%2+k) = b₀+b₀%2 = konstant!
- a-b = (b₀%2) + 2k; 2c = 2(b₀%2) + 2k

| Formel | Typ | Begründung |
|---|---|---|
| `(a-b) ≤ 2c` | **Inductive Invariant** | a-b=b₀%2+2k ≤ 2b₀%2+2k=2c (da b₀%2∈{0,1}≤2b₀%2... hmm for b₀ even: 0+2k≤0+2k ✓; for b₀ odd: 1+2k≤2+2k ✓). Body: a'-b'=(a+1)-(b-1)=a-b+2; 2c'=2(c+1)=2c+2. Falls a-b≤2c → a-b+2≤2c+2 ✓ |
| `(b+c)%2 ≤ a%2` | **Inductive Invariant** | (b+c)=b₀+b₀%2=konst; (b+c)%2=0 immer (b₀ even: b₀%2=0; b₀ odd: b₀+1 even). 0≤a%2 immer ✓. Body: (b'+c')%2=(b+c)%2=0; a'%2=(a+1)%2∈{0,1} ≥ 0 ✓ |
| `(a-b) = 2c` | **Neither** | Reachable CE: b₀=1 → c=1, a=2, b=1. a-b=1, 2c=2 → 1≠2. Invariante gilt nicht am Loop-Eintritt. |

**CE für Neither (iii):** b₀=1, k=0: a=2, b=1, c=1. a-b=1 ≠ 2=2c.

---

## Aufgabe 4: Temporal Logic

**Kripke:** s0(a)→s1(b)→s2(a)→s2 (s2 self-loop). Initial: s0.

### 4a) CTL Formeln

| Formula | Ergebnis | Begründung |
|---|---|---|
| i. EG b | ∅ | s1→s2(a), verlässt b. Kein unendlicher b-Pfad. |
| ii. AG(a⇒EF b) | ∅ | EF b={s0,s1} (s2→s2→...b nie). s2: a=T, EF b=F → a⇒EF b=F. Von s0 erreichbar → AG fails. |
| iii. EX a | {s1, s2} | s1→s2(a)✓; s2→s2(a)✓; s0→s1(b)✗ |
| iv. E(b U a) | {s0, s1, s2} | s0,s2: a sofort. s1: b∧(s1→s2(a)) ✓ |
| v. AF a | {s0, s1, s2} | s2: a✓; s1→s2✓; s0→s1→s2✓ |

### 4b) Tableaux: EX(¬EG a)

**Schritt 1: EG a** (νZ.(a ∩ EX Z))
- Z₀ = {s0,s1,s2}
- Z₁ = {s: a(s) ∧ ∃ succ in Z₀} = {s0,s2} (s0,s2 haben a; alle haben Nachfolger)
- Z₂ = {s: a(s) ∧ ∃ succ in {s0,s2}}:
  - EX{s0,s2}: s0→s1∉{s0,s2}✗; s1→s2∈✓; s2→s2∈✓ → EX{s0,s2}={s1,s2}
  - Z₂ = {s0,s2} ∩ {s1,s2} = {s2}
- Z₃ = {s: a(s) ∧ ∃ succ in {s2}}:
  - EX{s2}: s0→s1✗; s1→s2✓; s2→s2✓ → EX{s2}={s1,s2}
  - Z₃ = {s0,s2} ∩ {s1,s2} = {s2}
- **Fixpunkt: EG a = {s2}**

**Schritt 2: ¬EG a** = {s0, s1}

**Schritt 3: EX({s0,s1})**:
- s0→s1 ∈ {s0,s1} ✓
- s1→s2 ∉ {s0,s1} ✗
- s2→s2 ∉ {s0,s1} ✗

**Ergebnis: EX(¬EG a) = {s0}**

---

## Aufgabe 5: Decision Procedures

### 5a) SAT

**Formel:** (¬x₁∨x₂)∧(x₁∨¬x₂)∧(¬x₃∨x₄)∧(x₃∨¬x₄)∧(¬x₁∨x₂∨x₃)∧(¬x₁∨x₂∨x₄)∧(x₁∨¬x₂∨¬x₃)∧(x₁∨¬x₂∨¬x₄)

**Ergebnis: SAT** — 4 erfüllende Belegungen

**Analyse:**
- Kl. 1+2: x₁≡x₂ (Äquivalenz)
- Kl. 3+4: x₃≡x₄ (Äquivalenz)

**Fall x₁=x₂=T:**
- Kl. 5: (F∨T∨x₃)=T ✓ (immer)
- Kl. 6: T ✓; Kl. 7,8: T ✓ — **beide Werte für x₃=x₄ funktionieren**

**Fall x₁=x₂=F:**
- Kl. 5: (T∨F∨x₃)=T ✓
- Alle ✓ — **beide Werte für x₃=x₄ funktionieren**

**Lösungen:** (T,T,T,T), (T,T,F,F), (F,F,T,T), (F,F,F,F)

### 5b) EUF

| Formel | Ergebnis | Begründung |
|---|---|---|
| **i.** (a=b)∧(u=v)∧(x=y)∧(c=a)∧(x≠c)∧(w=v)∧(y=z)∧(w≠a)∧(f(a)≠f(x))∧(f(y)=f(v)) | **SAT** | Klassen: {a,b,c},{u,v,w},{x,y,z}. x≠c,w≠a: verschiedene Klassen✓. f(y)=f(v): y∈{x,y,z},v∈{u,v,w}→f(2. Klasse)=f(3. Klasse)✓. f(a)≠f(x): 1.≠2. Klasse✓. Modell: a=0,u=1,x=2; f(0)=3,f(1)=f(2)=5 |
| **ii.** (a=b)∧(c=d)∧(f(a)=f(d))∧(f(c)≠f(d)) | **UNSAT** | c=d → f(c)=f(d) per Kongruenz → Widerspruch mit f(c)≠f(d) |

---

## Aufgabe 6: True/False

| # | Aussage | Antwort | Begründung |
|---|---|---|---|
| 1 | AG a ≡ EG a auf Kripke mit nur einem einzigen Pfad | **TRUE** | Bei einem Pfad: ∀-Pfad = ∃-Pfad (nur einer). AG=EG auf Einzel-Pfad-Strukturen. |
| 2 | Zu jeder Formel F ∃ SAT-äquivalente Formel G ohne Variablen | **TRUE** | G=⊤ falls F SAT, G=⊥ falls F UNSAT. G und F SAT-äquivalent per Definition. |
| 3 | Decision Coverage für Programm → Decision Coverage für äquivalenten Mutanten | **FALSE** | Äquivalenter Mutant hat gleiche Ein-/Ausgabe aber möglicherweise andere Entscheidungsstruktur. Coverage-Tests für Original-Decisions decken Mutant-Decisions nicht ab. |
| 4 | Jede Formel in Gleichheitslogik mit endlich vielen Variablen hat ein Modell mit endlicher Domäne | **TRUE** | n Variablen benötigen max. n verschiedene Werte. Endliche Domäne {0,...,n-1} reicht. |
| 5 | Für jede nicht-induktive Invariante P ∃ induktive Invariante die P impliziert | **TRUE** | Die Menge der erreichbaren Zustände (Reachability-Prädikat) ist immer induktiv und impliziert jede Invariante (da P auf allen erreichbaren Zuständen gilt). |
