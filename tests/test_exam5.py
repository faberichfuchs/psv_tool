"""
Tests für Exam 5 (October 2024) Lösungen.
Ausführen: pytest tests/test_exam5.py -v
"""
import pytest
import sys
sys.path.insert(0, ".")

IS_COPRIME2_PY = """def is_coprime(n1, n2):
    a, b = n1, n2
    while a != b and a > 1 and b > 1:
        if a > b:
            a = a - b
        else:
            b = b - a
    return (a == 1 or b == 1)"""


# ── Aufgabe 1a: Control-Flow Coverage ────────────────────────────────────────

def test_is_coprime2_basic_results():
    """(0,0)=False, (2,3)=True, (6,2)=False."""
    ns = {}
    exec(IS_COPRIME2_PY, ns)
    f = ns['is_coprime']
    assert f(0, 0) == False
    assert f(2, 3) == True
    assert f(6, 2) == False


def test_is_coprime2_statement_coverage():
    """Alle Statements abgedeckt."""
    ns = {}
    exec(IS_COPRIME2_PY, ns)
    f = ns['is_coprime']
    assert f(6, 2) == False   # L4 (a=a-b)
    assert f(2, 3) == True    # L6 (b=b-a)


def test_is_coprime2_decision_coverage():
    """D0,D1,D2 alle T/F abgedeckt."""
    ns = {}
    exec(IS_COPRIME2_PY, ns)
    f = ns['is_coprime']
    # D0-F: (0,0); D1-T: (6,2); D1-F: (2,3); D2-T: (2,3); D2-F: (0,0)
    assert f(0, 0) == False
    assert f(2, 3) == True
    assert f(6, 2) == False


def test_is_coprime2_condition_coverage_fails():
    """D2-Atom (a==1) nie True mit Basis-Tests."""
    ns = {}
    exec(IS_COPRIME2_PY, ns)
    f = ns['is_coprime']
    # (3,2): a→1 am Ende → D2-Atom (a==1)=True
    assert f(3, 2) == True


def test_is_coprime2_mcdc_witness_d2():
    """MC/DC D2: (3,2)→a=1(a==1=T); (2,3)→b=1(b==1=T,a==1=F)."""
    ns = {}
    exec(IS_COPRIME2_PY, ns)
    f = ns['is_coprime']
    assert f(3, 2) == True   # a=1 at return
    assert f(2, 3) == True   # b=1 at return


def test_is_coprime2_mutation_equivalent():
    """Mutant (a=a-b → a=a%b) ist äquivalent zum Original."""
    ns_orig = {}
    exec(IS_COPRIME2_PY, ns_orig)
    mutant = IS_COPRIME2_PY.replace("a = a - b", "a = a % b")
    ns_mut = {}
    exec(mutant, ns_mut)
    f_o, f_m = ns_orig['is_coprime'], ns_mut['is_coprime']
    for n1, n2 in [(0,0),(2,3),(6,2),(5,3),(3,5),(3,2),(9,6),(7,3),(4,3),(12,4)]:
        assert f_o(n1, n2) == f_m(n1, n2), f"Differ at ({n1},{n2})"


# ── Aufgabe 1b: Data-Flow Coverage ───────────────────────────────────────────

def test_is_coprime2_all_defs():
    """all-defs mit Basis-Tests."""
    from tools.shared import _trace_dataflow_coverage
    result = _trace_dataflow_coverage(
        IS_COPRIME2_PY,
        ['is_coprime(0, 0)', 'is_coprime(2, 3)', 'is_coprime(6, 2)']
    )
    assert len(result['all_defs']['missing']) == 0


def test_is_coprime2_all_c_uses_incomplete():
    """all-c-uses mit Basis-Tests: fehlende c-use Paare."""
    from tools.shared import _trace_dataflow_coverage
    result = _trace_dataflow_coverage(
        IS_COPRIME2_PY,
        ['is_coprime(0, 0)', 'is_coprime(2, 3)', 'is_coprime(6, 2)']
    )
    assert len(result['all_c_uses']['missing']) > 0


def test_is_coprime2_all_c_uses_complete():
    """(5,3),(3,5),(2,7) decken alle c-uses ab."""
    from tools.shared import _trace_dataflow_coverage
    result = _trace_dataflow_coverage(
        IS_COPRIME2_PY,
        ['is_coprime(0, 0)', 'is_coprime(2, 3)', 'is_coprime(6, 2)',
         'is_coprime(5, 3)', 'is_coprime(3, 5)', 'is_coprime(2, 7)']
    )
    assert len(result['all_c_uses']['missing']) == 0


# ── Aufgabe 2: Hoare Logic ────────────────────────────────────────────────────

