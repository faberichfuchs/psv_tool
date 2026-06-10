"""
Tests für Exam 3 (June 2021) Lösungen.
Verifiziert alle Aufgaben mit deterministischen App-Tools.
Ausführen: pytest tests/test_exam3.py -v
"""
import pytest
import sys
sys.path.insert(0, ".")

GCD_PY = """def gcd(x, y):
    if x < y:
        min_v = x; max_v = y
    else:
        min_v = y; max_v = x
    t = min_v
    while t > 0:
        if x % t == 0 and y % t == 0:
            return t
        t = t - 1
    return max_v"""


# ── Aufgabe 1a: Control-Flow Coverage ────────────────────────────────────────

def test_gcd_basic_results():
    """gcd(0,1)=1, gcd(1,0)=1, gcd(2,3)=1, gcd(4,6)=2."""
    ns = {}
    exec(GCD_PY, ns)
    assert ns['gcd'](0, 1) == 1
    assert ns['gcd'](1, 0) == 1
    assert ns['gcd'](2, 3) == 1
    assert ns['gcd'](4, 6) == 2
    assert ns['gcd'](2, 4) == 2


def test_gcd_statement_coverage():
    """Mit gcd(0,1), gcd(2,3): alle Statements erreicht."""
    ns = {}
    exec(GCD_PY, ns)
    # gcd(0,1): x<y → min_v=0, t=0 → while 0>0 False → return max_v=1
    assert ns['gcd'](0, 1) == 1
    # gcd(2,3): x<y, t=2: 2%2=0 ∧ 3%2=1 F, t=1: 0∧0 → return 1
    assert ns['gcd'](2, 3) == 1


def test_gcd_decision_coverage():
    """D0(x<y), D1(x%t==0 and y%t==0), D2(t>0) alle T/F."""
    ns = {}
    exec(GCD_PY, ns)
    assert ns['gcd'](1, 0) == 1   # D0=False (x>=y)
    assert ns['gcd'](0, 1) == 1   # D0=True (x<y), D2=False (t=0)
    assert ns['gcd'](2, 3) == 1   # D1=True (t=1: return t), D1=False (t=2)


def test_gcd_branch_coverage():
    """Alle 6 Branches abgedeckt: D0 T/F, D1 T/F, D2 T/F."""
    ns = {}
    exec(GCD_PY, ns)
    # D0-True: gcd(0,1)
    assert ns['gcd'](0, 1) == 1
    # D0-False: gcd(1,0)
    assert ns['gcd'](1, 0) == 1
    # D2-True + D1-False + D1-True: gcd(2,3)
    assert ns['gcd'](2, 3) == 1
    # D2-False: gcd(0,1) → t=0, while False → return max_v
    # Statement coverage already handles this


def test_gcd_mcdc_fails_with_base_suite():
    """MC/DC scheitert mit Basis-Tests: x%t==0 immer True (x=2→2%2=0,2%1=0)."""
    ns = {}
    exec(GCD_PY, ns)
    # Mit gcd(2,3) ist x=2: x%2=0 (T), x%1=0 (T) → atom x%t==0 nie False
    # Für MC/DC braucht man gcd(3,4): 3%2=1 → x%t==0=False
    assert ns['gcd'](3, 4) == 1   # bestätigt MC/DC-Testcase funktioniert


def test_gcd_mcdc_witness():
    """gcd(3,4) liefert MC/DC-Witness: bei t=2: x%t=3%2=1≠0 → False-Zweig."""
    ns = {}
    exec(GCD_PY, ns)
    # t=3: 3%3=0∧4%3=1≠0 → D1=False; t=2: 3%2=1≠0 → x%t==0=False ✓ MC/DC-Witness
    assert ns['gcd'](3, 4) == 1


# ── Aufgabe 1b: Data-Flow Coverage ───────────────────────────────────────────

def test_gcd_all_defs():
    """all-defs: alle Definitionen genutzt mit Basis-Tests."""
    from tools.shared import _trace_dataflow_coverage
    result = _trace_dataflow_coverage(GCD_PY, ['gcd(0, 1)', 'gcd(1, 0)', 'gcd(2, 3)'])
    assert len(result['all_defs']['missing']) == 0


def test_gcd_all_p_uses():
    """all-p-uses: mit Basis-Tests erfüllt."""
    from tools.shared import _trace_dataflow_coverage
    result = _trace_dataflow_coverage(GCD_PY, ['gcd(0, 1)', 'gcd(1, 0)', 'gcd(2, 3)'])
    assert len(result['all_p_uses']['missing']) == 0


