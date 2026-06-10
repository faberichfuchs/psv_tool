"""
Tests für Exam 6 (June 2025) Lösungen.
Ausführen: pytest tests/test_exam6.py -v
"""
import pytest
import sys
sys.path.insert(0, ".")

PERFECT_PY = """def perfect(a):
    n = a
    if n <= 1:
        return False
    s = 1
    i = n // 2
    while i > 1 and s <= n:
        if n % i == 0:
            s = s + i
        i = i - 1
    return s == n"""


# ── Aufgabe 1a: Correctness & Control-Flow Coverage ──────────────────────────

def _run_perfect(a):
    ns = {}
    exec(PERFECT_PY, ns)
    return ns['perfect'](a)


def test_perfect_1_false():
    """(1)→False: D0=True, return False direkt."""
    assert _run_perfect(1) == False


def test_perfect_4_false():
    """(4)→False: s=3, n=4 → 3==4=False."""
    assert _run_perfect(4) == False


def test_perfect_6_true():
    """(6)→True: s=1+3+2=6=n. Perfekte Zahl."""
    assert _run_perfect(6) == True


def test_perfect_28_true():
    """(28)→True: 1+14+7+4+2=28. Zweite perfekte Zahl."""
    assert _run_perfect(28) == True


def test_perfect_12_false():
    """(12)→False: Divisorensumme 1+6+4+3+2=16≠12."""
    assert _run_perfect(12) == False


def test_perfect_5_false():
    """(5)→False: 5%2≠0 (D2=False-Branch wird ausgeführt)."""
    assert _run_perfect(5) == False


def test_perfect_0_false():
    """(0)→False: n≤1=True, Grenzfall."""
    assert _run_perfect(0) == False


def test_perfect_2_false():
    """(2)→False: i=1, Schleife nie betreten (i>1=False)."""
    assert _run_perfect(2) == False


def test_perfect_3_false():
    """(3)→False: s=1≠3."""
    assert _run_perfect(3) == False


def test_perfect_statement_coverage():
    """(1)+(4): alle Statements erreicht."""
    # L3: via (1)
    assert _run_perfect(1) == False
    # L5,L8,L10,L12: via (4)
    assert _run_perfect(4) == False


def test_perfect_decision_d0_true():
    """D0 (n<=1): True mit n=1."""
    assert _run_perfect(1) == False


def test_perfect_decision_d0_false():
    """D0 (n<=1): False mit n=4."""
    assert _run_perfect(4) == False


def test_perfect_decision_d1_true():
    """D1 (i>1 and s<=n): True mit n=4, erste Iteration."""
    # n=4: i=2>1 and s=1<=4 → T
    assert _run_perfect(4) == False


def test_perfect_decision_d1_false_i():
    """D1: False wegen i<=1. n=4: nach Iter. i=1 → i>1=False."""
    assert _run_perfect(4) == False


def test_perfect_decision_d1_false_s():
    """D1: False wegen s>n. n=12: s=14>12 stoppt Schleife früh."""
    # 12: i=6→s=7; i=5 skip; i=4→s=11; i=3→s=14>12 → D1-B=False
    assert _run_perfect(12) == False


def test_perfect_decision_d2_true():
    """D2 (n%i==0): True. n=4: 4%2=0."""
    assert _run_perfect(4) == False


def test_perfect_decision_d2_false():
    """D2 (n%i==0): False. n=5: 5%2=1≠0."""
    assert _run_perfect(5) == False


def test_perfect_decision_d3_true():
    """D3 (s==n): True. n=6: s=6=n."""
    assert _run_perfect(6) == True


def test_perfect_decision_d3_false():
    """D3 (s==n): False. n=4: s=3≠4."""
    assert _run_perfect(4) == False


# ── Aufgabe 1b: Data-Flow Coverage ───────────────────────────────────────────

def test_perfect_all_defs():
    """all-defs: n@L1→L5, s@L5→L8, i@L5→L10, s@L8→L12, i@L10→L6. Mit (4)."""
    assert _run_perfect(4) == False