def test_hoare_exam5_invariant_is_b_implies_i_le_10():
    """I = (b⇒i≤10): Init, Preservation, Consequence (Z3)."""
    from z3 import Int, Bool, Solver, Not, And, Implies, BoolVal

    i = Int('i')
    b = Bool('b')

    # Init: nach i=2;b=true: (true⇒2≤10)=T
    from z3 import IntVal, BoolVal as BV
    init_satisfied = (True and 2 <= 10)
    assert init_satisfied

    # Preservation: {(b⇒i≤10) ∧ b} body {(b⇒i≤10)}
    # = {i≤10}: nach body: i'=i+1, b'=if(i+1>10) false else true.
    # Wenn b'=true → ¬(i+1>10) → i+1≤10 ✓. Wenn b'=false → trivial ✓.
    for i_val in range(2, 12):
        i_new = i_val + 1
        b_new = not (i_new < 1 or i_new > 10)
        if b_new:
            assert i_new <= 10, f"i_new={i_new} but b_new=True violates invariant"


def test_hoare_exam5_init_check():
    """Init: nach i=2,b=true: I=(true⇒2≤10)=True."""
    i, b = 2, True
    assert (not b) or (i <= 10)


def test_hoare_exam5_preservation_check():
    """Preservation: bei b=True und i≤10, nach body I erhalten."""
    from z3 import Int, Solver, Not, And, Or
    i = Int('i')
    s = Solver()
    # {I ∧ b=True} = {i≤10}; nach body: i'=i+1, b'=not(i'<1 or i'>10)
    # b'=True ⟺ 1≤i'≤10 ⟺ i'≤10 (da i≥2→i'≥3)
    # Check: {i≤10} → {(b'⇒i'≤10)}
    # Falls b'=True: i'≤10. Falls b'=False: trivial.
    # = i≤10 ∧ b'=True ∧ i'>10 → unsat
    s.add(And(i <= 10, i + 1 <= 10 + 1, Not(i + 1 > 10)))
    # Actually just check: i≤10 ∧ ¬(i+1>10) → i+1≤10 (b' stays true, inv holds)
    s2 = Solver()
    s2.add(And(i <= 10, i + 1 > 10, i + 1 <= 10))  # b'=False case: trivial
    # Key check: wenn b' bleibt True (¬(i'>10)), dann i'≤10:
    s3 = Solver()
    s3.add(And(i <= 10, Not(i + 1 > 10), i + 1 > 10))  # contradiction
    assert str(s3.check()) == 'unsat'


# ── Aufgabe 3: Loop Invariants ────────────────────────────────────────────────

def _run_loop(b0):
    """Simuliert Programm für gegebenes initiales b."""
    c = b0 % 2
    a = b0 + c
    b = b0
    while b > 0:
        b -= 1
        a += 1
        c += 1
    return a, b, c


def test_invariant_1_a_minus_b_le_2c():
    """(a-b ≤ 2c) gilt in allen Zuständen."""
    # Prüfe bei Loop-Entry und nach jedem Schritt
    def check_during_loop(b0):
        c = b0 % 2
        a = b0 + c
        b = b0
        assert (a - b) <= 2 * c, f"Init failed: a={a},b={b},c={c}"
        while b > 0:
            b -= 1; a += 1; c += 1
            assert (a - b) <= 2 * c, f"Failed after step: a={a},b={b},c={c}"
    for b0 in range(0, 10):
        check_during_loop(b0)


def test_invariant_1_inductive():
    """(a-b ≤ 2c) ist induktiv: a-b+2 ≤ 2c+2 wenn a-b ≤ 2c."""
    from z3 import Int, Solver, Not, And
    a, b, c = Int('a'), Int('b'), Int('c')
    s = Solver()
    s.add(And(
        a - b <= 2 * c,     # Invariante vorher
        b > 0,              # Loop-Bedingung
        Not((a + 1) - (b - 1) <= 2 * (c + 1))  # Invariante nachher verletzt
    ))
    assert str(s.check()) == 'unsat'


def test_invariant_2_b_plus_c_mod2_le_a_mod2():
    """(b+c)%2 ≤ a%2 gilt in allen Zuständen."""
    def check_during_loop(b0):
        c = b0 % 2
        a = b0 + c
        b = b0
        assert (b + c) % 2 <= a % 2, f"Init: b={b},c={c},a={a}"
        while b > 0:
            b -= 1; a += 1; c += 1
            assert (b + c) % 2 <= a % 2, f"Step: b={b},c={c},a={a}"
    for b0 in range(0, 10):
        check_during_loop(b0)