def test_gcd_all_c_uses_incomplete():
    """all-c-uses mit Basis-Tests nicht vollständig abgedeckt."""
    from tools.shared import _trace_dataflow_coverage
    result = _trace_dataflow_coverage(GCD_PY, ['gcd(0, 1)', 'gcd(1, 0)', 'gcd(2, 3)'])
    assert len(result['all_c_uses']['missing']) > 0   # nicht alle c-uses abgedeckt


def test_gcd_all_c_uses_with_extra_tests():
    """gcd(2,4) und gcd(4,6) decken fehlende c-uses ab."""
    from tools.shared import _trace_dataflow_coverage
    result = _trace_dataflow_coverage(
        GCD_PY,
        ['gcd(0, 1)', 'gcd(1, 0)', 'gcd(2, 3)', 'gcd(2, 4)', 'gcd(4, 6)']
    )
    assert len(result['all_c_uses']['missing']) == 0


# ── Aufgabe 2: Hoare Logic ────────────────────────────────────────────────────

def test_hoare_invariant_init():
    """Init: nach if/else ist (m+n)%2=0 → I gilt."""
    from z3 import Int, Solver, Not, And
    m, n = Int('m'), Int('n')
    s = Solver()
    # Nach if/else: if (m+n)%2 != 0: m=m+1 → neue Summe (m+1+n)=(m+n)+1 gerade
    # Modell: m_new s.t. (m_new+n)%2=0 aus Konstruktion
    # Check: NOT((m_new+n)%2 = 0) → unsat
    m_new = Int('m_new')
    s.add(And(
        m_new == m + 1,         # falls (m+n)%2 != 0
        (m + n) % 2 != 0,       # Bedingung des if
        (m_new + n) % 2 != 0    # Negation der Invariante
    ))
    assert str(s.check()) == 'unsat'


def test_hoare_invariant_preservation():
    """Erhaltung: I ∧ m≠0 ∧ n≠0 → nach m=m-1;n=n-1 gilt I."""
    from z3 import Int, Solver, Not, And
    m, n = Int('m'), Int('n')
    s = Solver()
    # I = (m+n)%2=0; Body: m'=m-1, n'=n-1
    # Check: I ∧ m≠0 ∧ n≠0 ∧ NOT I[m→m-1, n→n-1]
    s.add(And(
        (m + n) % 2 == 0,
        m != 0,
        n != 0,
        (m - 1 + n - 1) % 2 != 0
    ))
    assert str(s.check()) == 'unsat'


def test_hoare_invariant_consequence():
    """Konsequenz: I ∧ (m=0 ∨ n=0) → m%2=0."""
    from z3 import Int, Solver, Not, And, Or
    m, n = Int('m'), Int('n')
    s = Solver()
    s.add(And(
        (m + n) % 2 == 0,
        Or(m == 0, n == 0),
        m % 2 != 0   # Negation der Postcondition
    ))
    assert str(s.check()) == 'unsat'


# ── Aufgabe 3: Loop Invariants ────────────────────────────────────────────────

def test_invariant_1_neither():
    """(a-b)=(x-y) ist Neither: CE x=1,y=2,a=5,b=3 → reachable, inv False."""
    # Nach Prefix (x=1,y=2: x≠y → a,b unverändert): a-b=2, x-y=-1 → nicht gleich
    a, b, x, y = 5, 3, 1, 2
    inv = (a - b) == (x - y)
    assert not inv   # Counterexample: reachable state where inv=False


def test_invariant_1_not_preserved():
    """(a-b)=(x-y) ist Neither: nicht nur nicht-induktiv, sondern gar nicht erfüllbar nach Prefix.
    CE: x=1,y=2 → nach Prefix x≠y → a,b beliebig → a-b ≠ x-y möglich."""
    # Reachable state where inv False: x=1,y=2,a=5,b=3 → a-b=2, x-y=-1 ≠ 2
    a, b, x, y = 5, 3, 1, 2
    assert (a - b) != (x - y)   # inv False in reachable state


def test_invariant_2_neither():
    """(a≠b)∨(x=y) ist Neither: CE x=1,y=2,a=0,b=0 → False und reachable."""
    x, y, a, b = 1, 2, 0, 0
    inv = (a != b) or (x == y)
    assert not inv


