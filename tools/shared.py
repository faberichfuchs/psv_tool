"""
Shared helper functions used by multiple tabs.
"""

import ast
import copy
import sys
import textwrap
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────
MATERIAL_DIR = Path(r"C:\Users\Fabio Fuchs\Documents\TU_Wien\SS26\ProgSysVer\material\184.741-2026S_2026066_2327")
CHROMA_DIR   = Path(r"C:\Users\Fabio Fuchs\Documents\TU_Wien\SS26\ProgSysVer\chroma_db")
COLLECTION   = "psv"


# ── C → Python transpiler (used by coverage tab) ──────────────────────────

def _c_to_python(c_code: str):
    """
    Transpile a simple C/C++ function to runnable Python.
    Handles: type declarations, while/if/else/for, return, skip,
             ||/&&/!, pre/post ++/--, block comments, line comments.
    Auto-corrects: missing semicolons, bare declarations without init,
                   for-loops (converted to while), common typos.
    Returns (python_code: str, warnings: list[str])
    """
    import re

    warnings_out = []
    code = c_code

    # ── 0. Normalize braceless if/else/while bodies ───────────────────────
    # Converts:   if (cond)\n    stmt;
    # To:         if (cond) {\n    stmt;\n}
    # Handles single-line too: if (cond) stmt;  →  if (cond) {\n    stmt;\n}
    def _add_braces(src):
        """Add braces to braceless if/else/while bodies."""
        lines = src.splitlines()
        out = []
        i = 0
        CONTROL = re.compile(r'^(\s*)(if|else\s+if|while|else|for)\b.*\)\s*$')
        INLINE   = re.compile(r'^(\s*)(if|else\s+if|while|for)\s*\(.*\)\s*(\S.*)$')
        ELSE_INLINE = re.compile(r'^(\s*)(else)\s+(\S.*)$')
        while i < len(lines):
            raw = lines[i]
            stripped = raw.strip()

            # already has { at end → pass through
            if stripped.endswith('{'):
                out.append(raw)
                i += 1
                continue

            # inline: if/while/for (cond) stmt  on same line
            m = INLINE.match(raw)
            if m and not stripped.startswith('//'):
                indent_str = m.group(1)
                keyword_part = raw[:raw.rfind(m.group(3))].rstrip()
                body = m.group(3)
                # Handle: if(cond) { stmt; }  →  unwrap inner braces
                brace_inner = re.match(r'^\{\s*(.*?)\s*\}\s*$', body)
                if brace_inner:
                    body = brace_inner.group(1)
                out.append(f"{keyword_part} {{")
                out.append(f"{indent_str}    {body}")
                out.append(f"{indent_str}}}")
                i += 1
                continue

            # inline: else stmt
            m2 = ELSE_INLINE.match(raw)
            if m2 and not stripped.startswith('//') and not stripped.startswith('else if'):
                indent_str = m2.group(1)
                body = m2.group(3)
                out.append(f"{indent_str}else {{")
                out.append(f"{indent_str}    {body}")
                out.append(f"{indent_str}}}")
                i += 1
                continue

            # if/while/else on its own line → next non-empty line is body
            m3 = CONTROL.match(raw)
            if m3 and not stripped.startswith('//'):
                i += 1
                # skip blank lines
                while i < len(lines) and not lines[i].strip():
                    i += 1
                if i < len(lines):
                    next_stripped = lines[i].strip()
                    if not next_stripped.startswith('{') and not next_stripped.startswith('//'):
                        # Put { at end of control line (same line)
                        out.append(raw.rstrip() + " {")
                        out.append(lines[i])
                        indent_str = m3.group(1)
                        out.append(f"{indent_str}}}")
                        i += 1
                        continue
                    else:
                        out.append(raw)
                else:
                    out.append(raw)
                continue

            out.append(raw)
            i += 1
        return "\n".join(out)

    code = _add_braces(code)

    # ── 1. Comments ───────────────────────────────────────────────────────
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'//(.*)$', r'  #\1', code, flags=re.MULTILINE)

    # ── 2. Literals & operators ───────────────────────────────────────────
    code = re.sub(r'\btrue\b',  'True',  code)
    code = re.sub(r'\bfalse\b', 'False', code)
    code = re.sub(r'\bNULL\b',  'None',  code)
    code = re.sub(r'\|\|', ' or ',  code)
    code = re.sub(r'&&',   ' and ', code)
    # NOT: ! not followed by = (keep !=)
    code = re.sub(r'!(?!=)', 'not ', code)
    # ++ / -- (post then pre to avoid double-replacement)
    code = re.sub(r'(\w+)\s*\+\+', r'\1 += 1', code)
    code = re.sub(r'(\w+)\s*--',   r'\1 -= 1', code)
    code = re.sub(r'\+\+\s*(\w+)', r'\1 += 1', code)
    code = re.sub(r'--\s*(\w+)',   r'\1 -= 1', code)

    # ── 3. Line-by-line structural conversion ─────────────────────────────
    C_TYPES = re.compile(
        r'\b(unsigned|signed|int|long|short|char|float|double|void|bool'
        r'|uint8_t|uint16_t|uint32_t|uint64_t|int8_t|int16_t|int32_t|int64_t'
        r'|size_t|const|static|inline|auto|register|struct|enum)\b\s*'
    )

    raw_lines = code.splitlines()
    out = []
    indent = 0
    IND = "    "

    for raw in raw_lines:
        line = raw.strip()
        if not line:
            continue

        opens = line.endswith('{')
        if opens:
            line = line[:-1].rstrip()

        while line.startswith('}'):
            indent = max(0, indent - 1)
            line = line[1:].strip()
            if line.startswith('else'):
                break

        if not line:
            continue

        if line.endswith(';'):
            line = line[:-1].rstrip()

        while line.endswith('}'):
            line = line[:-1].rstrip()
            indent = max(0, indent - 1)

        if not line:
            continue

        stripped = C_TYPES.sub('', line).strip()
        stripped = re.sub(r'^\*+', '', stripped).strip()

        # ── Function signature ───────────────────────────────────────────
        func_m = re.match(r'^([\w\s\*]+?)\s+(\w+)\s*\((.*?)\)\s*$', line)
        if (func_m
                and not re.search(r'\b(if|while|for|return|else)\b', line)
                and C_TYPES.search(func_m.group(1))):
            func_name = func_m.group(2)
            params_raw = func_m.group(3)
            params = []
            for p in params_raw.split(','):
                p = C_TYPES.sub('', p).strip()
                p = re.sub(r'\*', '', p).strip()
                if p:
                    params.append(p)
            out.append(f"{IND * indent}def {func_name}({', '.join(params)}):")
            if opens:
                indent += 1
            continue

        # ── else if ──────────────────────────────────────────────────────
        elif_m = re.match(r'else\s+if\s*\((.*?)\)\s*$', stripped)
        if elif_m:
            out.append(f"{IND * indent}elif {elif_m.group(1).strip()}:")
            if opens:
                indent += 1
            continue

        # ── else ─────────────────────────────────────────────────────────
        if re.match(r'^else\s*$', stripped):
            out.append(f"{IND * indent}else:")
            if opens:
                indent += 1
            continue

        # ── if (cond) — block follows on next line ───────────────────────
        if_m = re.match(r'^if\s*\((.*?)\)\s*$', stripped)
        if if_m:
            out.append(f"{IND * indent}if {if_m.group(1).strip()}:")
            if opens:
                indent += 1
            continue

        # ── while ────────────────────────────────────────────────────────
        while_m = re.match(r'^while\s*\((.*?)\)\s*$', stripped)
        if while_m:
            out.append(f"{IND * indent}while {while_m.group(1).strip()}:")
            if opens:
                indent += 1
            continue

        # ── for (convert to while) ────────────────────────────────────────
        for_m = re.match(r'^for\s*\((.*?);\s*(.*?);\s*(.*?)\)\s*$', stripped)
        if for_m:
            init = C_TYPES.sub('', for_m.group(1)).strip()
            cond = for_m.group(2).strip()
            step = for_m.group(3).strip()
            if init:
                out.append(f"{IND * indent}{init}")
            out.append(f"{IND * indent}while {cond}:")
            if opens:
                indent += 1
            warnings_out.append(
                f"ℹ for-Schleife: Update `{step}` wurde ans Ende des Loop-Body gesetzt (bitte prüfen)"
            )
            continue

        # ── return ───────────────────────────────────────────────────────
        if stripped.startswith('return'):
            out.append(f"{IND * indent}{stripped}")
            continue

        # ── skip / ; (empty statement) ───────────────────────────────────
        if stripped in ('skip', ';', ''):
            out.append(f"{IND * indent}pass")
            continue

        # ── Bare declaration without initializer ─────────────────────────
        bare_decl = re.match(r'^[a-zA-Z_]\w*$', stripped)
        if bare_decl and C_TYPES.search(line):
            out.append(f"{IND * indent}{stripped} = 0  # uninitialized C declaration")
            continue

        # ── Multi-var C declaration: `a = n1, b = n2` → split into two lines ──
        # After type-stripping, `unsigned a = n1, b = n2;` becomes `a = n1, b = n2`.
        # Python parses that as chained assignment (n1,b = n2) → unpack error.
        multi_decl = re.findall(r'(\w+\s*=\s*[^,=]+?)(?=,\s*\w+\s*=|$)', stripped)
        if (len(multi_decl) > 1
                and all(re.match(r'^\w+\s*=\s*.+$', p.strip()) for p in multi_decl)
                and C_TYPES.search(line)):
            for part in multi_decl:
                out.append(f"{IND * indent}{part.strip()}")
            continue

        # ── Regular statement ────────────────────────────────────────────
        if stripped:
            out.append(f"{IND * indent}{stripped}")

    python_code = '\n'.join(out)

    # ── 4. Auto-fix common typos ─────────────────────────────────────────
    python_code = re.sub(r'\bretun\b',  'return', python_code)
    python_code = re.sub(r'\bretrn\b',  'return', python_code)
    python_code = re.sub(r'\breturn\b', 'return', python_code)
    python_code = re.sub(r'\bwhlie\b',  'while',  python_code)
    python_code = re.sub(r'\bwhiel\b',  'while',  python_code)

    return python_code, warnings_out