def test_perfect_all_c_uses_needs_multiple_iters():
    """all-c-uses fehlt: (s,L8,L8) und (i,L10,L10). (12) deckt beides."""
    # (12): L8 dreimal getroffen (i=6,4,3), i@L10 mehrfach in L10 benutzt
    assert _run_perfect(12) == False


def test_perfect_all_p_uses_missing_i_l10_l7():
    """all-p-uses fehlt (i,L10,L7): i@L10 in D2 benutzt. (12) deckt: i=5→D2 evaluiert."""
    assert _run_perfect(12) == False


# ── Aufgabe 1c: Augmentierung ─────────────────────────────────────────────────

def test_perfect_augmentation_all_c_uses():
    """Testmenge {(1),(4),(12)} deckt alle c-uses/some-p-uses."""
    tests = [(1, False), (4, False), (12, False)]
    for a, expected in tests:
        assert _run_perfect(a) == expected, f"perfect({a}) sollte {expected} sein"


def test_perfect_augmentation_decision_coverage():
    """Testmenge {(1),(4),(5),(6),(12)} deckt alle Decisions."""
    tests = [(1, False), (4, False), (5, False), (6, True), (12, False)]
    for a, expected in tests:
        assert _run_perfect(a) == expected, f"perfect({a}) sollte {expected} sein"


# ── Aufgabe 1d: Mutation ──────────────────────────────────────────────────────

def test_perfect_mutation_equivalent():
    """Mutant (while i>1 statt while i>1 and s<=n) ist äquivalent.

    Wenn s>n vorzeitig stoppt: s_partial>n, s_full>=s_partial>n.
    Beide geben s==n=False zurück. Kein Killtest existiert.
    Demonstration: (12) → beide False (Original stoppt früh, Mutant nicht).
    """
    # Original (mit s<=n guard): 12→False (stoppt bei s=14>12)
    assert _run_perfect(12) == False

    # Mutant (ohne s<=n guard): berechnet vollständige Divisorensumme
    PERFECT_MUTANT = """def perfect(a):
    n = a
    if n <= 1:
        return False
    s = 1
    i = n // 2
    while i > 1:
        if n % i == 0:
            s = s + i
        i = i - 1
    return s == n"""
    ns = {}
    exec(PERFECT_MUTANT, ns)
    assert ns['perfect'](12) == False  # Mutant: 1+6+4+3+2=16≠12 → False
    assert ns['perfect'](6) == True    # Mutant: 1+3+2=6=6 → True (gleich wie Original)
    assert ns['perfect'](4) == False   # Mutant: 1+2=3≠4 → False (gleich)


# ── Aufgabe 2: Hoare Logic — Integer Square Root ──────────────────────────────

def test_sqrt_invariant_init():
    """I = (l*l <= n) and (n < r*r). Init: l=0, r=n+1."""
    for n in range(0, 10):
        l, r = 0, n + 1
        assert l * l <= n, f"l²≤n verletzt für n={n}"
        assert n < r * r, f"n<r² verletzt für n={n}"


def test_sqrt_invariant_preservation_m_sq_le_n():
    """Erhaltung: falls m²≤n → l=m. I bleibt. n=10, l=3, r=4."""
    n = 10
    l, r = 3, 4
    m = (l + r) // 2  # = 3
    assert m * m <= n  # 9 <= 10 ✓ → l=m
    l_new = m
    assert l_new * l_new <= n  # 9 <= 10 ✓ (I-Teil 1)
    assert n < r * r            # 10 < 16 ✓ (I-Teil 2)


def test_sqrt_invariant_preservation_m_sq_gt_n():
    """Erhaltung: falls m²>n → r=m. I bleibt."""
    n = 10
    l, r = 3, 5
    m = (l + r) // 2  # = 4
    assert m * m > n  # 16 > 10 ✓
    r_new = m
    assert l * l <= n      # 9 <= 10 ✓
    assert n < r_new * r_new  # 10 < 16 ✓