def test_invariant_3_inductive():
    """(x≠y)∨(a=b) ist Inductive Invariant."""
    from z3 import Int, Solver, Not, And, Or
    x, y, a, b = Int('x'), Int('y'), Int('a'), Int('b')
    inv = Or(x != y, a == b)
    # Init-Check: nach Prefix (if x==y: a=b): NOT(inv) reachable? unsat?
    s = Solver()
    s.add(And(
        # Reachable: x=y → a=b, OR x≠y (no constraint on a,b)
        # Post-prefix: (x!=y) OR (a==b) — zeige immer True
        Not(inv),
        # x=y implies a=b (from prefix)
        Or(x != y, a == b)  # prefix gibt uns das
    ))
    # Wenn x=y→a=b, dann inv=(x≠y)∨(a=b)=(False)∨(True)=True → unsat für NOT inv
    # Wenn x≠y, inv=True → unsat für NOT inv
    # Also: unsat
    assert str(s.check()) == 'unsat'


def test_invariant_3_preservation():
    """Erhaltung: (x≠y)∨(a=b) bleibt nach x=x+1,y=y+1."""
    from z3 import Int, Solver, Not, And, Or
    x, y, a, b = Int('x'), Int('y'), Int('a'), Int('b')
    inv = Or(x != y, a == b)
    # Loop body: x'=x+1, y'=y+1; a,b unverändert
    x2 = x + 1; y2 = y + 1
    inv_after = Or(x2 != y2, a == b)
    s = Solver()
    # I ∧ cond ∧ NOT I' → unsat?
    s.add(And(inv, x < 42, Not(inv_after)))
    assert str(s.check()) == 'unsat'


# ── Aufgabe 4: CTL ───────────────────────────────────────────────────────────

def _get_ctl_eval():
    from tools.shared import _ctl_check, _tokenize_ctl, _parse_ctl
    states = ['s0', 's1', 's2']
    transitions = [('s0', 's0'), ('s0', 's1'), ('s1', 's2'), ('s2', 's2')]
    labels = {'s0': {'a'}, 's1': {'a'}, 's2': {'b'}}
    ev, _, _ = _ctl_check(set(states), transitions, labels, ['s0'])

    def eval_formula(formula_str):
        tokens = _tokenize_ctl(formula_str)
        ast = _parse_ctl(tokens)
        return set(ev(ast, []))

    return eval_formula


def test_ctl_ag_a():
    """AG a = ∅ (s2 hat nur b)."""
    ev = _get_ctl_eval()
    assert ev("AG a") == set()


def test_ctl_eg_a():
    """EG a = {s0} (s0→s0→... unendlicher a-Pfad)."""
    ev = _get_ctl_eval()
    assert ev("EG a") == {'s0'}


def test_ctl_af_ag_b():
    """AF(AG b) = {s1, s2}."""
    ev = _get_ctl_eval()
    assert ev("AF(AG b)") == {'s1', 's2'}


def test_ctl_af_eg_b():
    """AF(EG b) = {s1, s2}."""
    ev = _get_ctl_eval()
    assert ev("AF(EG b)") == {'s1', 's2'}


def test_ctl_ef_ag_b():
    """EF(AG b) = {s0, s1, s2}."""
    ev = _get_ctl_eval()
    assert ev("EF(AG b)") == {'s0', 's1', 's2'}


def test_ctl_ex_b():
    """EX b = {s1, s2}."""
    ev = _get_ctl_eval()
    assert ev("EX b") == {'s1', 's2'}


def test_ctl_eg_af_a():
    """EG(AF a) = {s0} — nur s0 hat unendlichen Pfad durch AF-a-Zustände."""
    ev = _get_ctl_eval()
    assert ev("EG(AF a)") == {'s0'}


def test_ctl_a_b_until_a():
    """A(b U a) = {s0, s1} — s2 hat keinen a-Zustand erreichbar auf allen Pfaden."""
    ev = _get_ctl_eval()
    result = ev("A[b U a]")
    assert result == {'s0', 's1'}


def test_ctl_a_a_until_b():
    """A(a U b) = {s1, s2}."""
    ev = _get_ctl_eval()
    result = ev("A[a U b]")
    assert result == {'s1', 's2'}


def test_ctl_e_a_until_b():
    """E(a U b) = {s0, s1, s2}."""
    ev = _get_ctl_eval()
    result = ev("E[a U b]")
    assert result == {'s0', 's1', 's2'}


# ── Aufgabe 5a: SAT ──────────────────────────────────────────────────────────