# ── Coverage / dataflow helpers ────────────────────────────────────────────

def _build_instrumented_code_for_decisions(source_code: str):
    """Return instrumented code + decision metadata for dynamic decision/MC-DC logging."""
    tree = ast.parse(source_code)
    decision_meta = {}
    decision_id = 0

    def _src(node):
        seg = ast.get_source_segment(source_code, node)
        if seg:
            return seg.strip()
        try:
            return ast.unparse(node)
        except Exception:
            return "<expr>"

    class AtomWrapper(ast.NodeTransformer):
        def __init__(self, did):
            self.did = did
            self.atom_id = 0
            self.atom_texts = []

        def _mark_atom(self, node):
            aid = self.atom_id
            self.atom_id += 1
            self.atom_texts.append(_src(node))
            wrapped = ast.Call(
                func=ast.Name(id="__psv_atom", ctx=ast.Load()),
                args=[ast.Constant(self.did), ast.Constant(aid), node],
                keywords=[],
            )
            return ast.copy_location(wrapped, node)

        def visit_BoolOp(self, node):
            instrumented_values = [self.visit(v) for v in node.values]
            op_name = "or" if isinstance(node.op, ast.Or) else "and"
            return ast.copy_location(
                ast.Call(
                    func=ast.Name(id="__psv_bool_op", ctx=ast.Load()),
                    args=[ast.Constant(self.did), ast.Constant(op_name)] + instrumented_values,
                    keywords=[],
                ),
                node,
            )

        def visit_UnaryOp(self, node):
            if isinstance(node.op, ast.Not):
                node.operand = self.visit(node.operand)
                return node
            return self._mark_atom(node)

        def generic_visit(self, node):
            if isinstance(node, ast.BoolOp):
                return self.visit_BoolOp(node)
            if isinstance(node, ast.UnaryOp):
                return self.visit_UnaryOp(node)
            return self._mark_atom(node)

    class DecisionInstrumenter(ast.NodeTransformer):
        def visit_If(self, node):
            return self._instrument_branch_node(node)

        def visit_While(self, node):
            return self._instrument_branch_node(node)

        def _instrument_branch_node(self, node):
            nonlocal decision_id
            self.generic_visit(node)
            did = decision_id
            decision_id += 1
            original_expr = _src(node.test)

            wrapper = AtomWrapper(did)
            instrumented_test = wrapper.visit(node.test)
            node.test = ast.copy_location(
                ast.Call(
                    func=ast.Name(id="__psv_decision", ctx=ast.Load()),
                    args=[ast.Constant(did), instrumented_test],
                    keywords=[],
                ),
                node.test,
            )

            decision_meta[did] = {
                "lineno": getattr(node, "lineno", -1),
                "expr": original_expr,
                "atoms": wrapper.atom_texts,
            }
            return node

    instrumented = DecisionInstrumenter().visit(tree)
    ast.fix_missing_locations(instrumented)
    instrumented_code = ast.unparse(instrumented)
    return instrumented_code, decision_meta


def _mcdc_result_for_decision(evals, atom_count):
    """Check MC/DC witnesses per atom from recorded evaluations."""
    rows = []
    for e in evals:
        rows.append({"atoms": [e.get(i, None) for i in range(atom_count)], "result": e.get("__result__", None)})

    witnesses = {}
    for i in range(atom_count):
        witnesses[i] = None
        for a in range(len(rows)):
            for b in range(a + 1, len(rows)):
                ra, rb = rows[a], rows[b]
                ai, bi = ra["atoms"][i], rb["atoms"][i]
                if ai is None or bi is None:
                    continue
                if ai == bi or ra["result"] == rb["result"]:
                    continue

                independent = True
                for j in range(atom_count):
                    if j == i:
                        continue
                    aj, bj = ra["atoms"][j], rb["atoms"][j]
                    if aj is None or bj is None or aj != bj:
                        independent = False
                        break

                if independent:
                    witnesses[i] = (ra, rb)
                    break
            if witnesses[i] is not None:
                break

    all_ok = all(witnesses[i] is not None for i in range(atom_count)) if atom_count > 0 else True
    return all_ok, witnesses


def _run_tests_for_code(source_code: str, test_cases, timeout_secs: float = 2.0):
    """Execute code and evaluate test expressions in a fresh namespace.
    Läuft zuerst direkt (kein Thread-Overhead). Nur bei Timeout wird der Thread-Pool benötigt."""
    import threading
    namespace = {}
    try:
        exec(compile(source_code, "<mutation_target>", "exec"), namespace)
    except Exception as exc:
        return [(False, f"CompileError: {exc}") for _ in test_cases]

    tests = list(test_cases)
    results = []
    _timed_out = threading.Event()

    def _run_all():
        for tc in tests:
            if _timed_out.is_set():
                results.append((False, "TimeoutError: aborted"))
                continue
            try:
                results.append((True, eval(tc, namespace.copy())))
            except Exception as e:
                results.append((False, f"{type(e).__name__}: {e}"))

    t = threading.Thread(target=_run_all, daemon=True)
    t.start()
    t.join(timeout=timeout_secs)
    if t.is_alive():
        _timed_out.set()
        # Thread läuft daemon=True im Hintergrund — blockiert nicht weiter
        return [(False, "TimeoutError: mutant loops forever")] * len(tests)
    return results


def _generate_mutants(source_code: str, max_mutants: int = 80):
    """Generate first-order deterministic mutants for simple Python expressions."""
    tree = ast.parse(source_code)
    op_map = {
        ast.And: ast.Or,
        ast.Or: ast.And,
        ast.Add: ast.Sub,
        ast.Sub: ast.Add,
        ast.Mult: ast.FloorDiv,
        ast.FloorDiv: ast.Mult,
        ast.Eq: ast.NotEq,
        ast.NotEq: ast.Eq,
        ast.Lt: ast.LtE,
        ast.LtE: ast.Lt,
        ast.Gt: ast.GtE,
        ast.GtE: ast.Gt,
    }

    sites = []

    class SiteCollector(ast.NodeVisitor):
        def visit_BoolOp(self, node):
            if type(node.op) in op_map:
                sites.append(("BoolOp", len(sites), getattr(node, "lineno", -1), type(node.op), op_map[type(node.op)]))
            self.generic_visit(node)

        def visit_BinOp(self, node):
            if type(node.op) in op_map:
                sites.append(("BinOp", len(sites), getattr(node, "lineno", -1), type(node.op), op_map[type(node.op)]))
            self.generic_visit(node)

        def visit_Compare(self, node):
            if len(node.ops) == 1 and type(node.ops[0]) in op_map:
                from_op = type(node.ops[0])
                to_op = op_map[from_op]
                sites.append(("Compare", len(sites), getattr(node, "lineno", -1), from_op, to_op))
            self.generic_visit(node)

    SiteCollector().visit(tree)

    mutants = []
    for _, target_idx, lineno, from_op, to_op in sites[:max_mutants]:
        cloned = copy.deepcopy(tree)

        class Mutator(ast.NodeTransformer):
            def __init__(self):
                self.idx = 0

            def visit_BoolOp(self, node):
                # pre-order: check/increment BEFORE recursing into children (same order as SiteCollector)
                if type(node.op) in op_map:
                    if self.idx == target_idx:
                        node.op = to_op()
                    self.idx += 1
                self.generic_visit(node)
                return node

            def visit_BinOp(self, node):
                if type(node.op) in op_map:
                    if self.idx == target_idx:
                        node.op = to_op()
                    self.idx += 1
                self.generic_visit(node)
                return node

            def visit_Compare(self, node):
                if len(node.ops) == 1 and type(node.ops[0]) in op_map:
                    if self.idx == target_idx:
                        node.ops[0] = to_op()
                    self.idx += 1
                self.generic_visit(node)
                return node

        mutated_tree = Mutator().visit(cloned)
        ast.fix_missing_locations(mutated_tree)
        mutated_code = ast.unparse(mutated_tree)
        mutants.append(
            {
                "id": target_idx,
                "lineno": lineno,
                "operator": f"{from_op.__name__} -> {to_op.__name__}",
                "code": mutated_code,
            }
        )

    return mutants