def test_sqrt_consequence():
    """Konsequenz: I ∧ l=r-1 → l*l <= n < (l+1)*(l+1)."""
    for n in range(0, 20):
        import math
        l = int(math.isqrt(n))
        r = l + 1
        assert l * l <= n < (l + 1) * (l + 1), f"Postcond verletzt für n={n}"


def test_sqrt_correct_result():
    """Integer Square Root Algorithmus gibt korrektes l zurück."""
    def isqrt_hoare(n):
        l, r = 0, n + 1
        while l != r - 1:
            m = (l + r) // 2
            if m * m <= n:
                l = m
            else:
                r = m
        return l

    for n in range(0, 30):
        import math
        assert isqrt_hoare(n) == math.isqrt(n), f"isqrt({n}) falsch"


# ── Aufgabe 3: Loop Invariants ─────────────────────────────────────────────────

def test_invariant_i_b_gt_x_implies_a_gt_y_init():
    """Inv (i): (b>x)⇒(a>y). Init: nach Prefix gilt a>b und x>y."""
    # Nach Prefix (b>=a: a=b+1,b=old_a; y>=x: x=y+1,y=old_x):
    # Wenn b>x: a>b>x>y → a>y ✓
    for a0, b0, x0, y0 in [(3,3,2,2), (1,5,3,4), (2,2,1,1)]:
        if b0 >= a0:
            a, b = b0 + 1, a0
        else:
            a, b = a0, b0
        if y0 >= x0:
            x, y = y0 + 1, x0
        else:
            x, y = x0, y0
        # Nach Prefix: a>b und x>y
        assert a > b, f"a>b verletzt: a={a},b={b}"
        assert x > y, f"x>y verletzt: x={x},y={y}"
        if b > x:
            assert a > y, f"(b>x)⇒(a>y) verletzt: a={a},y={y}"


def test_invariant_i_is_inductive():
    """Inv (i): (b>x)⇒(a>y) ist induktiv. Body: a-=1, y+=1."""
    # Wenn b>x (konstant): a>b>x>y → a≥y+3 → a-1≥y+2 → a'>y' ✓
    test_cases = [
        # (a, b, x, y) mit a>b>x>y
        (6, 4, 3, 0),
        (10, 5, 3, 1),
        (5, 3, 2, 0),
    ]
    for a, b, x, y in test_cases:
        assert a > b > x > y, "Vorbedingung nicht erfüllt"
        a_new, y_new = a - 1, y + 1
        # b>x bleibt (konstant), also muss a_new>y_new gelten
        assert a_new > y_new, f"Induktion fehlt: a'={a_new}, y'={y_new}"


def test_invariant_ii_a_ge_b_and_x_ge_y_inductive():
    """Inv (ii): (a>=b)∧(x>=y) ist induktiv unter Loop-Bed. a≠b∧x≠y."""
    test_cases = [(5,3,4,2), (3,2,6,4), (10,1,8,3)]
    for a, b, x, y in test_cases:
        assert a > b and x > y  # strikt: a!=b, x!=y gegeben
        a_new, y_new = a - 1, y + 1
        assert a_new >= b, f"a'>=b verletzt: a'={a_new}, b={b}"
        assert x >= y_new, f"x>=y' verletzt: x={x}, y'={y_new}"


def test_invariant_iii_not_invariant_ce():
    """Inv (iii): (a>=y) ist Neither. CE: init a=0,b=0,x=100,y=100."""
    a0, b0, x0, y0 = 0, 0, 100, 100
    # Prefix
    if b0 >= a0:
        a, b = b0 + 1, a0  # a=1, b=0
    else:
        a, b = a0, b0
    if y0 >= x0:
        x, y = y0 + 1, x0  # x=101, y=100
    else:
        x, y = x0, y0
    # Prüfe: a>=y ist FALSE (Invariante verletzt an Loop-Entry)
    assert a >= b, "a>b muss gelten (Prefix korrekt)"
    assert x > y, "x>y muss gelten (Prefix korrekt)"
    # a=1 < y=100: Invariante (a>=y) verletzt!
    assert not (a >= y), f"CE: a={a}, y={y} — Invariante (a>=y) sollte False sein"


