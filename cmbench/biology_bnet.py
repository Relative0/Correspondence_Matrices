"""Bounded, non-evaluating parser for Biodivine `.bnet` update functions."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
import re


TOKEN = re.compile(r"\s*([A-Za-z_][A-Za-z0-9_.:-]*|[01]|[!&|()])")


@dataclass(frozen=True)
class BNetFunction:
    target: str
    expression: tuple
    regulators: tuple[str, ...]


class _Parser:
    def __init__(self, text: str, *, max_tokens: int = 2_000_000):
        self.tokens = []
        position = 0
        while position < len(text):
            match = TOKEN.match(text, position)
            if match is None:
                raise ValueError("invalid BNet expression token")
            self.tokens.append(match.group(1))
            position = match.end()
            if len(self.tokens) > max_tokens:
                raise ValueError("BNet expression token limit exceeded")

    def parse(self) -> tuple:
        if not self.tokens:
            raise ValueError("empty BNet expression")
        precedence = {"|": 1, "&": 2, "!": 3}
        operators: list[str] = []
        postfix: list[str] = []
        expect_operand = True
        for token in self.tokens:
            if token not in {"!", "&", "|", "(", ")"}:
                if not expect_operand:
                    raise ValueError("adjacent BNet operands")
                postfix.append(token)
                expect_operand = False
            elif token == "!":
                if not expect_operand:
                    raise ValueError("unexpected BNet negation")
                operators.append(token)
            elif token == "(":
                if not expect_operand:
                    raise ValueError("implicit BNet conjunction is forbidden")
                operators.append(token)
            elif token == ")":
                if expect_operand:
                    raise ValueError("empty or incomplete BNet parenthesis")
                while operators and operators[-1] != "(":
                    postfix.append(operators.pop())
                if not operators:
                    raise ValueError("unmatched BNet parenthesis")
                operators.pop()
                while operators and operators[-1] == "!":
                    postfix.append(operators.pop())
            else:
                if expect_operand:
                    raise ValueError("unexpected BNet binary operator")
                while operators and operators[-1] != "(" and precedence[operators[-1]] >= precedence[token]:
                    postfix.append(operators.pop())
                operators.append(token)
                expect_operand = True
        if expect_operand:
            raise ValueError("incomplete BNet expression")
        while operators:
            operator = operators.pop()
            if operator == "(":
                raise ValueError("unclosed BNet parenthesis")
            postfix.append(operator)

        stack: list[tuple] = []
        for token in postfix:
            if token == "!":
                if not stack:
                    raise ValueError("incomplete BNet negation")
                stack.append(("not", stack.pop()))
            elif token in {"&", "|"}:
                if len(stack) < 2:
                    raise ValueError("incomplete BNet binary expression")
                right, left = stack.pop(), stack.pop()
                kind = "and" if token == "&" else "or"
                children = (*left[1:], right) if left[0] == kind else (left, right)
                stack.append((kind, *children))
            else:
                stack.append(("const", int(token)) if token in {"0", "1"} else ("var", token))
        if len(stack) != 1:
            raise ValueError("invalid BNet expression")
        return stack[0]


def _variables(expression: tuple) -> set[str]:
    output: set[str] = set()
    pending = [expression]
    while pending:
        node = pending.pop()
        if node[0] == "var":
            output.add(node[1])
        elif node[0] != "const":
            pending.extend(node[1:])
    return output


def evaluate_bnet(expression: tuple, values: dict[str, int | bool]) -> bool:
    results: dict[int, bool] = {}
    pending = [(expression, False)]
    while pending:
        node, visited = pending.pop()
        kind = node[0]
        if kind == "var":
            if node[1] not in values:
                raise ValueError("missing BNet regulator value")
            results[id(node)] = bool(values[node[1]])
        elif kind == "const":
            results[id(node)] = bool(node[1])
        elif not visited:
            if kind not in {"not", "and", "or"}:
                raise ValueError("unknown BNet expression node")
            pending.append((node, True))
            pending.extend((child, False) for child in reversed(node[1:]))
        elif kind == "not":
            results[id(node)] = not results[id(node[1])]
        elif kind == "and":
            results[id(node)] = all(results[id(child)] for child in node[1:])
        else:
            results[id(node)] = any(results[id(child)] for child in node[1:])
    return results[id(expression)]


def parse_bnet(text: str, *, max_bytes: int = 16 << 20, max_functions: int = 16384,
               max_expression_chars: int = 1 << 20) -> tuple[BNetFunction, ...]:
    if not isinstance(text, str) or not 0 < len(text.encode("utf-8")) <= max_bytes:
        raise ValueError("BNet input outside byte limit")
    lines = text.splitlines()
    if not lines or lines[0].strip().lower() != "targets,factors":
        raise ValueError("BNet header must be targets,factors")
    functions = []
    seen = set()
    for number, raw in enumerate(lines[1:], 2):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "," not in line:
            raise ValueError(f"BNet row {number} lacks comma")
        target, source = (part.strip() for part in line.split(",", 1))
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.:-]*", target) or target in seen:
            raise ValueError("invalid or duplicate BNet target")
        if not source or len(source) > max_expression_chars:
            raise ValueError("BNet expression outside character limit")
        expression = _Parser(source).parse()
        regulators = tuple(sorted(_variables(expression)))
        functions.append(BNetFunction(target, expression, regulators))
        seen.add(target)
        if len(functions) > max_functions:
            raise ValueError("BNet function count exceeds limit")
    if not functions:
        raise ValueError("BNet has no update functions")
    return tuple(functions)


def undeclared_bnet_regulators(functions: tuple[BNetFunction, ...]) -> tuple[str, ...]:
    """Return regulators that have no update function in this BNet model."""
    targets = {function.target for function in functions}
    return tuple(sorted(set().union(*(set(function.regulators) for function in functions)) - targets))


def require_closed_bnet(functions: tuple[BNetFunction, ...]) -> None:
    """Require the fixed-point contract to be closed under declared targets."""
    undeclared = undeclared_bnet_regulators(functions)
    if undeclared:
        raise ValueError("Boolean network has undeclared regulator")


def scalar_fixed_point_count(functions: tuple[BNetFunction, ...], *, max_variables: int = 20) -> int:
    """Independent bounded oracle for fully specified Boolean networks."""
    targets = tuple(function.target for function in functions)
    if len(targets) > max_variables:
        raise ValueError("scalar fixed-point width exceeds limit")
    require_closed_bnet(functions)
    count = 0
    for values in product((False, True), repeat=len(targets)):
        assignment = dict(zip(targets, values))
        count += all(evaluate_bnet(function.expression, assignment) == assignment[function.target]
                     for function in functions)
    return count


def aeon_fixed_point_count(path: str | Path, *, max_variables: int = 16384) -> int:
    """Count fixed points through the pinned Biodivine AEON Python API."""
    source = Path(path).resolve()
    if not source.is_file() or source.is_symlink():
        raise ValueError("AEON input missing or linked")
    functions = parse_bnet(source.read_text(encoding="utf-8"), max_functions=max_variables)
    require_closed_bnet(functions)
    from biodivine_aeon import AsynchronousGraph, BooleanNetwork, FixedPoints
    network = BooleanNetwork.from_file(str(source)).infer_valid_graph()
    fixed_points = FixedPoints.symbolic(AsynchronousGraph(network))
    return int(fixed_points.vertices().cardinality())