def _analyze_dataflow(source_code: str):
    """Path-insensitive data-flow summary for all-defs / c-uses / p-uses guidance."""
    tree = ast.parse(source_code)
    defs = {}
    c_uses = {}
    p_uses = {}
    all_defs_edges = set()
    all_c_uses_edges = set()
    all_p_uses_edges = set()

    def _add_map(m, var, line):
        m.setdefault(var, []).append(line)

    def _all_load_names(expr):
        names = []
        for node in ast.walk(expr):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                names.append(node.id)
        return names

    def _record_c_use(var, line):
        _add_map(c_uses, var, line)
        for d in defs.get(var, []):
            all_defs_edges.add((var, d, line))
            all_c_uses_edges.add((var, d, line))

    def _record_p_use(var, line):
        _add_map(p_uses, var, line)
        for d in defs.get(var, []):
            all_defs_edges.add((var, d, line))
            all_p_uses_edges.add((var, d, line))

    class DataflowVisitor(ast.NodeVisitor):
        def visit_Assign(self, node):
            self.visit(node.value)
            lineno = getattr(node, "lineno", -1)
            for target in node.targets:
                # Walk all Name nodes in target (handles tuple unpacking like a,b,i=...)
                for name_node in ast.walk(target):
                    if isinstance(name_node, ast.Name) and isinstance(name_node.ctx, ast.Store):
                        _add_map(defs, name_node.id, lineno)
                # Still visit non-Name targets for c-use recording (e.g. subscripts)
                if not isinstance(target, ast.Name):
                    self.visit(target)

        def visit_AnnAssign(self, node):
            if node.value is not None:
                self.visit(node.value)
            if isinstance(node.target, ast.Name):
                _add_map(defs, node.target.id, getattr(node, "lineno", -1))

        def visit_AugAssign(self, node):
            if isinstance(node.target, ast.Name):
                _record_c_use(node.target.id, getattr(node, "lineno", -1))
            else:
                self.visit(node.target)
            self.visit(node.value)
            if isinstance(node.target, ast.Name):
                _add_map(defs, node.target.id, getattr(node, "lineno", -1))

        def visit_If(self, node):
            for var in _all_load_names(node.test):
                _record_p_use(var, getattr(node, "lineno", -1))
            for stmt in node.body:
                self.visit(stmt)
            for stmt in node.orelse:
                self.visit(stmt)

        def visit_While(self, node):
            lineno = getattr(node, "lineno", -1)
            # Erster Durchlauf: Condition + Body (normal)
            for var in _all_load_names(node.test):
                _record_p_use(var, lineno)
            for stmt in node.body:
                self.visit(stmt)
            for stmt in node.orelse:
                self.visit(stmt)
            # Zweiter Durchlauf: Condition + Body erneut mit nun bekannten Loop-Defs
            # → erfasst loop-carried Paare (z.B. a:Z.8→Z.7, i:Z.10→Z.6)
            for var in _all_load_names(node.test):
                _record_p_use(var, lineno)
            for stmt in node.body:
                self.visit(stmt)

        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                _record_c_use(node.id, getattr(node, "lineno", -1))

    DataflowVisitor().visit(tree)

    return {
        "defs": defs,
        "c_uses": c_uses,
        "p_uses": p_uses,
        "all_defs_edges": sorted(all_defs_edges),
        "all_c_uses_edges": sorted(all_c_uses_edges),
        "all_p_uses_edges": sorted(all_p_uses_edges),
    }


def _trace_dataflow_coverage(source_code: str, test_cases: list):
    """Dynamic def-use coverage via sys.settrace."""
    import sys

    static = _analyze_dataflow(source_code)
    all_defs_obligs = set(static["all_defs_edges"])
    all_c_uses_obligs = set(static["all_c_uses_edges"])
    all_p_uses_obligs = set(static["all_p_uses_edges"])

    def_lines: dict = {}
    cuse_lines: dict = {}
    puse_lines: dict = {}

    for var, d, u in all_c_uses_obligs:
        def_lines.setdefault(d, set()).add(var)
        cuse_lines.setdefault(u, set()).add(var)
    for var, d, u in all_p_uses_obligs:
        def_lines.setdefault(d, set()).add(var)
        puse_lines.setdefault(u, set()).add(var)

    covered_defs: set = set()
    covered_cuses: set = set()
    covered_puses: set = set()

    compiled = compile(source_code, "<df_dynamic>", "exec")

    for tc in test_cases:
        last_def: dict = {}
        prev_line: list = [None]

        def make_tracer():
            _last = last_def
            _prev = prev_line

            def _tracer(frame, event, arg):
                if frame.f_code.co_filename != "<df_dynamic>":
                    return None
                if event == "call":
                    return _tracer
                if event not in ("line", "return"):
                    return _tracer

                if event == "return":
                    just_done = frame.f_lineno
                else:
                    just_done = _prev[0]

                if just_done is not None:
                    for var in def_lines.get(just_done, ()):
                        _last[var] = just_done

                if event == "line":
                    current = frame.f_lineno
                    for var in cuse_lines.get(current, ()):
                        if var in _last:
                            edge = (var, _last[var], current)
                            covered_cuses.add(edge)
                            covered_defs.add(edge)
                    for var in puse_lines.get(current, ()):
                        if var in _last:
                            edge = (var, _last[var], current)
                            covered_puses.add(edge)
                            covered_defs.add(edge)
                    _prev[0] = current

                return _tracer
            return _tracer

        ns: dict = {}
        exec(compiled, ns)
        tracer = make_tracer()
        sys.settrace(tracer)
        try:
            eval(tc.strip(), dict(ns))
        except Exception:
            pass
        finally:
            sys.settrace(None)

    # all-defs: aggregate at (var, def_line) level — satisfied if ANY use covered
    all_def_pairs = {(v, d) for v, d, u in all_defs_obligs}
    covered_def_pairs = {(v, d) for v, d, u in covered_defs} & all_def_pairs
    p_def_pairs = {(v, d) for v, d, u in all_p_uses_obligs}
    c_def_pairs = {(v, d) for v, d, u in all_c_uses_obligs}

    def _mixed_criterion(primary_obligs, primary_covered, fallback_obligs, fallback_covered):
        """all-X/some-Y: all X edges + for defs with no X, ≥1 Y edge."""
        primary_defs = {(v, d) for v, d, u in primary_obligs}
        fallback_defs = {(v, d) for v, d, u in fallback_obligs}
        obligs: set = set(primary_obligs)
        covered: set = set(primary_obligs & primary_covered)
        for vd in fallback_defs - primary_defs:
            sentinel = (vd[0], vd[1], "some")
            obligs.add(sentinel)
            if any(e[0] == vd[0] and e[1] == vd[1] for e in fallback_covered):
                covered.add(sentinel)
        return {"covered": covered, "missing": obligs - covered}

    cov_c = covered_cuses & all_c_uses_obligs
    cov_p = covered_puses & all_p_uses_obligs

    return {
        "all_defs": {
            "covered": covered_def_pairs,
            "missing": all_def_pairs - covered_def_pairs,
        },
        "all_c_uses": {
            "covered": cov_c,
            "missing": all_c_uses_obligs - cov_c,
        },
        "all_p_uses": {
            "covered": cov_p,
            "missing": all_p_uses_obligs - cov_p,
        },
        "all_uses": {
            "covered": cov_c | cov_p,
            "missing": (all_c_uses_obligs | all_p_uses_obligs) - (cov_c | cov_p),
        },
        "some_c_uses": {
            "covered": {(v, d) for v, d, u in cov_c},
            "missing": c_def_pairs - {(v, d) for v, d, u in cov_c},
        },
        "some_p_uses": {
            "covered": {(v, d) for v, d, u in cov_p},
            "missing": p_def_pairs - {(v, d) for v, d, u in cov_p},
        },
        "all_p_uses_some_c_uses": _mixed_criterion(
            all_p_uses_obligs, cov_p, all_c_uses_obligs, cov_c
        ),
        "all_c_uses_some_p_uses": _mixed_criterion(
            all_c_uses_obligs, cov_c, all_p_uses_obligs, cov_p
        ),
    }


def _find_minimal_test_suite(source_code: str, candidates: list, criterion: str, fixed: list = None):
    """Greedy set-cover to find the minimal subset of candidates that satisfies criterion."""
    static = _analyze_dataflow(source_code)

    _all_c = set(static["all_c_uses_edges"])   # 3-tuples
    _all_p = set(static["all_p_uses_edges"])   # 3-tuples
    _c_def = {(v, d) for v, d, u in _all_c}   # 2-tuples — (var, def) that have c-uses
    _p_def = {(v, d) for v, d, u in _all_p}   # 2-tuples — (var, def) that have p-uses
    _all_def = _c_def | _p_def                 # 2-tuples — all definitions

    def _obligations(crit):
        if crit == "all-defs":
            return _all_def                          # 2-tuples
        if crit == "all-c-uses":
            return _all_c                            # 3-tuples
        if crit == "all-p-uses":
            return _all_p                            # 3-tuples
        if crit == "all-uses":
            return _all_c | _all_p
        if crit == "some-c-uses":
            return _c_def                            # 2-tuples: ≥1 c-use per (var,def)
        if crit == "some-p-uses":
            return _p_def                            # 2-tuples
        if crit == "all-p-uses/some-c-uses":
            return _all_p | _c_def                   # 3-tuples + 2-tuples
        if crit == "all-c-uses/some-p-uses":
            return _all_c | _p_def
        return set()

    def _project(r):
        """Compute coverage sets for all criterion types from one trace result."""
        c = r["all_c_uses"]["covered"]   # 3-tuples
        p = r["all_p_uses"]["covered"]   # 3-tuples
        d = r["all_defs"]["covered"]     # 2-tuples (var, def)
        cd = {(v, df) for v, df, u in c}  # 2-tuples from covered c-uses
        pd = {(v, df) for v, df, u in p}  # 2-tuples from covered p-uses
        return c, p, d, cd, pd

    tc_coverage = {}
    for tc in candidates:
        r = _trace_dataflow_coverage(source_code, [tc])
        c, p, d, cd, pd = _project(r)
        if criterion == "all-defs":
            covered = d
        elif criterion == "all-c-uses":
            covered = c
        elif criterion == "all-p-uses":
            covered = p
        elif criterion == "all-uses":
            covered = c | p
        elif criterion == "some-c-uses":
            covered = cd
        elif criterion == "some-p-uses":
            covered = pd
        elif criterion == "all-p-uses/some-c-uses":
            covered = p | cd
        elif criterion == "all-c-uses/some-p-uses":
            covered = c | pd
        else:
            covered = set()
        tc_coverage[tc] = covered

    obligs = _obligations(criterion)

    already_covered: set = set()
    if fixed:
        for tc in fixed:
            already_covered |= tc_coverage.get(tc, set())
    already_covered &= obligs

    remaining = obligs - already_covered
    extra_candidates = [c for c in candidates if c not in (fixed or [])]
    selected = []
    while remaining:
        if not extra_candidates:
            break
        best_tc = max(extra_candidates, key=lambda t: len(tc_coverage.get(t, set()) & remaining))
        gain = tc_coverage.get(best_tc, set()) & remaining
        if not gain:
            break
        selected.append(best_tc)
        remaining -= gain
        extra_candidates = [c for c in extra_candidates if c != best_tc]

    return {
        "selected": selected,
        "uncovered": remaining,
        "tc_coverage": tc_coverage,
        "total_obligs": obligs,
        "already_covered": already_covered,
    }


