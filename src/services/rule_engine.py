from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, DivisionByZero, InvalidOperation, ROUND_HALF_UP
from typing import Any

from src.core.errors import DomainError

DECIMAL_RE = re.compile(r"^(?:0|-[1-9]\d*|[1-9]\d*)(?:\.\d{1,6})?$")
NUMERIC_OPS = {"add", "sub", "mul", "div", "min", "max", "abs", "round"}
COMPARE_OPS = {"eq", "ne", "lt", "lte", "gt", "gte"}
BOOL_OPS = {"and", "or", "not", "is_missing", "is_valid", "in"}
ALLOWED_OPS = {"const", "ref"} | NUMERIC_OPS | COMPARE_OPS | BOOL_OPS


def decimal_value(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise DomainError("TYPE_INVALID", "Boolean is not a decimal")
    text = str(value)
    if not DECIMAL_RE.fullmatch(text) or text == "-0":
        raise DomainError("TYPE_INVALID", "Decimal must use canonical base-10 notation")
    try:
        parsed = Decimal(text)
    except InvalidOperation as exc:
        raise DomainError("TYPE_INVALID", "Decimal is invalid") from exc
    if len(parsed.as_tuple().digits) > 18:
        raise DomainError("RULE_SCHEMA_INVALID", "Decimal precision exceeds 18 digits")
    return parsed


def decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


@dataclass
class _Budget:
    nodes: int = 0


class RuleInterpreter:
    version = "json-ast/1"
    max_depth = 20
    max_nodes = 500
    max_args = 100

    _fields = {
        "const": {"op", "value"},
        "ref": {"op", "kind", "code"},
        "add": {"op", "args"},
        "mul": {"op", "args"},
        "min": {"op", "args"},
        "max": {"op", "args"},
        "sub": {"op", "left", "right"},
        "div": {"op", "left", "right"},
        "abs": {"op", "value"},
        "round": {"op", "value", "decimals", "mode"},
        "eq": {"op", "left", "right"},
        "ne": {"op", "left", "right"},
        "lt": {"op", "left", "right"},
        "lte": {"op", "left", "right"},
        "gt": {"op", "left", "right"},
        "gte": {"op", "left", "right"},
        "and": {"op", "args"},
        "or": {"op", "args"},
        "not": {"op", "value"},
        "is_missing": {"op", "value"},
        "is_valid": {"op", "value"},
        "in": {"op", "value", "set"},
    }

    def validate(self, node: Any) -> None:
        self._validate(node, 1, _Budget())

    def _validate(self, node: Any, depth: int, budget: _Budget) -> None:
        if depth > self.max_depth:
            raise DomainError("RULE_LIMIT_EXCEEDED", "AST depth exceeds 20")
        budget.nodes += 1
        if budget.nodes > self.max_nodes:
            raise DomainError("RULE_LIMIT_EXCEEDED", "AST node count exceeds 500")
        if not isinstance(node, dict) or not isinstance(node.get("op"), str):
            raise DomainError(
                "RULE_SCHEMA_INVALID", "Every AST node must be an object with op"
            )
        op = node["op"]
        if op not in ALLOWED_OPS:
            raise DomainError("RULE_SCHEMA_INVALID", f"Operator '{op}' is not allowed")
        expected = self._fields[op]
        if set(node) != expected:
            raise DomainError(
                "RULE_SCHEMA_INVALID", f"Operator '{op}' has invalid fields"
            )
        if op == "ref":
            if not isinstance(node["kind"], str) or not isinstance(node["code"], str):
                raise DomainError(
                    "RULE_SCHEMA_INVALID", "Reference kind/code must be strings"
                )
            if "." in node["kind"] or "." in node["code"]:
                raise DomainError(
                    "RULE_SCHEMA_INVALID", "Reference traversal is forbidden"
                )
        elif op in {"add", "mul", "min", "max", "and", "or"}:
            args = node["args"]
            if not isinstance(args, list) or not 2 <= len(args) <= self.max_args:
                raise DomainError(
                    "RULE_SCHEMA_INVALID", f"Operator '{op}' requires 2..100 args"
                )
            for arg in args:
                self._validate(arg, depth + 1, budget)
        elif op in {"sub", "div"} | COMPARE_OPS:
            self._validate(node["left"], depth + 1, budget)
            self._validate(node["right"], depth + 1, budget)
        elif op in {"abs", "not", "is_missing", "is_valid"}:
            self._validate(node["value"], depth + 1, budget)
        elif op == "round":
            if (
                node["mode"] != "half_up"
                or not isinstance(node["decimals"], int)
                or not 0 <= node["decimals"] <= 6
            ):
                raise DomainError(
                    "RULE_SCHEMA_INVALID", "round requires half_up and 0..6 decimals"
                )
            self._validate(node["value"], depth + 1, budget)
        elif op == "in":
            values = node["set"]
            if not isinstance(values, list) or not 1 <= len(values) <= 100:
                raise DomainError(
                    "RULE_SCHEMA_INVALID", "in set must contain 1..100 literals"
                )
            if any(isinstance(value, (dict, list)) for value in values):
                raise DomainError(
                    "RULE_SCHEMA_INVALID", "in set accepts scalar literals only"
                )
            if len({repr(value) for value in values}) != len(values):
                raise DomainError("RULE_SCHEMA_INVALID", "in set values must be unique")
            self._validate(node["value"], depth + 1, budget)

    def evaluate(self, node: dict, context: dict[str, Any]) -> Any:
        self.validate(node)
        return self._evaluate(node, context)

    def _evaluate(self, node: dict, context: dict[str, Any]) -> Any:
        op = node["op"]
        if op == "const":
            value = node["value"]
            if isinstance(value, str) and DECIMAL_RE.fullmatch(value) and value != "-0":
                return decimal_value(value)
            if isinstance(value, (str, bool)):
                return value
            raise DomainError(
                "RULE_SCHEMA_INVALID",
                "const must be canonical decimal, string or boolean",
            )
        if op == "ref":
            key = f"{node['kind']}:{node['code']}"
            if key not in context:
                raise DomainError(
                    "RULE_SCHEMA_INVALID", f"Reference '{key}' is not declared"
                )
            return context[key]
        if op in {"add", "mul", "min", "max"}:
            values = [
                self._numeric(self._evaluate(arg, context)) for arg in node["args"]
            ]
            if op == "add":
                return sum(values, Decimal(0))
            if op == "mul":
                result = Decimal(1)
                for value in values:
                    result *= value
                return self._bounded(result)
            return min(values) if op == "min" else max(values)
        if op in {"sub", "div"}:
            left = self._numeric(self._evaluate(node["left"], context))
            right = self._numeric(self._evaluate(node["right"], context))
            if op == "div" and right == 0:
                raise DomainError(
                    "DIVISION_BY_ZERO", "Division by zero in scoring rule"
                )
            try:
                return self._bounded(left - right if op == "sub" else left / right)
            except DivisionByZero as exc:
                raise DomainError(
                    "DIVISION_BY_ZERO", "Division by zero in scoring rule"
                ) from exc
        if op == "abs":
            return abs(self._numeric(self._evaluate(node["value"], context)))
        if op == "round":
            value = self._numeric(self._evaluate(node["value"], context))
            quantum = Decimal(1).scaleb(-node["decimals"])
            return value.quantize(quantum, rounding=ROUND_HALF_UP)
        if op in COMPARE_OPS:
            left = self._evaluate(node["left"], context)
            right = self._evaluate(node["right"], context)
            if op == "eq":
                return left == right
            if op == "ne":
                return left != right
            if type(left) is not type(right):
                raise DomainError(
                    "RULE_SCHEMA_INVALID",
                    "Ordered comparison operands must have the same type",
                )
            return {
                "lt": left < right,
                "lte": left <= right,
                "gt": left > right,
                "gte": left >= right,
            }[op]
        if op in {"and", "or"}:
            if op == "and":
                return all(bool(self._evaluate(arg, context)) for arg in node["args"])
            return any(bool(self._evaluate(arg, context)) for arg in node["args"])
        if op == "not":
            return not bool(self._evaluate(node["value"], context))
        if op == "is_missing":
            return self._evaluate(node["value"], context) is None
        if op == "is_valid":
            return self._evaluate(node["value"], context) == "valid"
        if op == "in":
            value = self._evaluate(node["value"], context)
            converted = [
                (
                    decimal_value(v)
                    if isinstance(v, str) and DECIMAL_RE.fullmatch(v)
                    else v
                )
                for v in node["set"]
            ]
            return value in converted
        raise DomainError("RULE_SCHEMA_INVALID", "Unreachable operator")

    @staticmethod
    def _numeric(value: Any) -> Decimal:
        if not isinstance(value, Decimal):
            raise DomainError(
                "RULE_SCHEMA_INVALID", "Numeric operator received non-numeric input"
            )
        return value

    @staticmethod
    def _bounded(value: Decimal) -> Decimal:
        if abs(value) > Decimal("1e18"):
            raise DomainError(
                "RULE_LIMIT_EXCEEDED", "Numeric result exceeds allowed range"
            )
        return value