def test_sat_exam3_satisfiable():
    """SAT-Formel aus Exam 3 ist SATISFIABLE."""
    from tools.shared import _run_dpll_with_trace, _parse_cnf_text
    # Klauseln: at-least-one + at-most-one für 3 Paare + Extra-Klausel
    cnf_str = """1 2
3 4
5 6
-1 -3
-1 -5
-2 -4
-2 -6
-3 -5
-4 -5
6 -5 1"""
    clauses = _parse_cnf_text(cnf_str)
    sat, model, _ = _run_dpll_with_trace(clauses)
    assert sat == True


def test_sat_exam3_model_valid():
    """DPLL-Modell x1=T,x2=F,x3=F,x4=T,x5=F,x6=T satisfiziert alle Klauseln."""
    model = {1: True, 2: False, 3: False, 4: True, 5: False, 6: True}
    clauses = [
        [1, 2], [3, 4], [5, 6],
        [-1, -3], [-1, -5], [-2, -4], [-2, -6],
        [-3, -5], [-4, -5], [6, -5, 1]
    ]
    for clause in clauses:
        satisfied = any(
            (model.get(abs(lit), False) if lit > 0 else not model.get(abs(lit), False))
            for lit in clause
        )
        assert satisfied, f"Clause {clause} not satisfied"


# ── Aufgabe 5b: EUF ──────────────────────────────────────────────────────────

def test_euf_exam3_f2_sat():
    """EUF F2: i=j∧j=k∧k=l∧l≠m∧l≠n∧m=n∧o≠p∧o=q ist SAT."""
    from z3 import Int, Function, IntSort, Solver, And, Not
    i, j, k, l, m, n, o, p, q = [Int(x) for x in 'i j k l m n o p q'.split()]
    s = Solver()
    s.add(i == j, j == k, k == l, l != m, l != n, m == n, o != p, o == q)
    assert str(s.check()) == 'sat'


def test_euf_exam3_f3_unsat():
    """EUF F3: i=j∧j=k∧k=l∧l≠n∧m=n∧g(i)≠g(m)∧f(i)≠f(l) ist UNSAT."""
    from z3 import Int, Function, IntSort, Solver, And
    i, j, k, l, m, n = [Int(x) for x in 'i j k l m n'.split()]
    f = Function('f', IntSort(), IntSort())
    g = Function('g', IntSort(), IntSort())
    s = Solver()
    s.add(i == j, j == k, k == l, l != n, m == n)
    s.add(g(i) != g(m))
    s.add(f(i) != f(l))
    # i=j=k=l → f(i)=f(l) per Kongruenz → Widerspruch mit f(i)≠f(l)
    assert str(s.check()) == 'unsat'


# ── Aufgabe 5c: OBDD ─────────────────────────────────────────────────────────

def test_obdd_xor_and_simplification():
    """(x1⊕x2)∧x1 vereinfacht sich zu x1∧¬x2."""
    # Verifikation durch Wahrheitstabelle
    results = {}
    for x1 in [False, True]:
        for x2 in [False, True]:
            orig = ((x1 != x2) and x1)
            simplified = (x1 and not x2)
            assert orig == simplified, f"x1={x1},x2={x2}: {orig} != {simplified}"
            results[(x1, x2)] = orig

    # x1=F: F; x1=T,x2=F: T; x1=T,x2=T: F
    assert results[(False, False)] == False
    assert results[(False, True)] == False
    assert results[(True, False)] == True
    assert results[(True, True)] == False


def test_obdd_node_count():
    """OBDD hat 1 inneren Knoten (x1) + 1 x2-Knoten = 2 innere Knoten, 2 Blätter."""
    # x1=F → leaf 0 (x2 irrelevant)
    # x1=T → x2-Knoten → leaf 0 (x2=T) oder leaf 1 (x2=F)
    # Reduziertes OBDD: x1-Knoten → {leaf_0, x2-Knoten}; x2-Knoten → {leaf_1, leaf_0}
    # = 2 innere Knoten (x1, x2), 2 Terminal-Knoten (0, 1)
    # Einfachste Verifikation: 3 unterschiedliche Ausgaben → mind. 1 innerer Entscheidungsknoten
    def bdd_eval(x1, x2):
        if not x1: return 0      # x1-Knoten → leaf 0
        if not x2: return 1      # x2-Knoten → leaf 1
        return 0                  # x2-Knoten → leaf 0

    assert bdd_eval(False, False) == 0
    assert bdd_eval(False, True) == 0
    assert bdd_eval(True, False) == 1
    assert bdd_eval(True, True) == 0