def _build_cfg(source_code: str):
    """Build a simple statement-level CFG for Python code."""
    tree = ast.parse(source_code)
    nodes = []
    edges = []

    for stmt in tree.body:
        line = getattr(stmt, "lineno", -1)
        nodes.append((line, type(stmt).__name__))

    for i in range(len(nodes) - 1):
        edges.append((nodes[i][0], nodes[i + 1][0], "seq"))

    for stmt in ast.walk(tree):
        if isinstance(stmt, ast.If):
            src = getattr(stmt, "lineno", -1)
            if stmt.body:
                edges.append((src, getattr(stmt.body[0], "lineno", -1), "true"))
            if stmt.orelse:
                edges.append((src, getattr(stmt.orelse[0], "lineno", -1), "false"))
        if isinstance(stmt, ast.While):
            src = getattr(stmt, "lineno", -1)
            if stmt.body:
                first = getattr(stmt.body[0], "lineno", -1)
                edges.append((src, first, "loop-true"))
                edges.append((first, src, "back"))

    return {"nodes": nodes, "edges": edges}


def _analyze_reachability(source_code: str):
    """Return reachable vs unreachable statement lines (conservative)."""
    tree = ast.parse(source_code)
    all_stmt_lines = sorted({getattr(s, "lineno", -1) for s in ast.walk(tree) if isinstance(s, ast.stmt)})
    reachable = set()

    def visit_stmt_list(stmts, stop_on_terminal=False):
        terminated = False
        for s in stmts:
            if terminated and stop_on_terminal:
                continue
            line = getattr(s, "lineno", -1)
            if line >= 0:
                reachable.add(line)
            if isinstance(s, ast.If):
                visit_stmt_list(s.body, stop_on_terminal=True)
                visit_stmt_list(s.orelse, stop_on_terminal=True)
            elif isinstance(s, ast.While):
                visit_stmt_list(s.body, stop_on_terminal=True)
                visit_stmt_list(s.orelse, stop_on_terminal=True)
            if isinstance(s, (ast.Return, ast.Raise)):
                terminated = True

    visit_stmt_list(tree.body, stop_on_terminal=True)
    unreachable = [ln for ln in all_stmt_lines if ln not in reachable and ln >= 0]
    return {
        "reachable": sorted([ln for ln in reachable if ln >= 0]),
        "unreachable": unreachable,
        "cfg": _build_cfg(source_code),
    }


def _check_equivalence(code_a: str, code_b: str, tests):
    """Compare two program snippets on provided test expressions."""
    for test_expr in tests:
        ns_a = {}
        ns_b = {}
        exec(compile(code_a, "<prog_a>", "exec"), ns_a)
        exec(compile(code_b, "<prog_b>", "exec"), ns_b)
        out_a = eval(test_expr, ns_a)
        out_b = eval(test_expr, ns_b)
        if out_a != out_b:
            return {
                "equivalent": False,
                "counterexample": test_expr,
                "out_a": out_a,
                "out_b": out_b,
            }
    return {"equivalent": True, "counterexample": None}


def _detect_mutation_equivalence(original_code: str, mutant_code: str, tests):
    """Convenience wrapper for mutant-vs-original equivalence check."""
    return _check_equivalence(original_code, mutant_code, tests)


# ── SAT / Z3 helpers ──────────────────────────────────────────────────────

def _euf_term_from_ast(node):
    """Parse Name / function-call AST into a hashable EUF term."""
    if isinstance(node, ast.Name):
        return ("var", node.id)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return ("fun", node.func.id, tuple(_euf_term_from_ast(a) for a in node.args))
    raise ValueError("Nur Variablen und Funktionsaufrufe sind erlaubt, z.B. a, f(a), g(a,b)")


def _euf_term_to_str(term):
    if term[0] == "var":
        return term[1]
    _, fn, args = term
    return f"{fn}({', '.join(_euf_term_to_str(a) for a in args)})"


def _euf_collect_subterms(term, out):
    if term in out:
        return
    out.add(term)
    if term[0] == "fun":
        for a in term[2]:
            _euf_collect_subterms(a, out)


def _euf_parse_constraints(text):
    """Return (equalities, disequalities) as lists of term-pairs."""
    eqs = []
    neqs = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if "!=" in line:
            left, right = line.split("!=", 1)
            rel = "!="
        elif "==" in line:
            left, right = line.split("==", 1)
            rel = "=="
        else:
            raise ValueError(f"Ungültige Zeile (erwarte == oder !=): '{line}'")

        l_ast = ast.parse(left.strip(), mode="eval").body
        r_ast = ast.parse(right.strip(), mode="eval").body
        l_term = _euf_term_from_ast(l_ast)
        r_term = _euf_term_from_ast(r_ast)
        if rel == "==":
            eqs.append((l_term, r_term))
        else:
            neqs.append((l_term, r_term))
    return eqs, neqs


def _euf_congruence_closure(equalities, disequalities):
    """Deterministic congruence-closure with step log for EUF teaching."""
    all_terms = set()
    for a, b in equalities + disequalities:
        _euf_collect_subterms(a, all_terms)
        _euf_collect_subterms(b, all_terms)

    parent = {t: t for t in all_terms}
    rank = {t: 0 for t in all_terms}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return False
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1
        return True

    steps = []
    for a, b in equalities:
        if union(a, b):
            steps.append(f"Merge aus Gleichung: {_euf_term_to_str(a)} == {_euf_term_to_str(b)}")

    terms_list = sorted(all_terms, key=_euf_term_to_str)
    changed = True
    while changed:
        changed = False
        for i in range(len(terms_list)):
            t1 = terms_list[i]
            if t1[0] != "fun":
                continue
            for j in range(i + 1, len(terms_list)):
                t2 = terms_list[j]
                if t2[0] != "fun":
                    continue
                if t1[1] != t2[1] or len(t1[2]) != len(t2[2]):
                    continue
                if all(find(a1) == find(a2) for a1, a2 in zip(t1[2], t2[2])):
                    if union(t1, t2):
                        changed = True
                        steps.append(
                            "Merge durch Kongruenz: "
                            f"{_euf_term_to_str(t1)} == {_euf_term_to_str(t2)}"
                        )

    conflict = None
    for a, b in disequalities:
        if find(a) == find(b):
            conflict = (a, b)
            break

    classes = {}
    for t in terms_list:
        r = find(t)
        classes.setdefault(r, []).append(t)
    class_strings = [sorted((_euf_term_to_str(t) for t in members)) for members in classes.values()]
    class_strings.sort(key=lambda cls: cls[0] if cls else "")

    return {
        "sat": conflict is None,
        "steps": steps,
        "classes": class_strings,
        "conflict": conflict,
    }


def _parse_cnf_text(cnf_text):
    """Parse DIMACS-like CNF lines (without trailing 0), e.g. '1 -2 3'."""
    clauses = []
    for line in cnf_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        lits = [int(x) for x in line.split() if x]
        if any(l == 0 for l in lits):
            raise ValueError("Literal 0 ist hier nicht erlaubt.")
        clauses.append(lits)
    return clauses


def _simplify_cnf(clauses, assignment):
    """Apply current assignment to CNF. Return None on conflict, else simplified clauses."""
    simplified = []
    for clause in clauses:
        clause_satisfied = False
        new_clause = []
        for lit in clause:
            v = abs(lit)
            val = assignment.get(v)
            if val is None:
                new_clause.append(lit)
            else:
                lit_true = (lit > 0 and val) or (lit < 0 and not val)
                if lit_true:
                    clause_satisfied = True
                    break
        if clause_satisfied:
            continue
        if len(new_clause) == 0:
            return None
        simplified.append(new_clause)
    return simplified


def _run_dpll_with_trace(clauses):
    """Deterministic DPLL with trace: unit prop, pure literals, decisions, backtracking."""
    trace = []

    def rec(current_clauses, assignment, level):
        current_clauses = _simplify_cnf(current_clauses, assignment)
        if current_clauses is None:
            trace.append(f"L{level}: Konflikt (leere Klausel)")
            return False, assignment
        if not current_clauses:
            trace.append(f"L{level}: Alle Klauseln erfüllt")
            return True, assignment

        changed = True
        while changed:
            changed = False

            unit_lits = [c[0] for c in current_clauses if len(c) == 1]
            for lit in unit_lits:
                v = abs(lit)
                val = lit > 0
                if v in assignment and assignment[v] != val:
                    trace.append(f"L{level}: Konflikt bei Unit {lit}")
                    return False, assignment
                if v not in assignment:
                    assignment[v] = val
                    trace.append(f"L{level}: Unit Propagation setzt x{v}={val}")
                    changed = True

            current_clauses = _simplify_cnf(current_clauses, assignment)
            if current_clauses is None:
                trace.append(f"L{level}: Konflikt nach Unit Propagation")
                return False, assignment
            if not current_clauses:
                trace.append(f"L{level}: Alle Klauseln erfüllt")
                return True, assignment

            lit_set = set(l for c in current_clauses for l in c)
            pure_lits = []
            for lit in sorted(lit_set, key=lambda x: (abs(x), x)):
                if -lit not in lit_set:
                    pure_lits.append(lit)

            for lit in pure_lits:
                v = abs(lit)
                val = lit > 0
                if v in assignment:
                    continue
                assignment[v] = val
                trace.append(f"L{level}: Pure Literal setzt x{v}={val}")
                changed = True

            if changed:
                current_clauses = _simplify_cnf(current_clauses, assignment)
                if current_clauses is None:
                    trace.append(f"L{level}: Konflikt nach Pure Literal")
                    return False, assignment
                if not current_clauses:
                    trace.append(f"L{level}: Alle Klauseln erfüllt")
                    return True, assignment

        var_candidates = sorted({abs(l) for c in current_clauses for l in c if abs(l) not in assignment})
        if not var_candidates:
            trace.append(f"L{level}: Keine offenen Variablen mehr")
            return True, assignment

        var = var_candidates[0]

        trace.append(f"L{level}: Entscheidung x{var}=True")
        a_true = dict(assignment)
        a_true[var] = True
        sat_result, model = rec(current_clauses, a_true, level + 1)
        if sat_result:
            return True, model

        trace.append(f"L{level}: Backtrack, versuche x{var}=False")
        a_false = dict(assignment)
        a_false[var] = False
        return rec(current_clauses, a_false, level + 1)

    sat_result, model = rec(clauses, {}, 0)
    return sat_result, model, trace


