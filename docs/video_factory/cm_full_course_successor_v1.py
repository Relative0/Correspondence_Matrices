"""Build a source-only successor for the approved full-course review edits.

This module deliberately creates an additive delta package.  The delivered v2
foundation and v1 advanced packages are frozen and are never opened for write.
It creates revised visual states, scripts, companion exercises, and a runnable
code example.  It never reads credentials, calls a voice service, or encodes
replacement media.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from html import escape
from itertools import product
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "deep_series" / "cm_full_course_successor_v1"
sys.path.insert(0, str(HERE))

import cm_advanced_curriculum_v1 as advanced_source
import cm_tutorial_curriculum_v2 as foundation_source


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def find(lessons: list[dict], lesson_id: str) -> dict:
    return next(item for item in lessons if item["id"] == lesson_id)


def scene(lesson: dict, number: int) -> dict:
    return lesson["scenes"][number - 1]


def revise_curricula() -> tuple[list[dict], list[dict], dict[str, list[int]]]:
    """Apply editorial source changes while retaining the originals untouched."""
    foundation = deepcopy(foundation_source.LESSONS)
    advanced = deepcopy(advanced_source.LESSONS)
    changed: dict[str, list[int]] = {}

    def record(lesson_id: str, number: int) -> None:
        changed.setdefault(lesson_id, []).append(number)

    # CMR-02: These two exercises are deliberately guided checks.  That makes
    # supplied input facts legitimate rather than pretending they are hidden.
    l04 = find(foundation, "04_symbolic_implication")
    s = scene(l04, 10)
    s.update(
        title="Guided consistency check: implication at one input",
        text=(
            "Use the supplied input X equal to one and Y equal to zero. First "
            "evaluate not X or Y. Then use the true-first axes to locate the "
            "same input in the implication matrix. Check that the two methods "
            "agree before revealing the result."
        ),
        note="Guided check: compute ¬X∨Y and locate X=1, Y=0.",
        assessment_mode="guided_consistency_check",
    )
    record(l04["id"], 10)

    l07 = find(foundation, "07_compound_rule")
    s = scene(l07, 8)
    s.update(
        title="Your turn: evaluate this assignment",
        text=(
            "For W, X, Y, Z equal to zero, one, one, one, evaluate P and Q "
            "from their definitions. Then decide the implication and locate the "
            "matching row and column in the matrix. Explain why the direct rule "
            "calculation and the addressed entry agree."
        ),
        note="WXYZ=0111. Find P, Q, the output, and its addressed cell.",
        assessment_mode="independent_prediction",
    )
    record(l07["id"], 8)

    l10 = find(advanced, "10_transpose")
    s = scene(l10, 7)
    s.update(
        title="Your turn: predict the transposed operator",
        text=(
            "Transpose the displayed implication matrix once more. Track the "
            "zero from its current position, then name the bracketed operator "
            "you obtain and explain why every entry returns to its original "
            "coordinate."
        ),
        note="Predict the transposed operator from the moved zero.",
        assessment_mode="independent_prediction",
    )
    record(l10["id"], 7)

    l15 = find(advanced, "15_lm_factors")
    s = scene(l15, 7)
    s.update(
        text=(
            "We explicitly use entrywise AND for this factorization. If we read "
            "the juxtaposition as our AND-and-exclusive-or row-by-column product, "
            "the top-left entry becomes X and Y exclusive-or X and Y, which is "
            "zero. The two identical terms cancel. The surrounding source prose "
            "uses conjunction, but the displayed notation alone does not prove a "
            "unique multiplication convention."
        ),
        note="State the entrywise convention; compare it with the zero row-by-column product.",
        source_interpretation="explicit_entrywise_convention_not_unique_authorial_intent",
    )
    record(l15["id"], 7)

    l16 = find(advanced, "16_lm_measurement")
    s = scene(l16, 3)
    s.update(
        text=(
            "Use both entries in the first column. Pair X with X implies Y, and "
            "not X with not X implies Y. AND each pair, then exclusive-or the two "
            "products. They simplify to Y. The whole first column participates in "
            "this contraction."
        ),
        note="Both first-column cells and both bra entries produce Y.",
        full_column_highlight=0,
        intermediate_row="[Y, ?]",
    )
    record(l16["id"], 3)
    s = scene(l16, 4)
    s.update(
        text=(
            "Now use both entries in the second column. Pair X with X implies not "
            "Y, and not X with not X implies not Y. AND each pair, then "
            "exclusive-or the two products. They simplify to not Y, leaving the "
            "complete intermediate row [Y, not Y]."
        ),
        note="Both second-column cells and both bra entries produce ¬Y.",
        full_column_highlight=1,
        intermediate_row="[Y, ¬Y]",
    )
    record(l16["id"], 4)

    l18 = find(advanced, "18_larger_operations")
    s = scene(l18, 7)
    s.update(
        title="Guided consistency check: outer implication",
        text=(
            "For the supplied assignment W one, X zero, Y one, Z one, calculate "
            "F and G, then apply the outer implication. The component values are "
            "shown as a guided check: explain how the outer implication uses them "
            "and locate the corresponding row and column."
        ),
        note="Guided check: apply outer implication to the supplied F and G values.",
        assessment_mode="guided_consistency_check",
    )
    record(l18["id"], 7)

    l20 = find(advanced, "20_public_api")
    s = scene(l20, 1)
    s["cards"] = [
        {"label": "RUNNABLE IMPORTS", "lines": [
            "from cm_exprlib import Var, And, Or, Xor",
            "from cm_build import compile_expr_to_cm, eval_cm_boolean",
        ]},
        {"label": "EXPLANATORY RULE", "lines": [
            "A,B,C,D = [Var(i) for i in range(4)]",
            "rule = Xor(And(A,B), Or(C,D))",
        ]},
    ]
    s["note"] = "The displayed imports and setup are runnable as one fragment."
    record(l20["id"], 1)
    s = scene(l20, 4)
    s.update(
        text=(
            "For A one, B one, C zero, D zero, pass every repository name in an "
            "assignment dictionary. Row bits one-one give index three and column "
            "bits zero-zero give index zero. Store the lookup result, then assert "
            "that it is one. This is runnable Python, not equation notation."
        ),
        equations=[
            'assignment = {"x0":1,"x1":1,"x2":0,"x3":0}',
            "result = eval_cm_boolean(M, R, C, assignment, {})",
            "assert result == 1",
        ],
        note="Use a complete assignment and a runnable assertion.",
    )
    record(l20["id"], 4)
    s = scene(l20, 5)
    s.update(
        equations=[
            "expected = (a_bit & b_bit) ^ (c_bit | d_bit)",
            "assert result == expected",
        ],
        note="Keep scalar oracle bit names separate from assignment.",
    )
    record(l20["id"], 5)
    s = scene(l20, 6)
    s.update(
        title="Three representative balanced partitions",
        text=(
            "Here are three representative balanced partitions: A B over C D, A "
            "C over B D, and A D over B C. We keep A in the row group and retain "
            "the original order within each list. Swapping axes or changing list "
            "order produces other valid layouts. The example checks these three "
            "representatives across all sixteen assignments."
        ),
        equations=["AB / CD     AC / BD     AD / BC", "A stays in rows; list order stays original"],
        note="Three representative partitions; ordered swaps and permutations are also valid.",
        layout_count_convention="three_unordered_pairings_with_A_in_rows_and_original_list_order",
    )
    record(l20["id"], 6)
    s = scene(l20, 7)
    s.update(
        text=(
            "Import compilation and materialization from cm_ir. Compile the rule "
            "once, then materialize its node for each declared layout. Those arrays "
            "match direct public-wrapper construction. This distinguishes reusable "
            "preparation from the requested final matrix output."
        ),
        equations=[
            "from cm_ir import compile_expr, materialize_cm",
            "compiled = compile_expr(rule)",
            "M = materialize_cm(compiled.node, R, C, {})",
        ],
        note="Display the imports needed by every runnable fragment.",
    )
    record(l20["id"], 7)
    s = scene(l20, 9)
    s["note"] = "The three representative partitions retain the rule under their declared addressing."
    record(l20["id"], 9)

    l21 = find(advanced, "21_packed_outputs")
    s = scene(l21, 5)
    s.update(
        text=(
            "The packed integer has ten set bits, so the satisfying-assignment "
            "count is ten. The runnable helper bitset to bool array takes the "
            "packed integer and number of variables, then returns the same "
            "sixteen-entry vector as the scalar oracle. The earlier word unpack "
            "was explanatory shorthand, not an API call."
        ),
        equations=[
            "packed.bit_count() = 10",
            "vector = bitset_to_bool_array(packed, n_vars=4)",
        ],
        note="Label pseudocode separately; show the actual helper and signature for runnable code.",
    )
    record(l21["id"], 5)

    return foundation, advanced, changed


def matrix(name: str, values: list[list[str | int]], rows: list[str], cols: list[str], *,
           row_group: str, col_group: str, marks: list[tuple[int, int]] | None = None) -> dict:
    return {
        "kind": "matrix", "name": name, "values": values, "rows": rows, "cols": cols,
        "row_group": row_group, "col_group": col_group, "marks": marks or [],
    }


def panel(label: str, *lines: str) -> dict:
    return {"kind": "panel", "label": label, "lines": list(lines)}


def visual_specs() -> dict[str, dict]:
    """Replacement states.  Each state is complete enough to review in isolation."""
    implication = [[1, 0], [1, 1]]
    reverse = [[1, 1], [0, 1]]
    lm = [["X⇒Y", "X⇒¬Y"], ["¬X⇒Y", "¬X⇒¬Y"]]
    repo = [[0, 1, 1, 1], [0, 1, 1, 1], [0, 1, 1, 1], [1, 0, 0, 0]]
    gamma1 = [[1,1,0,1],[1,1,0,1],[1,0,1,0],[1,1,1,1]]
    gamma2 = [[1,1,0,1],[1,1,0,1],[0,0,1,0],[1,0,1,0]]
    tensor8 = [["ABCDEF" for _ in range(8)] for _ in range(8)]
    return {
        "04_symbolic_implication/10": {
            "title": "Guided consistency check: implication at one input",
            "subtitle": "CM FOUNDATIONS · GUIDED CHECK",
            "equations": ["X=1, Y=0", "¬X∨Y = ?     ⟨1|[⇒]|0⟩ = ?"],
            "cards": [panel("DO BOTH PATHS", "1. Evaluate ¬X∨Y", "2. Use X/Y true-first axes", "3. Compare before reveal")],
            "takeaway": "A guided consistency check supplies the case, not the result.",
        },
        "07_compound_rule/08": {
            "title": "Your turn: evaluate this assignment",
            "subtitle": "CM FOUNDATIONS · YOUR TURN",
            "equations": ["WXYZ = 0111", "P = ?     Q = ?     P⇒Q = ?"],
            "cards": [panel("FIRST: DIRECT RULE", "Evaluate P and Q", "Then evaluate P⇒Q"), panel("THEN: ADDRESS", "Rows WY, columns XZ", "Locate the same assignment")],
            "takeaway": "Explain why the direct rule and addressed matrix entry agree.",
        },
        "10_transpose/03": {
            "title": "Transpose: exchange row and column indices",
            "subtitle": "CM ADVANCED · AXES STAY EXPLICIT",
            "equations": ["Tᵀ[j,i] = T[i,j]", "[⇒]ᵀ = [⇐]"],
            "cards": [
                matrix("[⇒]", implication, ["1","0"], ["1","0"], row_group="row input X · true-first", col_group="column input Y · true-first", marks=[(0,1)]),
                matrix("[⇐]", reverse, ["1","0"], ["1","0"], row_group="row input X · true-first", col_group="column input Y · true-first", marks=[(1,0)]),
            ],
            "takeaway": "The values move; labels state which input each axis still represents.",
        },
        "10_transpose/07": {
            "title": "Your turn: predict the transposed operator",
            "subtitle": "CM ADVANCED · YOUR TURN",
            "equations": ["([⇒]ᵀ)ᵀ = ?"],
            "cards": [matrix("Current matrix", reverse, ["1","0"], ["1","0"], row_group="row input X · true-first", col_group="column input Y · true-first", marks=[(1,0)]), panel("PREDICT", "Track the zero", "Name the resulting bracketed operator", "Explain why every coordinate returns")],
            "takeaway": "Infer the operator from the moved entry; no answer name is shown.",
        },
        "15_lm_factors/07": {
            "title": "Why the multiplication convention matters",
            "subtitle": "CM ADVANCED · SOURCE INTERPRETATION",
            "equations": ["Entrywise: X∧Y", "Row-by-column: (X∧Y) ⇕ (X∧Y) = 0"],
            "cards": [panel("EXPLICIT CONVENTION", "Use entrywise AND for this factorization", "It reconstructs the logical matrix"), panel("COUNTEREXAMPLE", "Row-by-column product duplicates terms", "Identical terms cancel under ⇕")],
            "takeaway": "The entrywise convention is stated; notation alone does not prove unique source intent.",
        },
        "16_lm_measurement/03": {
            "title": "Expand the first intermediate entry",
            "subtitle": "CM ADVANCED · FULL COLUMN CONTRACTION",
            "equations": ["X∧(X⇒Y) ⇕ ¬X∧(¬X⇒Y)", "= (X∧Y) ⇕ (¬X∧Y) = Y", "⟨X|M = [Y, ?]"],
            "cards": [panel("BRA", "⟨X| = [X, ¬X]"), matrix("M₍X⇒Y₎", lm, ["X","¬X"], ["Y","¬Y"], row_group="bra entries", col_group="remaining ket choice", marks=[(0,0),(1,0)]), panel("PAIR BOTH TERMS", "X with X⇒Y", "¬X with ¬X⇒Y", "AND pairs; XOR products")],
            "takeaway": "The complete active column, not one selected cell, produces Y.",
        },
        "16_lm_measurement/04": {
            "title": "Expand the second intermediate entry",
            "subtitle": "CM ADVANCED · FULL COLUMN CONTRACTION",
            "equations": ["X∧(X⇒¬Y) ⇕ ¬X∧(¬X⇒¬Y)", "= (X∧¬Y) ⇕ (¬X∧¬Y) = ¬Y", "⟨X|M = [Y, ¬Y]"],
            "cards": [panel("BRA", "⟨X| = [X, ¬X]"), matrix("M₍X⇒Y₎", lm, ["X","¬X"], ["Y","¬Y"], row_group="bra entries", col_group="remaining ket choice", marks=[(0,1),(1,1)]), panel("PAIR BOTH TERMS", "X with X⇒¬Y", "¬X with ¬X⇒¬Y", "AND pairs; XOR products")],
            "takeaway": "The complete second column produces ¬Y; the intermediate row is [Y, ¬Y].",
        },
        "16_lm_measurement/07": {
            "title": "Read all four matched relations",
            "subtitle": "CM ADVANCED · MATCHED SELECTORS",
            "equations": ["⟨X|M₍X⇒Y₎|Y⟩ = 1", "⟨X|M₍X⇒Y₎|¬Y⟩ = 0"],
            "cards": [matrix("M₍X⇒Y₎", lm, ["X","¬X"], ["Y","¬Y"], row_group="bra selector formula", col_group="ket selector formula"), panel("READ THE TYPE", "Matched formulas recover coefficients", "An unrelated ket requires recalculation")],
            "takeaway": "Axis formulas identify selector meanings; 1/0 are results, not the defining labels.",
        },
        "17_larger_tensors/04": {
            "title": "Add one more complete factor",
            "subtitle": "CM ADVANCED · 8×8 OVERVIEW",
            "equations": ["M_AB ⊗ M_CD ⊗ M_EF", "Rows: (A,C,E)     Columns: (B,D,F)"],
            "cards": [matrix("8×8 tensor overview", tensor8, ["111","110","101","100","011","010","001","000"], ["111","110","101","100","011","010","001","000"], row_group="row variables A,C,E · true-first", col_group="column variables B,D,F · true-first"), panel("NEXT STATE", "This is an overview", "The next state enlarges one addressed entry")],
            "takeaway": "Keep group labels persistent; do not require reading every dense formula at once.",
        },
        "18_larger_operations/05": {
            "title": "Combine matching assignments",
            "subtitle": "CM ADVANCED · ALIGNED ENTRYWISE OPERATION",
            "equations": ["H = F⇒G", "Γ[i,j] = Γ₁[i,j] ⇒ Γ₂[i,j]"],
            "cards": [
                matrix("Γ₁", gamma1, ["11","10","01","00"], ["11","10","01","00"], row_group="row variables W,Y · true-first", col_group="column variables X,Z · true-first", marks=[(1,2)]),
                matrix("Γ₂", gamma2, ["11","10","01","00"], ["11","10","01","00"], row_group="row variables W,Y · true-first", col_group="column variables X,Z · true-first", marks=[(1,2)]),
            ],
            "takeaway": "Entrywise implication is valid only because both cells denote the same WXYZ assignment.",
        },
        "18_larger_operations/07": {
            "title": "Guided consistency check: outer implication",
            "subtitle": "CM ADVANCED · GUIDED CHECK",
            "equations": ["WXYZ=1011", "F=0     G=0     F⇒G = ?"],
            "cards": [panel("SUPPLIED COMPONENTS", "Use the shown F and G values", "Apply outer implication"), panel("ADDRESS", "Rows WY=11", "Columns XZ=01", "Explain the matching cell")],
            "takeaway": "This is a guided outer-implication check, not an uncued prediction.",
        },
        "20_public_api/01": {
            "title": "Build a small example you can run",
            "subtitle": "CM ADVANCED · RUNNABLE PYTHON",
            "equations": ["A,B,C,D = [Var(i) for i in range(4)]", "rule = Xor(And(A,B), Or(C,D))"],
            "cards": [panel("IMPORTS", "from cm_exprlib import Var, And, Or, Xor", "from cm_build import compile_expr_to_cm, eval_cm_boolean"), panel("RULE", "Use expression constructors", "Do not use Python 'and'/'or' on expression objects")],
            "takeaway": "The displayed imports and setup form a runnable fragment.",
        },
        "20_public_api/03": {
            "title": "Declare the rows and columns",
            "subtitle": "CM ADVANCED · DECLARED REPOSITORY LAYOUT",
            "equations": ["R = [\"x0\",\"x1\"]     C = [\"x2\",\"x3\"]", "M = compile_expr_to_cm(rule, R, C, {})"],
            "cards": [matrix("M", repo, ["00","01","10","11"], ["00","01","10","11"], row_group="row variables x0,x1 · false-first", col_group="column variables x2,x3 · false-first")],
            "takeaway": "Variable lists define membership, order and false-first physical addressing.",
        },
        "20_public_api/04": {
            "title": "Make a complete assignment explicit",
            "subtitle": "CM ADVANCED · RUNNABLE PYTHON",
            "equations": ["assignment = {\"x0\":1, \"x1\":1, \"x2\":0, \"x3\":0}", "result = eval_cm_boolean(M, R, C, assignment, {})", "assert result == 1"],
            "cards": [panel("ADDRESS", "row 11₂ = 3", "column 00₂ = 0"), panel("RESULT", "The assert checks the returned value", "Equation-style function calls are not code")],
            "takeaway": "Use a complete assignment and an explicit runnable assertion.",
        },
        "20_public_api/05": {
            "title": "Check with an independent scalar oracle",
            "subtitle": "CM ADVANCED · RUNNABLE PYTHON",
            "equations": ["expected = (a_bit & b_bit) ^ (c_bit | d_bit)", "assert result == expected"],
            "cards": [panel("ORACLE", "Plain scalar bit operations", "Names do not shadow assignment"), panel("COVERAGE", "Check all 16 inputs", "Compare lookup with oracle")],
            "takeaway": "The scalar oracle is independent of matrix addressing.",
        },
        "20_public_api/06": {
            "title": "Three representative balanced partitions",
            "subtitle": "CM ADVANCED · LAYOUT CONVENTION",
            "equations": ["AB / CD     AC / BD     AD / BC", "A remains in rows; original list order is retained"],
            "cards": [panel("REPRESENTATIVES", "3 unordered pairings", "3 × 16 = 48 checked lookups"), panel("OTHER VALID LAYOUTS", "Swap axes or permute a list", "Those change addresses, not the rule")],
            "takeaway": "The three examples are representatives under a stated layout-count convention.",
        },
        "20_public_api/07": {
            "title": "Reuse compilation when appropriate",
            "subtitle": "CM ADVANCED · RUNNABLE PYTHON",
            "equations": ["from cm_ir import compile_expr, materialize_cm", "compiled = compile_expr(rule)", "M = materialize_cm(compiled.node, R, C, {})"],
            "cards": [panel("PREPARATION", "Compile graph once", "Reuse compiled.node"), panel("OUTPUT", "Materialize each declared layout", "Compare direct wrapper output")],
            "takeaway": "Displayed imports make the code fragment reproducible.",
        },
        "20_public_api/09": {
            "title": "Answer: row three, column zero, value one",
            "subtitle": "CM ADVANCED · REPRESENTATIVE PARTITION",
            "equations": ["row=11₂=3     column=00₂=0", "(1∧0)⇕(1∨0) = 0⇕1 = 1"],
            "cards": [panel("DECLARED LAYOUT", "Rows [A,C]", "Columns [B,D]"), panel("CHECK", "This representative preserves the rule", "Other ordered layouts are also valid")],
            "takeaway": "Addressing changes under a declared layout; the Boolean rule does not.",
        },
        "21_packed_outputs/05": {
            "title": "Recover a count or unpack the vector",
            "subtitle": "CM ADVANCED · RUNNABLE HELPER",
            "equations": ["packed.bit_count() = 10", "vector = bitset_to_bool_array(packed, n_vars=4)"],
            "cards": [panel("ACTUAL API", "from bitset_backend import bitset_to_bool_array", "Helper returns truth-vector order"), panel("RESULT", "packed = 7918", "16 outputs match scalar oracle")],
            "takeaway": "“Unpack” is explanatory prose; the helper name and signature are shown for code.",
        },
    }


def render_card(card: dict) -> str:
    if card["kind"] == "panel":
        lines = "".join(f"<div>{escape(line)}</div>" for line in card["lines"])
        return f'<section class="card panel"><h2>{escape(card["label"])}</h2>{lines}</section>'
    header = "<tr><th></th>" + "".join(f"<th>{escape(str(x))}</th>" for x in card["cols"]) + "</tr>"
    marks = {tuple(x) for x in card.get("marks", [])}
    body = []
    for i, row in enumerate(card["values"]):
        cells = "".join(
            f'<td class="{"selected" if (i, j) in marks else ""}">{escape(str(value))}</td>'
            for j, value in enumerate(row)
        )
        body.append(f"<tr><th>{escape(str(card['rows'][i]))}</th>{cells}</tr>")
    n = len(card["values"])
    return (
        f'<section class="card matrix-card size-{n}"><h2>{escape(card["name"])}</h2>'
        f'<div class="axis">Rows: {escape(card["row_group"])}<br>Columns: {escape(card["col_group"])}</div>'
        f'<table><thead>{header}</thead><tbody>{"".join(body)}</tbody></table></section>'
    )


def render_page(spec: dict) -> str:
    cards = "".join(render_card(card) for card in spec["cards"])
    equations = "".join(f"<div>{escape(item)}</div>" for item in spec["equations"])
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{escape(spec["title"])}</title><style>
*{{box-sizing:border-box}} body{{margin:0;width:1280px;height:720px;overflow:hidden;background:#08131b;color:#edf7fb;font-family:Arial,sans-serif}}
header{{height:100px;padding:20px 42px;border-bottom:2px solid #3e6c78}} .subtitle{{color:#78d8e4;font-size:15px;font-weight:bold;letter-spacing:1px}} h1{{font-size:31px;margin:7px 0}}
main{{padding:18px 42px}} .equations{{border-left:4px solid #b8a5ed;background:#14212e;padding:10px 17px;font:25px Consolas,monospace;line-height:1.3}}
.cards{{display:flex;gap:18px;margin-top:18px;height:370px}} .card{{flex:1;min-width:0;border-top:3px solid #68d4e1;background:#10212b;padding:14px;overflow:hidden}} h2{{font-size:20px;color:#87ddeb;text-align:center;margin:0 0 13px}} .panel div{{font-size:23px;line-height:1.38;margin:8px 3px}}
.axis{{font-size:18px;line-height:1.3;color:#b7dce5;margin:0 0 8px}} table{{width:100%;border-spacing:4px;text-align:center;border-collapse:separate;font-family:Consolas,monospace}} th{{font-size:20px;color:#c5e6ed;font-weight:500}} td{{font-size:27px;background:#142f3a;border:1px solid #456671;padding:9px 2px;height:45px;white-space:nowrap}} td.selected{{background:#42375d;border:3px solid #e0c9ff;color:#fff}} .size-8 th{{font-size:16px}} .size-8 td{{font-size:12px;height:25px;padding:2px 0}} .takeaway{{position:absolute;left:42px;right:42px;bottom:52px;border:2px solid #b9a2eb;background:#182333;padding:10px 15px;font-size:21px}}
</style></head><body><header><div class="subtitle">{escape(spec["subtitle"])}</div><h1>{escape(spec["title"])}</h1></header><main><div class="equations">{equations}</div><div class="cards">{cards}</div></main><div class="takeaway">{escape(spec["takeaway"])}</div></body></html>'''


def companion_markdown() -> str:
    return '''# Independent construction and transfer companions

These companion exercises implement CMR-01 without changing the frozen lesson media. They are intentionally longer than the original five-second checks. Keep each answer key separate from the question page.

## After lesson 9 — paper/layout companion

**Question.** A system accepts when A or B is true, provided C is false. Write the Boolean rule. Use rows `[A]` and columns `[B,C]` in false-first order. Construct the full 2×4 CM. Predict the result for `ABC=101`, then locate it. Next use rows `[A,B]` and columns `[C]`; show where the same assignment moves. Finally verify every one of the eight assignments independently from the Boolean rule.

**Answer key.** `F=(A∨B)∧¬C`. With rows `[A]`, columns `[B,C]`, the matrix is `[[0,0,1,0],[1,0,1,0]]`; `101` maps to row 1, column 1 and returns 0. With rows `[A,B]`, columns `[C]`, it is `[[0,0],[1,0],[1,0],[1,0]]`; `101` maps to row 2, column 1 and still returns 0. There are three accepted assignments.

## After lesson 23 — executable transfer companion

**Question.** Starting from the same specification, create a fresh expression with the public API, choose a different valid row/column split, materialize it, and compare every entry with a scalar oracle. Then change OR to XOR and repeat the complete check. Explain which cells and count change.

**Answer key.** The XOR variant is `G=(A⇕B)∧¬C`. Under rows `[A]`, columns `[B,C]`, its matrix is `[[0,0,1,0],[1,0,0,0]]` and its accepted-count is 2. The supplied `examples/successor_course_examples.py` checks both rules over all eight assignments.

## Use in a learner session

Do not show either answer key or the matrix while collecting the first response. Record the rule, chosen layout, address, explanation, time and any hint/replay. A later 24–72 hour XOR transfer attempt can assess retention; no study result is claimed by this package.
'''


def companion_html(title: str, body: str) -> str:
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>{escape(title)}</title><style>
body{{max-width:920px;margin:40px auto;background:#08131b;color:#edf7fb;font:19px/1.5 Arial,sans-serif;padding:28px}} h1{{color:#87ddeb}} code{{background:#14212e;padding:2px 5px}} .grid{{border:2px dashed #78d8e4;padding:70px 15px;text-align:center;color:#b7dce5}} .rule{{background:#14212e;padding:18px;border-left:4px solid #b8a5ed}}
</style><h1>{escape(title)}</h1>{body}</html>'''


def write_readme() -> None:
    write(OUT / "README.md", '''# CM full-course successor v1 — source delta

This additive package implements the review recommendations in `cm_full_course_panel_review_v1` without changing either frozen delivery. It contains revised successor scripts, reviewable replacement visual states, an independent companion after lessons 9 and 23, and a runnable code example. Its scope is CMR-01 through CMR-07; CMR-08 remains deliberately deferred because it calls for preserving the foundation-arrow decision.

No paid service, voice synthesis, `.env`/secret access, upload, publishing, commit, push, automation or production-media overwrite was used. Existing narration and media remain the delivery truth. Several revised spoken paragraphs and captions are authored here but cannot be aligned/encoded until a separately authorized narration decision is made. The local browser policy also blocked previewing `file:` replacement states, so the HTML is structurally validated but still needs a permitted 640×360 rendered review before media sign-off; no workaround was attempted.

## Implemented changes

| Finding | Implemented successor work |
|---|---|
| CMR-01 | Separate paper/layout and executable transfer companions, answer keys, independent exhaustive checks |
| CMR-02 | Neutral independent prompts for L7/L10; explicit guided-check labels for L4/L18 |
| CMR-03 | L16 full-column states with both active cells, complete bra and intermediate row |
| CMR-04 | Persistent row/column variable-group labels and enlarged headers in all affected replacement states |
| CMR-05 | Runnable L20 imports/result/assertion/reuse fragments; actual L21 unpack helper; executable example |
| CMR-06 | L20 representative-layout wording and 24 ordered-layout verification |
| CMR-07 | L15 wording identifies entrywise convention without asserting unique authorial intent |
| CMR-08 | Deferred exactly as directed; frozen foundation glyphs were not regenerated |

Open [CHANGELOG.md](CHANGELOG.md) for scene-level source changes, [NARRATION_AND_CAPTION_GATE.md](NARRATION_AND_CAPTION_GATE.md) for the only remaining media dependency, [COMPANION_CHECKPOINTS.md](COMPANION_CHECKPOINTS.md) for the new assessment material, and [VALIDATION.md](VALIDATION.md) for checks.
''')


def write_gate() -> None:
    write(OUT / "NARRATION_AND_CAPTION_GATE.md", '''# Narration and caption gate

The revised texts for L7, L10, L15, L16, L18, L20 and L21 are stored in `CURRICULUM_SUCCESSOR_V1.json` and their delta scripts. Existing MP3/WAV/caption timings cannot be reused for altered paragraphs without misleading timing or saying obsolete wording. No synthesis or caption realignment was performed.

The exact remaining external action is voice generation for the changed lessons, followed by subtitle alignment, local assembly and perceptual listening. It has a monetary/service effect and therefore requires separate authorization. This package is otherwise ready for that step: no content decision, mathematical correction or code design is left open.

Title-only/guided labels could be visually prototyped with existing audio, but the successor intentionally does not encode mismatched audio and visuals. Human listening, preferred-player captions and chapter navigation remain acceptance checks after any future encode.
''')


def write_changelog(foundation: list[dict], advanced: list[dict], changed: dict[str, list[int]]) -> None:
    records = {item["id"]: item for item in foundation + advanced}
    lines = ["# Implemented change log", "", "All scene text below is successor source. Frozen scripts and media are unchanged.", ""]
    for lesson_id in sorted(changed):
        item = records[lesson_id]
        lines.extend([f"## {lesson_id}", ""])
        for number in changed[lesson_id]:
            s = scene(item, number)
            lines.extend([
                f"### Scene {number}: {s['title']}", "", s["text"], "",
                f"**Visual takeaway:** {s['note']}", "",
            ])
    lines.extend([
        "## Companion additions", "",
        "- After L9: paper/layout independent construction checkpoint.",
        "- After L23: public-API transfer checkpoint and XOR variant.",
        "",
        "## Deferred", "",
        "- CMR-08: no change to the foundation legacy arrows. The decision to preserve those frozen historical files is implemented by leaving them untouched.",
    ])
    write(OUT / "CHANGELOG.md", "\n".join(lines))


def write_example() -> None:
    write(OUT / "examples" / "successor_course_examples.py", '''"""Runnable checks used by the successor L20/L21 panels and CMR-01 companions."""
from itertools import permutations, product
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from bitset_backend import bitset_to_bool_array
from cm_build import compile_expr_to_cm, eval_cm_boolean
from cm_exprlib import And, Or, Var, Xor
from cm_ir import compile_expr, materialize_cm


def rule_value(a_bit, b_bit, c_bit, d_bit):
    return (a_bit & b_bit) ^ (c_bit | d_bit)


def all_ordered_balanced_layouts():
    A, B, C, D = [Var(i) for i in range(4)]
    rule = Xor(And(A, B), Or(C, D))
    names = ["x0", "x1", "x2", "x3"]
    compiled = compile_expr(rule)
    checks = 0
    for order in permutations(names):
        rows, columns = list(order[:2]), list(order[2:])
        direct = compile_expr_to_cm(rule, rows, columns, {})
        reused = materialize_cm(compiled.node, rows, columns, {})
        assert direct.tolist() == reused.tolist()
        for bits in product((0, 1), repeat=4):
            assignment = dict(zip(names, bits))
            result = eval_cm_boolean(direct, rows, columns, assignment, {})
            expected = rule_value(*bits)
            assert result == expected
            checks += 1
    assert checks == 24 * 16
    return checks


def companion_rule_checks():
    standard = lambda a, b, c: (a | b) & (1 - c)
    transfer = lambda a, b, c: (a ^ b) & (1 - c)
    m_a_bc = [[standard(a, b, c) for b, c in product((0, 1), repeat=2)] for a in (0, 1)]
    m_ab_c = [[standard(a, b, c) for c in (0, 1)] for a, b in product((0, 1), repeat=2)]
    xor_a_bc = [[transfer(a, b, c) for b, c in product((0, 1), repeat=2)] for a in (0, 1)]
    assert m_a_bc == [[0, 0, 1, 0], [1, 0, 1, 0]]
    assert m_ab_c == [[0, 0], [1, 0], [1, 0], [1, 0]]
    assert xor_a_bc == [[0, 0, 1, 0], [1, 0, 0, 0]]
    assert sum(sum(row) for row in m_a_bc) == 3
    assert sum(sum(row) for row in xor_a_bc) == 2
    return m_a_bc, m_ab_c, xor_a_bc


def packed_helper_check():
    vector = bitset_to_bool_array(7918, n_vars=4)
    assert vector.tolist() == [0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0]
    assert int(vector.sum()) == 10
    return vector


if __name__ == "__main__":
    print({
        "ordered_layout_assignment_checks": all_ordered_balanced_layouts(),
        "companion_matrices": companion_rule_checks(),
        "packed_vector": packed_helper_check().tolist(),
    })
''')
    write(OUT / "examples" / "README.md", '''# Successor example

Run from the repository root:

```powershell
.venv/Scripts/python.exe -B -X utf8 docs/video_factory/deep_series/cm_full_course_successor_v1/examples/successor_course_examples.py
```

This file is intentionally independent of the frozen course companion. It demonstrates the exact imports and helper signature displayed in the successor L20/L21 visual states, checks all 24 ordered balanced layouts, and validates both new three-bit companion rules.
''')


def write_visuals() -> None:
    specs = visual_specs()
    for key, spec in specs.items():
        lesson_id, scene_number = key.split("/")
        write(OUT / "visual_replacements" / lesson_id / f"scene_{scene_number.zfill(2)}.html", render_page(spec))
    write(OUT / "VISUAL_REPLACEMENTS.json", json.dumps(specs, ensure_ascii=False, indent=2))


def write_companions() -> None:
    write(OUT / "COMPANION_CHECKPOINTS.md", companion_markdown())
    write(OUT / "companions" / "after_lesson_09_question.html", companion_html(
        "After lesson 9: construct a new CM",
        '<p>A system accepts when A or B is true, provided C is false.</p><div class="rule">Write the rule. Use rows <code>[A]</code> and columns <code>[B,C]</code> in false-first order. Build the full 2×4 CM, predict <code>101</code>, then show where the same input moves under rows <code>[A,B]</code> and columns <code>[C]</code>.</div><div class="grid">Draw the 2×4 matrix here. Do not reveal its entries yet.</div>'
    ))
    write(OUT / "companions" / "after_lesson_23_question.html", companion_html(
        "After lesson 23: code and transfer",
        '<p>Create the same three-bit rule through the public API, choose an alternate layout, and check all eight inputs against a scalar oracle. Then change OR to XOR and repeat.</p><div class="grid">Keep the oracle, matrix, answer count and explanation separate until after the first attempt.</div>'
    ))
    write(OUT / "companions" / "answer_key.md", companion_markdown())


def write_scripts(foundation: list[dict], advanced: list[dict], changed: dict[str, list[int]]) -> None:
    records = {item["id"]: item for item in foundation + advanced}
    serializable = {
        lesson_id: {
            "source": "foundation_v2" if int(lesson_id[:2]) < 10 else "advanced_v1",
            "scenes": [{"scene_number": n, **scene(records[lesson_id], n)} for n in numbers],
        }
        for lesson_id, numbers in changed.items()
    }
    write(OUT / "CURRICULUM_SUCCESSOR_V1.json", json.dumps(serializable, ensure_ascii=False, indent=2))
    for lesson_id, entry in serializable.items():
        lines = [f"# {lesson_id} successor script", "", f"Frozen source: {entry['source']}. This file contains only replacement scenes.", ""]
        for index, state in zip(changed[lesson_id], entry["scenes"]):
            lines.extend([f"## Scene {index}: {state['title']}", "", state["text"], "", f"Visual takeaway: {state['note']}", ""])
        write(OUT / "script_replacements" / lesson_id / "SCRIPT_DELTA_V1.md", "\n".join(lines))


def write_validation_notes() -> None:
    write(OUT / "VALIDATION.md", '''# Successor validation

Run the local checks after building:

```powershell
.venv/Scripts/python.exe -B -X utf8 docs/video_factory/cm_full_course_successor_v1/validate_successor_v1.py
.venv/Scripts/python.exe -B -X utf8 docs/video_factory/deep_series/cm_full_course_successor_v1/examples/successor_course_examples.py
```

The validation verifies that frozen-package hashes remain unchanged, every required CMR delta is present, visual replacement HTML is structurally complete, revised code examples compile and run, the 24 ordered balanced layouts yield 384 scalar-oracle checks, and all companion answer keys are correct. Browser policy blocked a local `file:` preview, so this is not a rendered visual QA result.

It cannot validate rendered small-player legibility, audio, subtitle alignment, voice consistency, preferred-player captions, chapter interaction or learner outcomes. Those remain human checks after any separately authorized narration and assembly work.
''')


def manifest() -> None:
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "IMPLEMENTATION_MANIFEST_V1.json")
    data = {
        "version": 1,
        "purpose": "source-only successor delta for CM full-course review recommendations",
        "files": [{"path": str(path.relative_to(OUT)).replace("\\", "/"), "sha256": digest(path), "bytes": path.stat().st_size} for path in files],
        "paid_or_external_actions": [],
        "frozen_delivery_mutations": [],
    }
    write(OUT / "IMPLEMENTATION_MANIFEST_V1.json", json.dumps(data, ensure_ascii=False, indent=2))


def build() -> None:
    if OUT.exists():
        raise RuntimeError(f"Successor package already exists: {OUT}. Refuse to overwrite it.")
    foundation, advanced, changed = revise_curricula()
    write_readme()
    write_gate()
    write_changelog(foundation, advanced, changed)
    write_scripts(foundation, advanced, changed)
    write_visuals()
    write_companions()
    write_example()
    write_validation_notes()
    manifest()
    print(json.dumps({"out": str(OUT), "changed_lessons": sorted(changed), "replacement_scenes": sum(map(len, changed.values())), "visual_states": len(visual_specs())}, ensure_ascii=False))


def refresh() -> None:
    """Refresh generated code/docs after an additive builder correction only."""
    if not OUT.is_dir():
        raise RuntimeError("Build the successor before refreshing it.")
    write_example()
    write_validation_notes()
    manifest()
    print(json.dumps({"out": str(OUT), "refreshed": ["examples", "validation", "manifest"]}, ensure_ascii=False))


if __name__ == "__main__":
    {"build": build, "refresh": refresh}[sys.argv[1] if len(sys.argv) > 1 else "build"]()