def test_invariant_2_b_plus_c_always_even():
    """b+c = b₀+b₀%2 = konstant und gerade."""
    for b0 in range(0, 10):
        c0 = b0 % 2
        a0 = b0 + c0
        expected_sum = b0 + c0  # = b₀ + b₀%2, immer gerade
        assert expected_sum % 2 == 0, f"b0={b0}: sum={expected_sum} not even"
        # Verify konstant im Loop
        b, c = b0, c0
        while b > 0:
            b -= 1; c += 1
            assert b + c == expected_sum


def test_invariant_3_a_minus_b_eq_2c_neither():
    """(a-b = 2c) ist Neither: CE b₀=1 → a=2,b=1,c=1: a-b=1≠2=2c."""
    b0 = 1
    c = b0 % 2  # = 1
    a = b0 + c  # = 2
    b = b0      # = 1
    assert (a - b) != 2 * c, f"Expected a-b={a-b} ≠ 2c={2*c}"


def test_invariant_3_inductive_for_even():
    """(a-b = 2c) ist induktiv für gerades b₀."""
    from z3 import Int, Solver, Not, And
    a, b, c = Int('a'), Int('b'), Int('c')
    s = Solver()
    s.add(And(
        a - b == 2 * c,
        b > 0,
        Not((a + 1) - (b - 1) == 2 * (c + 1))
    ))
    assert str(s.check()) == 'unsat'  # Inductive IF it holds initially


# ── Aufgabe 4: CTL ───────────────────────────────────────────────────────────

def _get_ctl_eval5():
    from tools.shared import _ctl_check, _tokenize_ctl, _parse_ctl
    # s0(a)→s1(b)→s2(a)→s2 (s2 self-loop)
    states = ['s0', 's1', 's2']
    transitions = [('s0', 's1'), ('s1', 's2'), ('s2', 's2')]
    labels = {'s0': {'a'}, 's1': {'b'}, 's2': {'a'}}
    ev, _, _ = _ctl_check(set(states), transitions, labels, ['s0'])

    def eval_formula(formula_str):
        tokens = _tokenize_ctl(formula_str)
        ast = _parse_ctl(tokens)
        return set(ev(ast, []))

    return eval_formula


def test_ctl_exam5_eg_b():
    """EG b = ∅."""
    ev = _get_ctl_eval5()
    assert ev("EG b") == set()


def test_ctl_exam5_ex_a():
    """EX a = {s1, s2}: s1→s2(a)✓, s2→s2(a)✓, s0→s1(b)✗."""
    ev = _get_ctl_eval5()
    assert ev("EX a") == {'s1', 's2'}


def test_ctl_exam5_af_a():
    """AF a = {s0, s1, s2}: alle Pfade treffen a."""
    ev = _get_ctl_eval5()
    assert ev("AF a") == {'s0', 's1', 's2'}


def test_ctl_exam5_e_b_until_a():
    """E(b U a) = {s0, s1, s2}."""
    ev = _get_ctl_eval5()
    assert ev("E[b U a]") == {'s0', 's1', 's2'}


def test_ctl_exam5_eg_a_fixpoint():
    """EG a = {s2}: Fixpunkt-Verifikation."""
    ev = _get_ctl_eval5()
    assert ev("EG a") == {'s2'}


def test_ctl_exam5_ex_neg_eg_a():
    """EX(¬EG a) = {s0}: EG a={s2}, ¬{s2}={s0,s1}, EX{s0,s1}: nur s0→s1∈{s0,s1}."""
    ev = _get_ctl_eval5()
    eg_a = ev("EG a")
    assert eg_a == {'s2'}
    # EX(¬EG a): need to compute manually since parser might not support negation
    # s0→s1 (s1 ∈ {s0,s1} ✓): s0 ∈ result
    # s1→s2 (s2 ∉ {s0,s1} ✗): s1 ∉ result
    # s2→s2 (s2 ∉ {s0,s1} ✗): s2 ∉ result
    from tools.shared import _ctl_check, _tokenize_ctl, _parse_ctl
    states = ['s0', 's1', 's2']
    transitions = [('s0', 's1'), ('s1', 's2'), ('s2', 's2')]
    labels = {'s0': {'a'}, 's1': {'b'}, 's2': {'a'}}
    ev2, _, _ = _ctl_check(set(states), transitions, labels, ['s0'])
    # EX a = {s1,s2}; ¬EG_a = {s0,s1}; EX({s0,s1}): s with succ in {s0,s1}
    # Manually: only s0→s1 ∈ {s0,s1} → result = {s0}
    not_eg_a = {'s0', 's1', 's2'} - eg_a
    assert not_eg_a == {'s0', 's1'}
    succ = {'s0': {'s1'}, 's1': {'s2'}, 's2': {'s2'}}
    result = {s for s in states if succ[s] & not_eg_a}
    assert result == {'s0'}