def _find_smt_model(formula_str: str):
    """Solve an SMT formula and return SAT/UNSAT/UNKNOWN with model when SAT."""
    from z3 import Int, Real, Bool, And, Or, Not, Implies, Solver, sat, unsat

    z3ns = {
        "Int": Int,
        "Real": Real,
        "Bool": Bool,
        "And": And,
        "Or": Or,
        "Not": Not,
        "Implies": Implies,
    }
    solver = Solver()
    formula = eval(formula_str, z3ns)
    solver.add(formula)
    res = solver.check()
    if res == sat:
        m = solver.model()
        return {"result": "SAT", "model": {d.name(): str(m[d]) for d in m.decls()}}
    if res == unsat:
        return {"result": "UNSAT", "model": None}
    return {"result": "UNKNOWN", "model": None}


def _analyze_unsat_core(constraints_text: str):
    """Build tracked constraints and return UNSAT core when inconsistent."""
    from z3 import Int, Real, Bool, And, Or, Not, Implies, Solver, sat, unsat, Bool as Z3Bool

    lines = [ln.strip() for ln in constraints_text.splitlines() if ln.strip()]
    solver = Solver()
    z3ns = {
        "Int": Int,
        "Real": Real,
        "Bool": Bool,
        "And": And,
        "Or": Or,
        "Not": Not,
        "Implies": Implies,
    }

    labels = []
    for i, line in enumerate(lines):
        lbl = Z3Bool(f"c_{i}")
        labels.append((lbl, line))
        solver.assert_and_track(eval(line, z3ns), lbl)

    res = solver.check()
    if res == sat:
        return {"result": "SAT", "core": [], "constraints": lines}
    if res == unsat:
        core_lbl = {str(x) for x in solver.unsat_core()}
        core_lines = [line for lbl, line in labels if str(lbl) in core_lbl]
        return {"result": "UNSAT", "core": core_lines, "constraints": lines}
    return {"result": "UNKNOWN", "core": [], "constraints": lines}


def _eliminate_quantifiers(formula_str: str):
    """Try to eliminate quantifiers using Z3 simplify/tactics."""
    from z3 import Int, Real, Bool, And, Or, Not, Implies, Exists, ForAll, Tactic, simplify

    z3ns = {
        "Int": Int,
        "Real": Real,
        "Bool": Bool,
        "And": And,
        "Or": Or,
        "Not": Not,
        "Implies": Implies,
        "Exists": Exists,
        "ForAll": ForAll,
    }
    fml = eval(formula_str, z3ns)
    simplified = simplify(fml)
    try:
        qe_goal = Tactic("qe")(fml)
        qe_txt = str(qe_goal.as_expr())
    except Exception:
        qe_txt = str(simplified)
    return {"original": str(fml), "qe": qe_txt, "simplified": str(simplified)}


# ── Hoare / WP helpers ────────────────────────────────────────────────────

def _wp_of_stmts(stmts, post, vars_dict, z3ns, steps, depth=0):
    """
    Recursively compute WP of a list of AST statements w.r.t. post.
    Supports: ast.Assign (x = expr), ast.If (if/else), sequences.
    Returns the Z3 formula for WP(stmts, post).
    """
    from z3 import And, Not, Implies, substitute

    indent = "  " * depth

    if not stmts:
        return post

    current = post
    for stmt in reversed(stmts):
        if isinstance(stmt, ast.Assign):
            if (len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and stmt.targets[0].id in vars_dict):
                var_name = stmt.targets[0].id
                rhs_str = ast.unparse(stmt.value)
                expr_z3 = eval(rhs_str, z3ns)
                if isinstance(expr_z3, int):
                    from z3 import IntVal
                    expr_z3 = IntVal(expr_z3)
                elif isinstance(expr_z3, float):
                    from z3 import RealVal
                    expr_z3 = RealVal(expr_z3)
                new = substitute(current, (vars_dict[var_name], expr_z3))
                steps.append(
                    f"{indent}← `{var_name} := {rhs_str}` → `{new}`"
                )
                current = new
            else:
                steps.append(f"{indent}⚠ Übersprungen (kein einfaches Assignment): `{ast.unparse(stmt)}`")

        elif isinstance(stmt, ast.If):
            cond_str = ast.unparse(stmt.test)
            cond_z3 = eval(cond_str, z3ns)

            steps.append(f"{indent}🔀 if `{cond_str}`:")
            then_steps = []
            wp_then = _wp_of_stmts(stmt.body, current, vars_dict, z3ns, then_steps, depth + 1)
            for s in then_steps:
                steps.append(s)
            steps.append(f"{indent}  WP(then, Q) = `{wp_then}`")

            if stmt.orelse:
                steps.append(f"{indent}  else:")
                else_steps = []
                wp_else = _wp_of_stmts(stmt.orelse, current, vars_dict, z3ns, else_steps, depth + 1)
                for s in else_steps:
                    steps.append(s)
                steps.append(f"{indent}  WP(else, Q) = `{wp_else}`")
                new = And(Implies(cond_z3, wp_then), Implies(Not(cond_z3), wp_else))
                steps.append(
                    f"{indent}  WP(if/else, Q) = `(B→WP_then) ∧ (¬B→WP_else)` = `{new}`"
                )
            else:
                new = And(Implies(cond_z3, wp_then), Implies(Not(cond_z3), current))
                steps.append(
                    f"{indent}  WP(if, Q) = `(B→WP_then) ∧ (¬B→Q)` = `{new}`"
                )
            current = new

        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            pass

        else:
            steps.append(f"{indent}⚠ Nicht unterstützt: `{ast.unparse(stmt)}`")

    return current


def _find_hoare_counterexample(code: str, pre_str: str, post_str: str):
    """Find model for Pre ∧ ¬WP(code, Post) using assignment/if subset."""
    from z3 import Int, And, Or, Not, Implies, Solver, sat

    tree = ast.parse(textwrap.dedent(code))
    names = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name)})
    vars_dict = {n: Int(n) for n in names}
    z3ns = {**vars_dict, "And": And, "Or": Or, "Not": Not, "Implies": Implies}

    pre = eval(pre_str, z3ns)
    post = eval(post_str, z3ns)
    steps = []
    wp = _wp_of_stmts(tree.body, post, vars_dict, z3ns, steps)

    s = Solver()
    s.add(pre, Not(wp))
    if s.check() == sat:
        m = s.model()
        return {
            "found": True,
            "counterexample": {n: str(m.eval(vars_dict[n], model_completion=True)) for n in names},
            "wp": str(wp),
            "steps": steps,
        }
    return {"found": False, "counterexample": None, "wp": str(wp), "steps": steps}


def _falsify_loop_invariant(code: str, invariant_str: str, pre_str: str, post_str: str):
    """Return first failing loop-invariant obligation with counterexample if any."""
    from z3 import Int, And, Or, Not, Implies, Solver, sat, unsat

    tree = ast.parse(textwrap.dedent(code))
    loop = next((s for s in tree.body if isinstance(s, ast.While)), None)
    if loop is None:
        return {"error": "Keine while-Schleife im Programm gefunden."}

    names = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name)})
    vars_dict = {n: Int(n) for n in names}
    z3ns = {**vars_dict, "And": And, "Or": Or, "Not": Not, "Implies": Implies}

    I = eval(invariant_str, z3ns)
    Pre = eval(pre_str, z3ns)
    Post = eval(post_str, z3ns)
    B = eval(ast.unparse(loop.test), z3ns)

    init_prefix = []
    for s in tree.body:
        if s is loop:
            break
        init_prefix.append(s)

    init_steps = []
    wp_init = _wp_of_stmts(init_prefix, I, vars_dict, z3ns, init_steps)
    s1 = Solver()
    s1.add(Pre, Not(wp_init))
    if s1.check() == sat:
        m = s1.model()
        return {
            "falsified": True,
            "which": "Init",
            "counterexample": {n: str(m.eval(vars_dict[n], model_completion=True)) for n in names},
        }

    body_steps = []
    wp_body = _wp_of_stmts(loop.body, I, vars_dict, z3ns, body_steps)
    s2 = Solver()
    s2.add(I, B, Not(wp_body))
    if s2.check() == sat:
        m = s2.model()
        return {
            "falsified": True,
            "which": "Erhaltung",
            "counterexample": {n: str(m.eval(vars_dict[n], model_completion=True)) for n in names},
        }

    s3 = Solver()
    s3.add(I, Not(B), Not(Post))
    if s3.check() == sat:
        m = s3.model()
        return {
            "falsified": True,
            "which": "Konsequenz",
            "counterexample": {n: str(m.eval(vars_dict[n], model_completion=True)) for n in names},
        }

    return {"falsified": False, "which": None, "counterexample": None}