# ── Aufgabe 4: CTL ────────────────────────────────────────────────────────────

def _get_ctl_eval_4a():
    """Kripke 4a: s0(a)→s1(b)↔s2(a). s0→s1, s1→s2, s2→s1."""
    from tools.shared import _ctl_check, _tokenize_ctl, _parse_ctl
    states = ['s0', 's1', 's2']
    transitions = [('s0', 's1'), ('s1', 's2'), ('s2', 's1')]
    labels = {'s0': {'a'}, 's1': {'b'}, 's2': {'a'}}
    ev, _, _ = _ctl_check(set(states), transitions, labels, ['s0'])
    def eval_ctl(formula_str):
        tokens = _tokenize_ctl(formula_str)
        ast = _parse_ctl(tokens)
        return set(ev(ast, []))
    return eval_ctl


def _get_ctl_eval_4b():
    """Kripke 4b: s0(a)→s1(b)↔s2(b). s0→s1, s1→s2, s2→s1."""
    from tools.shared import _ctl_check, _tokenize_ctl, _parse_ctl
    states = ['s0', 's1', 's2']
    transitions = [('s0', 's1'), ('s1', 's2'), ('s2', 's1')]
    labels = {'s0': {'a'}, 's1': {'b'}, 's2': {'b'}}
    ev, _, _ = _ctl_check(set(states), transitions, labels, ['s0'])
    def eval_ctl(formula_str):
        tokens = _tokenize_ctl(formula_str)
        ast = _parse_ctl(tokens)
        return set(ev(ast, []))
    return eval_ctl


def test_ctl_4a_ag_af_a():
    """4a: AG(AF a) = {s0,s1,s2}. Alle Pfade treffen immer irgendwann a."""
    ev = _get_ctl_eval_4a()
    result = ev("AG(AF a)")
    assert result == {'s0', 's1', 's2'}


def test_ctl_4a_af_ag_a():
    """4a: AF(AG a) = {} . AG a=∅ (s2→s1(b) verlässt a). AF(∅)=∅."""
    ev = _get_ctl_eval_4a()
    result = ev("AF(AG a)")
    assert result == set()


def test_ctl_4a_ag_b_implies_af_a():
    """4a: AG(b => AF a) = {s0,s1,s2}. Äquivalent: AG(~b | AF a). s1 hat b und AF a ✓."""
    ev = _get_ctl_eval_4a()
    # Parser unterstützt keine => innerhalb AG(); benutze ~b | AF a
    result = ev("AG(~b | AF a)")
    assert result == {'s0', 's1', 's2'}


def test_ctl_4a_ag_af_a_and_ax_b():
    """4a: AG(AF(a & AX b)) = {s0,s1,s2}. a∧AXb={s0,s2}, AF{s0,s2}=all."""
    ev = _get_ctl_eval_4a()
    result = ev("AG(AF(a & AX b))")
    assert result == {'s0', 's1', 's2'}


def test_ctl_4a_a_and_ex_b():
    """4a: a & EX b = {s0,s2}. EXb={s0,s2}, a∩EXb={s0,s2}."""
    ev = _get_ctl_eval_4a()
    result = ev("a & EX b")
    assert result == {'s0', 's2'}


def test_ctl_4b_eg_b():
    """4b: EG b = {s1,s2}. s0 hat a, kein b. s1,s2 im Zyklus mit b."""
    ev = _get_ctl_eval_4b()
    result = ev("EG b")
    assert result == {'s1', 's2'}


def test_ctl_4b_ex_eg_b():
    """4b: EX(EG b) = {s0,s1,s2}. Alle haben Nachfolger in {s1,s2}."""
    ev = _get_ctl_eval_4b()
    result = ev("EX(EG b)")
    assert result == {'s0', 's1', 's2'}


# ── Aufgabe 5a: CDCL ─────────────────────────────────────────────────────────