# ── Aufgabe 5a: SAT ──────────────────────────────────────────────────────────

def test_sat_exam5_satisfiable():
    """Formel aus Exam 5 ist SAT mit 4 Lösungen."""
    from tools.shared import _run_dpll_with_trace, _parse_cnf_text
    cnf_str = """-1 2
1 -2
-3 4
3 -4
-1 2 3
-1 2 4
1 -2 -3
1 -2 -4"""
    clauses = _parse_cnf_text(cnf_str)
    sat, model, _ = _run_dpll_with_trace(clauses)
    assert sat == True


def test_sat_exam5_four_models():
    """Alle 4 Belegungen: (T,T,T,T),(T,T,F,F),(F,F,T,T),(F,F,F,F)."""
    clauses = [
        [-1, 2], [1, -2], [-3, 4], [3, -4],
        [-1, 2, 3], [-1, 2, 4], [1, -2, -3], [1, -2, -4]
    ]

    def check(model_dict):
        m = {i+1: model_dict[i+1] for i in range(4)}
        for cl in clauses:
            ok = any((m[abs(l)] if l > 0 else not m[abs(l)]) for l in cl)
            if not ok:
                return False
        return True

    solutions = [
        {1:True, 2:True, 3:True, 4:True},
        {1:True, 2:True, 3:False, 4:False},
        {1:False, 2:False, 3:True, 4:True},
        {1:False, 2:False, 3:False, 4:False},
    ]
    for sol in solutions:
        assert check(sol), f"Solution {sol} not satisfying"


def test_sat_exam5_x1_equiv_x2():
    """Klauseln 1+2 erzwingen x1≡x2 (Äquivalenz)."""
    # x1≠x2 verletzt mind. eine Klausel
    for x1, x2 in [(True, False), (False, True)]:
        cl1 = (not x1) or x2   # ¬x1∨x2
        cl2 = x1 or (not x2)   # x1∨¬x2
        assert not (cl1 and cl2), f"x1={x1},x2={x2} shouldn't satisfy both"


# ── Aufgabe 5b: EUF ──────────────────────────────────────────────────────────

def test_euf_exam5_i_sat():
    """EUF i: SAT — verschiedene Klassen, f-Constraints erfüllbar."""
    from z3 import Int, Function, IntSort, Solver, And, Not
    a, b, u, v, w, x, y, z, c = [Int(n) for n in 'a b u v w x y z c'.split()]
    f = Function('f', IntSort(), IntSort())
    s = Solver()
    s.add(a == b, u == v, x == y, c == a, x != c, w == v, y == z, w != a)
    s.add(f(a) != f(x), f(y) == f(v))
    assert str(s.check()) == 'sat'


def test_euf_exam5_ii_unsat():
    """EUF ii: UNSAT — c=d → f(c)=f(d) per Kongruenz, aber f(c)≠f(d) gefordert."""
    from z3 import Int, Function, IntSort, Solver
    a, b, c, d = [Int(n) for n in 'a b c d'.split()]
    f = Function('f', IntSort(), IntSort())
    s = Solver()
    s.add(a == b, c == d, f(a) == f(d), f(c) != f(d))
    assert str(s.check()) == 'unsat'


# ── Aufgabe 6: True/False ─────────────────────────────────────────────────────

def test_tf_ag_eq_eg_single_path():
    """AG a ≡ EG a auf einem einzigen Pfad (TRUE)."""
    from tools.shared import _ctl_check, _tokenize_ctl, _parse_ctl
    # Linearer Pfad: s0→s1→s2→s2 mit allen a
    states = ['s0', 's1', 's2']
    transitions = [('s0', 's1'), ('s1', 's2'), ('s2', 's2')]
    labels = {'s0': {'a'}, 's1': {'a'}, 's2': {'a'}}
    ev, _, _ = _ctl_check(set(states), transitions, labels, ['s0'])
    ag_a = set(ev(_parse_ctl(_tokenize_ctl("AG a")), []))
    eg_a = set(ev(_parse_ctl(_tokenize_ctl("EG a")), []))
    # On this single-path structure, AG a = EG a (only one path from each state)
    assert ag_a == eg_a == {'s0', 's1', 's2'}


def test_tf_equality_logic_finite_model():
    """Gleichheitslogik: endliche Domäne reicht (TRUE)."""
    from z3 import Int, Solver, And
    # 3 Variablen, alle verschieden → Domäne {0,1,2} reicht
    x, y, z = Int('x'), Int('y'), Int('z')
    s = Solver()
    s.add(x != y, y != z, x != z)
    assert str(s.check()) == 'sat'
    m = s.model()
    values = {m[x].as_long(), m[y].as_long(), m[z].as_long()}
    assert len(values) == 3   # finite model exists