def _generate_hoare_proof(
    code: str,
    invariant_str: str,
    pre_str: str,
    post_str: str,
    vars_str: str = "",
    domain_hint: str = "N₀",
):
    """
    Generates a step-by-step Hoare proof in exam annotation format.
    Returns a list of markdown strings.

    Format:
      {Pre}
      if (B) {
          {Pre ∧ B}   ← if-Regel
          x = e;
          {I}         ← Zuweisungsregel: WP(x:=e, I) = ...
      } else {
          {Pre ∧ ¬B}  ← if-Regel
          x = e;
          {I}         ← Zuweisungsregel: WP(x:=e, I) = ...
      }
      {I}             ← if/else-Regel: beide Zweige ✅
      while (B) {
          {I ∧ B}     ← While-Regel
          x = x + 1;
          {I}         ← Zuweisungsregel: WP(...) + Consequence ✅
      }
      {I ∧ ¬B}       ← While-Regel
      {Post}          ← Konsequenz-Regel: I ∧ ¬B ⊨ Post ✅
    """
    from z3 import Int, And, Or, Not, Implies, Solver, sat, unsat, substitute, BoolVal, IntVal, is_expr

    code = textwrap.dedent(code)
    tree = ast.parse(code)

    names = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name)})
    extra = [v.strip() for v in vars_str.split(",") if v.strip()]
    vars_dict = {n: Int(n) for n in sorted(set(names) | set(extra))}
    z3ns = {**vars_dict, "And": And, "Or": Or, "Not": Not, "Implies": Implies, "BoolVal": BoolVal}

    def _eval_z3(s):
        """Eval a string as a Z3 expression, rewriting and/or/not via AST."""
        import ast as _ast2
        s = s.strip()
        if s.lower() == 'true':  return BoolVal(True)
        if s.lower() == 'false': return BoolVal(False)
        try:
            tree2 = _ast2.parse(s, mode='eval')
        except SyntaxError:
            return eval(s, z3ns)

        class _BoolRewriter(_ast2.NodeTransformer):
            def visit_BoolOp(self, node):
                self.generic_visit(node)
                fn = 'And' if isinstance(node.op, _ast2.And) else 'Or'
                return _ast2.Call(func=_ast2.Name(id=fn, ctx=_ast2.Load()),
                                  args=node.values, keywords=[])
            def visit_UnaryOp(self, node):
                self.generic_visit(node)
                if isinstance(node.op, _ast2.Not):
                    return _ast2.Call(func=_ast2.Name(id='Not', ctx=_ast2.Load()),
                                      args=[node.operand], keywords=[])
                return node

        new_tree = _ast2.fix_missing_locations(_BoolRewriter().visit(tree2))
        compiled = compile(new_tree, '<z3eval>', 'eval')
        return eval(compiled, z3ns)

    _safe_eval = _eval_z3

    try:
        I    = _eval_z3(invariant_str)
        Pre  = _eval_z3(pre_str)
        Post = _eval_z3(post_str)
    except Exception as e:
        return [f"❌ Fehler beim Parsen: {e}"]

    def _wp_assign(stmt, post):
        """Compute WP for a single assignment statement."""
        v = stmt.targets[0].id
        r = ast.unparse(stmt.value)
        rv = eval(r, z3ns)
        if not is_expr(rv): rv = IntVal(int(rv))
        return substitute(post, (vars_dict[v], rv)), v, r

    def _wp_stmts(stmts, post):
        """Compute WP backwards through a list of assignment-only statements."""
        cur = post
        for s in reversed(stmts):
            if isinstance(s, ast.Assign) and len(s.targets) == 1 and s.targets[0].id in vars_dict:
                cur, _, _ = _wp_assign(s, cur)
        return cur

    def _check(solver_add_fn):
        s = Solver()
        solver_add_fn(s)
        return s.check() == unsat

    # pretty-print a Z3 expr in a readable way
    def _fmt(expr):
        s = str(expr)
        # replace z3 And/Or with ∧/∨ etc. for readability
        import re as _re
        s = _re.sub(r'And\(([^()]+)\)', lambda m: ' ∧ '.join(x.strip() for x in m.group(1).split(',')), s)
        s = _re.sub(r'Or\(([^()]+)\)', lambda m: ' ∨ '.join(x.strip() for x in m.group(1).split(',')), s)
        s = s.replace('Not(', '¬(')
        return s

    loop   = next((s for s in tree.body if isinstance(s, ast.While)), None)
    prefix = [s for s in tree.body if s is not loop]
    cond_str = ast.unparse(loop.test) if loop else ""

    out = []   # lines of the proof block

    # ── {Pre} ────────────────────────────────────────────────────────────────
    out.append(f"{{{pre_str}}}")
    out.append(f"    ← gegeben")

    # ── prefix statements (if/else or assignments) ────────────────────────────
    for stmt in prefix:
        if isinstance(stmt, ast.If):
            cond = ast.unparse(stmt.test)
            # then WP
            wp_then = _wp_stmts(stmt.body, I)
            # else WP
            wp_else = _wp_stmts(stmt.orelse or [], I) if stmt.orelse else I

            init_ok = _check(lambda s: (s.add(Pre, Not(
                And(Implies(_eval_z3(cond), wp_then),
                    Implies(Not(_eval_z3(cond)), wp_else))
            )))
            )

            out.append(f"if ({cond}) {{")
            out.append(f"    {{{pre_str} ∧ {cond}}}")
            out.append(f"        ← if/else-Regel: Pre ∧ B")
            for s2 in stmt.body:
                if isinstance(s2, ast.Assign):
                    v = s2.targets[0].id; r = ast.unparse(s2.value)
                    out.append(f"    {v} = {r};")
            out.append(f"    {{{_fmt(I)}}}")
            then_ok = _check(lambda s: (s.add(_eval_z3(cond), Pre, Not(wp_then))))
            out.append(f"        ← Zuweisungsregel: WP({stmt.body[0].targets[0].id}:={ast.unparse(stmt.body[0].value)}, I) = {_fmt(wp_then)}")
            out.append(f"           Consequence: Pre ∧ B ⊨ WP  {'✅' if then_ok else '❌'}")
            out.append(f"}} else {{")
            out.append(f"    {{{pre_str} ∧ ¬({cond})}}")
            out.append(f"        ← if/else-Regel: Pre ∧ ¬B")
            for s2 in (stmt.orelse or []):
                if isinstance(s2, ast.Assign):
                    v = s2.targets[0].id; r = ast.unparse(s2.value)
                    out.append(f"    {v} = {r};")
            out.append(f"    {{{_fmt(I)}}}")
            else_ok = _check(lambda s: (s.add(Not(_eval_z3(cond)), Pre, Not(wp_else))))
            out.append(f"        ← Zuweisungsregel: WP({stmt.orelse[0].targets[0].id}:={ast.unparse(stmt.orelse[0].value)}, I) = {_fmt(wp_else)}")
            out.append(f"           Consequence: Pre ∧ ¬B ⊨ WP  {'✅' if else_ok else '❌'}")
            out.append(f"}}")
            out.append(f"{{{_fmt(I)}}}")
            out.append(f"    ← if/else-Regel: beide Zweige enden in I  {'✅' if init_ok else '❌'}")

        elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            wp, v, r = _wp_assign(stmt, I)
            ok = _check(lambda s: (s.add(Pre, Not(wp))))
            out.append(f"{v} = {r};")
            out.append(f"{{{_fmt(I)}}}")
            out.append(f"    ← Zuweisungsregel: WP({v}:={r}, I) = {_fmt(wp)}")
            out.append(f"       Consequence: Pre ⊨ WP  {'✅' if ok else '❌'}")

    # ── while loop ────────────────────────────────────────────────────────────
    if loop:
        body_stmts = loop.body
        wp_body = _wp_stmts(body_stmts, I)

        pres_ok = _check(lambda s: (
            s.add(_safe_eval(invariant_str), _eval_z3(cond_str),
                  *[v >= 0 for v in vars_dict.values()],
                  Not(wp_body))
        ))
        out.append(f"while ({cond_str}) {{")
        out.append(f"    {{{_fmt(I)} ∧ {cond_str}}}")
        out.append(f"        ← While-Regel: I ∧ B gilt am Schleifeneingang")
        for s2 in body_stmts:
            if isinstance(s2, ast.Assign):
                v = s2.targets[0].id; r = ast.unparse(s2.value)
                out.append(f"    {v} = {r};")
        out.append(f"    {{{_fmt(I)}}}")
        if body_stmts and isinstance(body_stmts[0], ast.Assign):
            bv = body_stmts[0].targets[0].id; br = ast.unparse(body_stmts[0].value)
            out.append(f"        ← Zuweisungsregel: WP({bv}:={br}, I) = {_fmt(wp_body)}")
        out.append(f"           Consequence: I ∧ B ⊨ WP(body, I)  {'✅' if pres_ok else '❌'}")
        out.append(f"}}")

        # Exit annotation
        out.append(f"{{{_fmt(I)} ∧ ¬({cond_str})}}")
        out.append(f"    ← While-Regel: I bleibt, B ist falsch")

        conseq_ok = _check(lambda s: (
            s.add(_safe_eval(invariant_str), Not(_eval_z3(cond_str)),
                  *[v >= 0 for v in vars_dict.values()],
                  Not(Post))
        ))
        out.append(f"{{{post_str}}}")
        out.append(f"    ← Konsequenz-Regel: I ∧ ¬B ⊨ Post  {'✅' if conseq_ok else '❌'}")
    else:
        out.append(f"{{{post_str}}}")

    # Render as a single code block
    proof_block = "```\n" + "\n".join(out) + "\n```"
    return [proof_block]


def _generate_invariant_ce_explanation(
    loop_body_str: str,
    invariant_str: str,
    cond_str: str,
    counterexample: dict,
) -> list:
    """
    Given a counterexample for non-inductivity, format the before/after explanation
    in exam style: show state before body, evaluate P, run body, show state after, evaluate P.
    """
    lines = []
    # Evaluate body with CE values
    ns = {k: int(v) for k, v in counterexample.items()}
    try:
        exec(compile(textwrap.dedent(loop_body_str), "<body>", "exec"), ns)
    except Exception:
        pass

    before = {k: int(v) for k, v in counterexample.items()}
    after  = {k: ns[k] for k in ns if not k.startswith("__")}

    # Evaluate P before
    def eval_p(state, formula_str):
        try:
            return bool(eval(formula_str, {**state}))
        except Exception:
            return "?"

    p_before = eval_p(before, invariant_str)
    b_before = eval_p(before, cond_str)
    p_after  = eval_p(after,  invariant_str)

    lines.append("**Gegenbeispiel (Nicht-Induktivität):**")
    lines.append("")
    lines.append("| Variable | Vor Body | Nach Body |")
    lines.append("|---|---|---|")
    all_vars = sorted(set(before) | set(after))
    for v in all_vars:
        b_val = before.get(v, "—")
        a_val = after.get(v,  "—")
        lines.append(f"| `{v}` | `{b_val}` | `{a_val}` |")
    lines.append("")
    lines.append(f"- **Vor Body:** P = `{invariant_str}` → `{p_before}` "
                 f"({'✅ hält' if p_before else '❌ gilt nicht'}) | "
                 f"B = `{cond_str}` → `{b_before}` ({'Body läuft' if b_before else 'Body läuft nicht'})")
    lines.append(f"- **Nach Body:** P = `{invariant_str}` → `{p_after}` "
                 f"({'✅ hält' if p_after else '❌ VERLETZT — P ist nicht induktiv'})")
    lines.append("")
    lines.append(f"> Hoare-Triple {{P∧B}} body {{P}} gilt **NICHT** für diesen Zustand.")
    return lines


