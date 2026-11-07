from __future__ import annotations

import ast
from typing import Any, Dict


class ExpressionError(ValueError):
    pass


_ALLOWED_FUNCS = {
    "len": len,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "sum": sum,
    "sorted": sorted,
    "any": any,
    "all": all,
}


def _resolve(obj: Any, key: Any) -> Any:
    if isinstance(key, str) and key.startswith("_"):
        raise ExpressionError("private attribute is not allowed")
    if isinstance(obj, dict):
        try:
            return obj[key]
        except KeyError as exc:
            raise ExpressionError(f"missing key: {key}") from exc
    try:
        return getattr(obj, key)
    except AttributeError as exc:
        raise ExpressionError(f"missing attribute: {key}") from exc


def _eval(node: ast.AST, env: Dict[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval(node.body, env)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise ExpressionError(f"unknown name: {node.id}")
    if isinstance(node, ast.Attribute):
        return _resolve(_eval(node.value, env), node.attr)
    if isinstance(node, ast.Subscript):
        obj = _eval(node.value, env)
        key = _eval(node.slice, env)
        return _resolve(obj, key)
    if isinstance(node, ast.List):
        return [_eval(item, env) for item in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_eval(item, env) for item in node.elts)
    if isinstance(node, ast.Dict):
        return {_eval(k, env): _eval(v, env) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.UnaryOp):
        value = _eval(node.operand, env)
        if isinstance(node.op, ast.Not):
            return not value
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return +value
        raise ExpressionError("unsupported unary operator")
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            result: Any = True
            for value in node.values:
                result = _eval(value, env)
                if not result:
                    return result
            return result
        result = False
        for value in node.values:
            result = _eval(value, env)
            if result:
                return result
        return result
    if isinstance(node, ast.BinOp):
        left = _eval(node.left, env)
        right = _eval(node.right, env)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.FloorDiv):
            return left // right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            if abs(right) > 8:
                raise ExpressionError("exponent is too large")
            return left**right
        raise ExpressionError("unsupported operator")
    if isinstance(node, ast.Compare):
        left = _eval(node.left, env)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval(comparator, env)
            if isinstance(op, ast.Eq):
                ok = left == right
            elif isinstance(op, ast.NotEq):
                ok = left != right
            elif isinstance(op, ast.Lt):
                ok = left < right
            elif isinstance(op, ast.LtE):
                ok = left <= right
            elif isinstance(op, ast.Gt):
                ok = left > right
            elif isinstance(op, ast.GtE):
                ok = left >= right
            elif isinstance(op, ast.In):
                ok = left in right
            elif isinstance(op, ast.NotIn):
                ok = left not in right
            else:
                raise ExpressionError("unsupported comparison")
            if not ok:
                return False
            left = right
        return True
    if isinstance(node, ast.IfExp):
        return _eval(node.body, env) if _eval(node.test, env) else _eval(node.orelse, env)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCS:
            raise ExpressionError("function is not allowed")
        if node.keywords:
            raise ExpressionError("keyword arguments are not allowed")
        func = _ALLOWED_FUNCS[node.func.id]
        return func(*[_eval(arg, env) for arg in node.args])
    raise ExpressionError(f"unsupported expression: {type(node).__name__}")


def evaluate(expression: str | None, env: Dict[str, Any], default: Any = None) -> Any:
    if expression is None or (isinstance(expression, str) and not expression.strip()):
        return default
    try:
        tree = ast.parse(str(expression).strip(), mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"语法错误: {exc.msg}") from exc
    return _eval(tree, env)


def render_template(text: str, env: Dict[str, Any]) -> str:
    """Render {{ expression }} placeholders inside a text field."""
    if not text or "{{" not in text:
        return text
    out = []
    index = 0
    while True:
        start = text.find("{{", index)
        if start == -1:
            out.append(text[index:])
            break
        end = text.find("}}", start + 2)
        if end == -1:
            out.append(text[index:])
            break
        out.append(text[index:start])
        expr = text[start + 2 : end].strip()
        try:
            value = evaluate(expr, env)
        except ExpressionError as exc:
            value = f"<{exc}>"
        out.append(str(value))
        index = end + 2
    return "".join(out)