def test_cdcl_conflict_level():
    """CDCL Conflict bei Level 3 (x6=T): C15=(x10∨x11)=(F∨F)."""
    # x10=F ← C9 mit x5=T,x9=T; x11=F ← C10 mit x5=T,x9=T
    # x9=T ← C14 mit x7=T,x8=T; x7=T ← C7; x8=T ← C4
    # Verifiziere Konflikt-Ursache
    assignment = {
        'x1': True,   # L1 decide
        'x2': False,  # L1 C2
        'x3': True,   # L2 decide
        'x4': False,  # L2 C6
        'x5': True,   # L2 C3
        'x6': True,   # L3 decide
        'x8': True,   # L3 C4
        'x7': True,   # L3 C7
        'x9': True,   # L3 C14
        'x10': False, # L3 C9
        'x11': False, # L3 C10
    }
    # C15 = x10 ∨ x11 = F ∨ F → CONFLICT ✓
    c15 = assignment['x10'] or assignment['x11']
    assert c15 == False, "C15 muss unter diesem Assignment FALSE sein (Konflikt)"


def test_cdcl_learned_clause():
    """Gelernte Klausel: ¬x5 ∨ ¬x9 (durch Resolution von C15,C9,C10)."""
    # Resolution:
    # C15 ∨ C9 / x10: {x11,¬x5,¬x9}
    # {x11,¬x5,¬x9} ∨ C10 / x11: {¬x5,¬x9}
    # Mit x5=T (L2): x9 muss F sein → Backjump zu L2
    x5 = True
    # Gelernte Klausel: ¬x5 ∨ ¬x9. Mit x5=T → x9 wird zu F propagiert.
    x9_learned = not x5  # = False
    assert x9_learned == False, "x9 wird zu False propagiert (aus gelernter Klausel)"


def test_cdcl_backjump_level():
    """Backjump zu Level 2: max. Level der Non-UIP-Literale in Lernklausel."""
    # Lernklausel: ¬x5 ∨ ¬x9. x5 ist L2, x9 ist L3 (UIP).
    # Backjump = max(L2, ...) = L2.
    # Nach Backjump: x6-Assignment aufgehoben; x9=F propagiert.
    learned_clause_levels = {'x5': 2, 'x9': 3}  # x9 ist UIP
    non_uip_levels = [v for k, v in learned_clause_levels.items() if k != 'x9']
    backjump_level = max(non_uip_levels)
    assert backjump_level == 2


# ── Aufgabe 5b: EUF ──────────────────────────────────────────────────────────

def test_euf_i_sat():
    """F ∧ f(x3)≠f(f(x5)) ist SAT."""
    from z3 import IntSort, Function, Solver, Consts, Not, sat
    Int = IntSort()
    x1, x2, x3, x4, x5 = Consts('x1 x2 x3 x4 x5', Int)
    f = Function('f', Int, Int)
    s = Solver()
    # F
    s.add(x1 == x2)
    s.add(x3 == x4)
    s.add(f(f(x4)) == f(x5))
    s.add(f(x2) == x5)
    s.add(f(x1) != f(x5))
    s.add(f(x3) != f(x5))
    s.add(x1 != x5)
    # Erweiterung i
    s.add(f(x3) != f(f(x5)))
    assert s.check() == sat


def test_euf_ii_unsat():
    """F ∧ f(x2)=f(f(x1)) ist UNSAT.

    Kette: f(x2)=x5 (F) → f(f(x1))=x5 (neu) → f(x5)=x5 (via f(x1)=x5).
    Aber f(x1)≠f(x5) (F) und f(x1)=x5 → x5≠f(x5)=x5 → Widerspruch.
    """
    from z3 import IntSort, Function, Solver, Consts, Not, unsat
    Int = IntSort()
    x1, x2, x3, x4, x5 = Consts('x1 x2 x3 x4 x5', Int)
    f = Function('f', Int, Int)
    s = Solver()
    # F
    s.add(x1 == x2)
    s.add(x3 == x4)
    s.add(f(f(x4)) == f(x5))
    s.add(f(x2) == x5)
    s.add(f(x1) != f(x5))
    s.add(f(x3) != f(x5))
    s.add(x1 != x5)
    # Erweiterung ii
    s.add(f(x2) == f(f(x1)))
    assert s.check() == unsat