# ── Temporal logic helpers ────────────────────────────────────────────────

def _ctl_check(states, transitions, labels, init_states):
    """
    Returns a CTL model checker object with an eval(formula_str) method.
    Supports: atom, not, and, or, implies,
              EX, AX, EF, AF, EG, AG, EU(phi,psi), AU(phi,psi)
    """
    succ = {s: set() for s in states}
    pred = {s: set() for s in states}
    for (a, b) in transitions:
        succ[a].add(b)
        pred[b].add(a)

    def sat_atom(ap):
        return {s for s in states if ap in labels.get(s, set())}

    def sat_not(phi_set):
        return states - phi_set

    def sat_and(a_set, b_set):
        return a_set & b_set

    def sat_or(a_set, b_set):
        return a_set | b_set

    def sat_implies(a_set, b_set):
        return sat_or(sat_not(a_set), b_set)

    def sat_EX(phi_set):
        return {s for s in states if succ[s] & phi_set}

    def sat_AX(phi_set):
        return {s for s in states if succ[s] and succ[s] <= phi_set}

    def sat_EF(phi_set):
        result = set(phi_set)
        while True:
            new = result | sat_EX(result)
            if new == result:
                break
            result = new
        return result

    def sat_AF(phi_set):
        result = set(phi_set)
        while True:
            new = result | {s for s in states if succ[s] and succ[s] <= result}
            if new == result:
                break
            result = new
        return result

    def sat_EG(phi_set):
        result = set(phi_set)
        while True:
            new = result & sat_EX(result)
            if new == result:
                break
            result = new
        return result

    def sat_AG(phi_set):
        result = set(phi_set)
        while True:
            new = result & sat_AX(result)
            if new == result:
                break
            result = new
        return result

    def sat_EU(phi_set, psi_set):
        result = set(psi_set)
        while True:
            new = result | (phi_set & sat_EX(result))
            if new == result:
                break
            result = new
        return result

    def sat_AU(phi_set, psi_set):
        result = set(psi_set)
        while True:
            new = result | (phi_set & sat_AX(result))
            if new == result:
                break
            result = new
        return result

    def evaluate(node, steps):
        kind = node[0]

        if kind == "atom":
            ap = node[1]
            result = sat_atom(ap)
            steps.append((f"atom({ap})", result))
            return result

        elif kind == "not":
            inner = evaluate(node[1], steps)
            result = sat_not(inner)
            steps.append(("NOT", result))
            return result

        elif kind == "and":
            a = evaluate(node[1], steps)
            b = evaluate(node[2], steps)
            result = sat_and(a, b)
            steps.append(("AND", result))
            return result

        elif kind == "or":
            a = evaluate(node[1], steps)
            b = evaluate(node[2], steps)
            result = sat_or(a, b)
            steps.append(("OR", result))
            return result

        elif kind == "implies":
            a = evaluate(node[1], steps)
            b = evaluate(node[2], steps)
            result = sat_implies(a, b)
            steps.append(("IMPLIES", result))
            return result

        elif kind == "EX":
            inner = evaluate(node[1], steps)
            result = sat_EX(inner)
            steps.append(("EX", result))
            return result

        elif kind == "AX":
            inner = evaluate(node[1], steps)
            result = sat_AX(inner)
            steps.append(("AX", result))
            return result

        elif kind == "EF":
            inner = evaluate(node[1], steps)
            result = sat_EF(inner)
            steps.append(("EF", result))
            return result

        elif kind == "AF":
            inner = evaluate(node[1], steps)
            result = sat_AF(inner)
            steps.append(("AF", result))
            return result

        elif kind == "EG":
            inner = evaluate(node[1], steps)
            result = sat_EG(inner)
            steps.append(("EG", result))
            return result

        elif kind == "AG":
            inner = evaluate(node[1], steps)
            result = sat_AG(inner)
            steps.append(("AG", result))
            return result

        elif kind == "EU":
            phi = evaluate(node[1], steps)
            psi = evaluate(node[2], steps)
            result = sat_EU(phi, psi)
            steps.append(("EU", result))
            return result

        elif kind == "AU":
            phi = evaluate(node[1], steps)
            psi = evaluate(node[2], steps)
            result = sat_AU(phi, psi)
            steps.append(("AU", result))
            return result

        else:
            raise ValueError(f"Unbekannter Operator: {kind}")

    return evaluate, states, init_states


def _ctl_tableaux_explain(states, transitions, labels, formula_str):
    """
    Computes CTL formula satisfaction sets with full tableaux-style step trace.
    Returns (result_set, lines) where lines is a list of Markdown strings
    showing each subformula and fixpoint iteration — suitable for exam answers.
    """
    succ = {s: set() for s in states}
    pred = {s: set() for s in states}
    for (a, b) in transitions:
        succ[a].add(b)
        pred[b].add(a)

    lines = []
    all_s = set(states)

    def fmt(s):
        return "{" + ", ".join(sorted(s)) + "}" if s else "∅"

    def sat_atom(ap):
        r = {s for s in states if ap in labels.get(s, set())}
        lines.append(f"- **atom({ap})** = {fmt(r)}  "
                     f"_(Zustände mit {ap} im Label)_")
        return r

    def sat_EX(phi):
        r = {s for s in states if succ[s] & phi}
        lines.append(f"- **EX** {fmt(phi)} = {fmt(r)}  "
                     f"_(Zustände mit mind. 1 Nachfolger in φ)_")
        return r

    def sat_AX(phi):
        r = {s for s in states if succ[s] and succ[s] <= phi}
        lines.append(f"- **AX** {fmt(phi)} = {fmt(r)}")
        return r

    def sat_EF(phi):
        # μZ. φ ∪ EX Z
        Z = set(phi)
        k = 0
        lines.append(f"- **EF** {fmt(phi)} = μZ. φ ∪ EX Z:")
        lines.append(f"  - Z₀ = {fmt(Z)}")
        while True:
            new = Z | {s for s in states if succ[s] & Z}
            k += 1
            lines.append(f"  - Z{k} = {fmt(new)}")
            if new == Z:
                lines.append(f"  - Fixpunkt ✓ → EF = {fmt(Z)}")
                break
            Z = new
        return Z

    def sat_AF(phi):
        Z = set(phi)
        k = 0
        lines.append(f"- **AF** {fmt(phi)} = μZ. φ ∪ AX Z:")
        lines.append(f"  - Z₀ = {fmt(Z)}")
        while True:
            new = Z | {s for s in states if succ[s] and succ[s] <= Z}
            k += 1
            lines.append(f"  - Z{k} = {fmt(new)}")
            if new == Z:
                lines.append(f"  - Fixpunkt ✓ → AF = {fmt(Z)}")
                break
            Z = new
        return Z

    def sat_EG(phi):
        # νZ. φ ∩ EX Z  (greatest fixpoint)
        Z = set(phi)
        k = 0
        lines.append(f"- **EG** {fmt(phi)} = νZ. φ ∩ EX Z  _(größter Fixpunkt)_:")
        lines.append(f"  - Z₀ = {fmt(Z)}  _(Start: alle φ-Zustände)_")
        while True:
            ex_z = {s for s in states if succ[s] & Z}
            new = Z & ex_z
            k += 1
            lines.append(f"  - EX(Z{k-1}) = {fmt(ex_z)}")
            lines.append(f"  - Z{k} = φ ∩ EX(Z{k-1}) = {fmt(Z)} ∩ {fmt(ex_z)} = {fmt(new)}")
            if new == Z:
                lines.append(f"  - Z{k} = Z{k-1} → **Fixpunkt erreicht** → EG = {fmt(Z)}")
                break
            Z = new
        return Z

    def sat_AG(phi):
        Z = set(phi)
        k = 0
        lines.append(f"- **AG** {fmt(phi)} = νZ. φ ∩ AX Z  _(größter Fixpunkt)_:")
        lines.append(f"  - Z₀ = {fmt(Z)}")
        while True:
            ax_z = {s for s in states if succ[s] and succ[s] <= Z}
            new = Z & ax_z
            k += 1
            lines.append(f"  - Z{k} = φ ∩ AX(Z{k-1}) = {fmt(new)}")
            if new == Z:
                lines.append(f"  - Fixpunkt ✓ → AG = {fmt(Z)}")
                break
            Z = new
        return Z

    def sat_EU(phi, psi):
        Z = set(psi)
        k = 0
        lines.append(f"- **E[φ U ψ]** = μZ. ψ ∪ (φ ∩ EX Z)  _(kleinster Fixpunkt)_:")
        lines.append(f"  - Z₀ = {fmt(Z)}")
        while True:
            ex_z = {s for s in states if succ[s] & Z}
            new = Z | (phi & ex_z)
            k += 1
            lines.append(f"  - Z{k} = {fmt(new)}")
            if new == Z:
                lines.append(f"  - Fixpunkt ✓ → EU = {fmt(Z)}")
                break
            Z = new
        return Z

    def sat_AU(phi, psi):
        Z = set(psi)
        k = 0
        lines.append(f"- **A[φ U ψ]** = μZ. ψ ∪ (φ ∩ AX Z)  _(kleinster Fixpunkt)_:")
        lines.append(f"  - Z₀ = {fmt(Z)}")
        while True:
            ax_z = {s for s in states if succ[s] and succ[s] <= Z}
            new = Z | (phi & ax_z)
            k += 1
            lines.append(f"  - Z{k} = {fmt(new)}")
            if new == Z:
                lines.append(f"  - Fixpunkt ✓ → AU = {fmt(Z)}")
                break
            Z = new
        return Z

    def sat_not(s):  return all_s - s
    def sat_and(a, b): return a & b
    def sat_or(a, b):  return a | b
    def sat_implies(a, b): return (all_s - a) | b

    try:
        toks = _tokenize_ctl(formula_str)
        tree = _parse_ctl(toks)
    except Exception as e:
        return set(), [f"❌ Parse-Fehler: {e}"]

    # Recursive evaluator using the above sat_ functions with logging
    def ev(node):
        k = node[0]
        if k == "atom":     return sat_atom(node[1])
        if k == "not":      return sat_not(ev(node[1]))
        if k == "and":      r = sat_and(ev(node[1]), ev(node[2])); lines.append(f"- **AND** → {fmt(r)}"); return r
        if k == "or":       r = sat_or(ev(node[1]), ev(node[2]));  lines.append(f"- **OR** → {fmt(r)}"); return r
        if k == "implies":  return sat_implies(ev(node[1]), ev(node[2]))
        if k == "EX":       return sat_EX(ev(node[1]))
        if k == "AX":       return sat_AX(ev(node[1]))
        if k == "EF":       return sat_EF(ev(node[1]))
        if k == "AF":       return sat_AF(ev(node[1]))
        if k == "EG":       return sat_EG(ev(node[1]))
        if k == "AG":       return sat_AG(ev(node[1]))
        if k == "EU":       return sat_EU(ev(node[1]), ev(node[2]))
        if k == "AU":       return sat_AU(ev(node[1]), ev(node[2]))
        return set()

    lines.append(f"**Formel:** `{formula_str}`")
    lines.append("")
    lines.append("**Kripke-Struktur:**")
    for s in states:
        labs = ", ".join(sorted(labels.get(s, set()))) or "∅"
        nexts = ", ".join(sorted(succ[s])) or "—"
        lines.append(f"- {s}: L={{{labs}}}, succ={{{nexts}}}")
    lines.append("")
    lines.append("**Berechnung (Tableaux, bottom-up):**")
    lines.append("")

    result = ev(tree)
    lines.append("")
    lines.append(f"**Ergebnis: `{formula_str}` gilt in {fmt(result)}**")
    return result, lines


