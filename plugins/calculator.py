"""计算器连接器 — 安全的数学表达式计算。"""

import ast
import operator
import math
from typing import Optional

from plugins.base import BasePlugin


class CalculatorPlugin(BasePlugin):
    """安全的数学表达式计算器，不执行任意代码。"""

    # 允许的操作符和函数
    _ALLOWED_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    _ALLOWED_FUNCS = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
        "tan": math.tan, "log": math.log, "log10": math.log10,
        "log2": math.log2, "exp": math.exp,
        "ceil": math.ceil, "floor": math.floor,
        "radians": math.radians, "degrees": math.degrees,
        "pi": math.pi, "e": math.e,
    }

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "安全的数学计算器，支持基本运算和数学函数"

    @property
    def auto_trigger(self) -> bool:
        return True

    @property
    def manual_command(self) -> str:
        return "calc"

    def _safe_eval(self, node):
        """安全地计算 AST 节点。"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = self._safe_eval(node.left)
            right = self._safe_eval(node.right)
            op_type = type(node.op)
            if op_type not in self._ALLOWED_OPS:
                raise ValueError(f"不支持的操作符: {op_type}")
            return self._ALLOWED_OPS[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self._safe_eval(node.operand)
            op_type = type(node.op)
            if op_type not in self._ALLOWED_OPS:
                raise ValueError(f"不支持的操作符: {op_type}")
            return self._ALLOWED_OPS[op_type](operand)
        elif isinstance(node, ast.Call):
            func_name = node.func.id
            if func_name not in self._ALLOWED_FUNCS:
                raise ValueError(f"不支持的函数: {func_name}")
            args = [self._safe_eval(arg) for arg in node.args]
            return self._ALLOWED_FUNCS[func_name](*args)
        elif isinstance(node, ast.Name):
            if node.id in self._ALLOWED_FUNCS:
                return self._ALLOWED_FUNCS[node.id]
            raise ValueError(f"不支持的变量: {node.id}")
        else:
            raise ValueError(f"不支持的表达式类型: {type(node)}")

    async def execute(self, params: dict, context: Optional[dict] = None) -> str:
        expr = params.get("query", "") or params.get("expression", "")
        if not expr:
            return "请提供计算表达式，例如: /calc 1024 * 768"

        # 清理表达式
        expr = expr.strip()
        if expr.startswith("计算"):
            expr = expr[2:].strip()

        try:
            tree = ast.parse(expr, mode="eval")
            result = self._safe_eval(tree.body)

            if isinstance(result, float):
                if result == int(result):
                    result = int(result)
                else:
                    result = round(result, 10)

            return f"{expr} = {result}"

        except SyntaxError:
            return f"表达式 '{expr}' 格式不正确"
        except (ValueError, ZeroDivisionError) as e:
            return f"计算错误: {e}"
        except Exception as e:
            return f"无法计算: {e}"