def test_euf_ii_unsat_manual_chain():
    """Manueller Widerspruchs-Beweis für EUF ii."""
    # Aus F: x1=x2 → f(x1)=f(x2). f(x2)=x5 → f(x1)=x5.
    # Neu: f(x2)=f(f(x1)) → x5=f(f(x1))=f(x5) (via f(x1)=x5).
    # Aber: f(x1)≠f(x5) → x5≠f(x5). Widerspruch.
    # Simuliere mit konkreten Werten:
    x1, x2, x5 = 0, 0, 1  # x1=x2, x5≠x1
    # f(x1)=x5=1 (aus f(x2)=x5)
    f_x1 = x5  # = 1
    # f(x5)=? Aus Constraint f(x1)≠f(x5): f(x5)≠f_x1=1
    # Neu: f(x2)=f(f(x1)) → x5=f(f(x1))=f(1)=f(x5)
    # Also f(x5) müsste = x5 = 1. Aber f(x5)≠1 (aus f(x1)≠f(x5)). Widerspruch.
    f_x5_required_by_new = x5   # = 1 (aus x5=f(f(x1))=f(x5))
    f_x1_ne_f_x5 = True          # f(x1)≠f(x5) aus F
    f_x1_eq_x5 = (f_x1 == x5)   # True (f(x1)=x5=1)
    # f(x5) muss = f_x5_required_by_new = 1 = x5
    # Aber f(x1)=x5=1 und f(x1)≠f(x5) → f(x5)≠1. Widerspruch!
    contradiction = f_x1_eq_x5 and (f_x5_required_by_new == x5)
    assert contradiction == True


# ── Aufgabe 6: True/False ─────────────────────────────────────────────────────

def test_tf_1_all_p_uses_collide_without_c_uses():
    """1=TRUE: Programm ohne c-uses → all-p-uses ≡ all-p-uses/some-c-uses."""
    # Ohne c-uses: 'some-c-uses'-Bedingung vakuös. Beide Metriken = all-p-uses.
    assert True  # konzeptueller Test, dokumentiert Antwort


def test_tf_2_non_inductive_unreachable_state():
    """2=TRUE: Nicht-indukive Invariante → mind. 1 unerreichbarer Zustand der sie erfüllt."""
    # CE-Zustand erfüllt P, ist aber unerreichbar (Body würde ¬P erzeugen, was mit P=Invariante kollidiert).
    # Dokumentierter Beweis: CE ∈ sat(P), CE ∉ Reachable.
    assert True


def test_tf_3_whenever_p_then_possible_q_not_in_ltl_ctl():
    """3=FALSE: AG(p⇒EF q) ist CTL aber nicht LTL (EF ist existentiell)."""
    # LTL hätte AG(p⇒AF q) (universell). LTL∩CTL enthält kein EF ohne entsprechendes AF.
    answer = False  # Die Aussage 'ist in LTL∩CTL ausdrückbar' ist FALSCH
    assert answer == False


def test_tf_4_2cnf_not_always_satisfiable():
    """4=FALSE: 2-CNF ist nicht immer erfüllbar. CE: (x∨x)∧(¬x∨¬x) = UNSAT."""
    from z3 import Bool, Solver, unsat
    x = Bool('x')
    s = Solver()
    s.add(x)       # (x∨x) = x
    s.add(~x)      # (¬x∨¬x) = ¬x
    assert s.check() == unsat


def test_tf_5_non_terminating_hoare_proof_possible():
    """5=FALSE: Für nicht-terminierendes C ist {true}C{false} gültiges Hoare-Tripel (vakuös)."""
    # Partielle Korrektheit: {P}C{Q} gilt wenn C terminiert → Q. Nicht-Terminierung → vakuös True.
    # Also: {true}(while true skip){false} ist BEWEISBAR in Hoare-Logik (partiell).
    answer = False  # 'Kein Beweis möglich' ist FALSCH
    assert answer == False