def _parse_ctl(tokens):
    """Recursive descent parser for CTL formulas."""
    pos = [0]

    def peek():
        while pos[0] < len(tokens) and tokens[pos[0]] == '':
            pos[0] += 1
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def consume(expected=None):
        tok = peek()
        if expected and tok != expected:
            raise ValueError(f"Erwartet '{expected}', bekommen '{tok}'")
        pos[0] += 1
        return tok

    def parse_formula():
        return parse_implies()

    def parse_implies():
        left = parse_or()
        if peek() == '->':
            consume('->')
            right = parse_implies()
            return ('implies', left, right)
        return left

    def parse_or():
        left = parse_and()
        if peek() == '|':
            consume('|')
            right = parse_or()
            return ('or', left, right)
        return left

    def parse_and():
        left = parse_unary()
        if peek() == '&':
            consume('&')
            right = parse_and()
            return ('and', left, right)
        return left

    def parse_unary():
        if peek() == '!':
            consume('!')
            return ('not', parse_unary())
        return parse_primary()

    def parse_primary():
        tok = peek()
        if tok is None:
            raise ValueError("Unerwartetes Ende der Formel")

        tok_up = tok.upper()

        if tok == '(':
            consume('(')
            f = parse_formula()
            consume(')')
            return f

        if tok_up in ('EX', 'AX', 'EF', 'AF', 'EG', 'AG'):
            consume(tok)
            inner = parse_primary()
            return (tok_up, inner)

        if tok_up == 'E' and pos[0] + 1 < len(tokens) and tokens[pos[0]+1] == '[':
            consume(tok)
            consume('[')
            phi = parse_formula()
            nxt = peek()
            if nxt is None or nxt.upper() != 'U':
                raise ValueError("Erwartet 'U' in E[phi U psi]")
            consume(nxt)
            psi = parse_formula()
            consume(']')
            return ('EU', phi, psi)

        if tok_up == 'A' and pos[0] + 1 < len(tokens) and tokens[pos[0]+1] == '[':
            consume(tok)
            consume('[')
            phi = parse_formula()
            nxt = peek()
            if nxt is None or nxt.upper() != 'U':
                raise ValueError("Erwartet 'U' in A[phi U psi]")
            consume(nxt)
            psi = parse_formula()
            consume(']')
            return ('AU', phi, psi)

        consume(tok)
        return ('atom', tok)

    result = parse_formula()
    if peek() is not None:
        raise ValueError(f"Unerwartetes Token nach Formel: '{peek()}'")
    return result


def _tokenize_ctl(formula_str):
    """Split a CTL formula string into tokens."""
    import re
    token_re = re.compile(r'->|\[|\]|[()!&|]|[A-Za-z][A-Za-z0-9_]*')
    return token_re.findall(formula_str)


def _parse_ltl(tokens):
    """Recursive descent parser for LTL formulas on paths (supports X,F,G,U)."""
    pos = [0]

    def peek():
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def consume(expected=None):
        tok = peek()
        if expected is not None and tok != expected:
            raise ValueError(f"Erwartet '{expected}', bekommen '{tok}'")
        pos[0] += 1
        return tok

    def parse_formula():
        return parse_implies()

    def parse_implies():
        left = parse_or()
        if peek() == '->':
            consume('->')
            right = parse_implies()
            return ('implies', left, right)
        return left

    def parse_or():
        left = parse_and()
        while peek() == '|':
            consume('|')
            right = parse_and()
            left = ('or', left, right)
        return left

    def parse_and():
        left = parse_until()
        while peek() == '&':
            consume('&')
            right = parse_until()
            left = ('and', left, right)
        return left

    def parse_until():
        left = parse_unary()
        while (peek() or '').upper() == 'U':
            consume(peek())
            right = parse_unary()
            left = ('U', left, right)
        return left

    def parse_unary():
        tok = peek()
        if tok == '!':
            consume('!')
            return ('not', parse_unary())
        if tok is not None and tok.upper() in ('X', 'F', 'G'):
            op = tok.upper()
            consume(tok)
            return (op, parse_unary())
        return parse_primary()

    def parse_primary():
        tok = peek()
        if tok is None:
            raise ValueError("Unerwartetes Ende der Formel")
        if tok == '(':
            consume('(')
            inner = parse_formula()
            consume(')')
            return inner
        if tok.upper() == 'U':
            raise ValueError("'U' braucht linken und rechten Operanden")
        consume(tok)
        return ('atom', tok)

    result = parse_formula()
    if peek() is not None:
        raise ValueError(f"Unerwartetes Token nach Formel: '{peek()}'")
    return result


def _ltl_check_lasso(labels_by_pos, loop_start):
    """
    Build evaluator for LTL over an ultimately periodic path (lasso).
    labels_by_pos: list[set[str]], positions 0..n-1
    next(n-1) = loop_start, otherwise next(i)=i+1
    """
    n = len(labels_by_pos)
    if n == 0:
        raise ValueError("Pfad darf nicht leer sein")
    if loop_start < 0 or loop_start >= n:
        raise ValueError(f"Loop-Start muss zwischen 0 und {n-1} liegen")

    positions = set(range(n))

    def next_pos(i):
        return i + 1 if i + 1 < n else loop_start

    def sat_atom(ap):
        return {i for i in range(n) if ap in labels_by_pos[i]}

    def sat_not(a_set):
        return positions - a_set

    def sat_and(a_set, b_set):
        return a_set & b_set

    def sat_or(a_set, b_set):
        return a_set | b_set

    def sat_implies(a_set, b_set):
        return sat_or(sat_not(a_set), b_set)

    def sat_X(a_set):
        return {i for i in range(n) if next_pos(i) in a_set}

    def sat_F(a_set):
        result = set(a_set)
        while True:
            new = result | sat_X(result)
            if new == result:
                return result
            result = new

    def sat_G(a_set):
        result = set(positions)
        while True:
            new = a_set & sat_X(result)
            if new == result:
                return result
            result = new

    def sat_U(phi_set, psi_set):
        result = set(psi_set)
        while True:
            new = psi_set | (phi_set & sat_X(result))
            if new == result:
                return result
            result = new

    def evaluate(node, steps):
        kind = node[0]
        if kind == 'atom':
            res = sat_atom(node[1])
            steps.append((f"atom({node[1]})", res))
            return res
        if kind == 'not':
            inner = evaluate(node[1], steps)
            res = sat_not(inner)
            steps.append(("NOT", res))
            return res
        if kind == 'and':
            a = evaluate(node[1], steps)
            b = evaluate(node[2], steps)
            res = sat_and(a, b)
            steps.append(("AND", res))
            return res
        if kind == 'or':
            a = evaluate(node[1], steps)
            b = evaluate(node[2], steps)
            res = sat_or(a, b)
            steps.append(("OR", res))
            return res
        if kind == 'implies':
            a = evaluate(node[1], steps)
            b = evaluate(node[2], steps)
            res = sat_implies(a, b)
            steps.append(("IMPLIES", res))
            return res
        if kind == 'X':
            inner = evaluate(node[1], steps)
            res = sat_X(inner)
            steps.append(("X", res))
            return res
        if kind == 'F':
            inner = evaluate(node[1], steps)
            res = sat_F(inner)
            steps.append(("F", res))
            return res
        if kind == 'G':
            inner = evaluate(node[1], steps)
            res = sat_G(inner)
            steps.append(("G", res))
            return res
        if kind == 'U':
            left = evaluate(node[1], steps)
            right = evaluate(node[2], steps)
            res = sat_U(left, right)
            steps.append(("U", res))
            return res
        raise ValueError(f"Unbekannter LTL-Operator: {kind}")

    return evaluate
