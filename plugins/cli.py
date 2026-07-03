"""CLI 命令执行连接器 — 直接在容器沙箱中执行 Shell 命令。"""

import os
import resource
import subprocess
from typing import Optional

from plugins.base import BasePlugin
from utils.logger import logger

WORKSPACE = "/app/workspace"
MAX_OUTPUT = 8000
TIMEOUT = 30  # 秒
MAX_MEMORY_MB = 256  # 进程最大内存 (MB)

# 危险命令黑名单（docker 容器内不需要这些）
_BLOCKED_COMMANDS = (
    "shutdown", "reboot", "halt", "poweroff", "init ",
    "mkfs.", "mkswap", "dd if=", ":(){ :|:& };:",
)


def _set_limits():
    """子进程资源限制：CPU 时间 + 内存上限。"""
    cpu_seconds = TIMEOUT + 5
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    mem_bytes = MAX_MEMORY_MB * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))


class CLIPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "cli"

    @property
    def description(self) -> str:
        return "在容器沙箱中执行 Shell 命令（bash -c），可用于文件操作、文本搜索、JSON 处理等"

    @property
    def auto_trigger(self) -> bool:
        return True

    @property
    def manual_command(self) -> str:
        return ""

    def get_tool_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": (
                    "在容器的 /app/workspace 目录下执行 Shell 命令。\n"
                    "可用于：\n"
                    "- 列出文件: ls -la /app/workspace/\n"
                    "- 读取文件: cat /app/workspace/file.txt\n"
                    "- 搜索文本: grep 'pattern' /app/workspace/*.json\n"
                    "- JSON 处理: python3 -m json.tool /app/workspace/data.json\n"
                    "- 统计: wc -l /app/workspace/*.py | sort -n\n"
                    "- 查找: find /app/workspace/ -name '*.py' -mtime -1\n"
                    "可用工具: cat grep find ls wc head tail sort uniq awk sed python3\n"
                    f"输出限制 {MAX_OUTPUT} 字符，超时 {TIMEOUT} 秒。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": (
                                "要执行的 Shell 命令。自动在 /app/workspace 目录下执行。"
                                "支持管道(|)和重定向(>)，但不要用交互式命令。"
                                "JSON 格式化推荐: python3 -m json.tool <file>"
                            ),
                        }
                    },
                    "required": ["command"],
                },
            },
        }

    async def execute(self, params: dict, context: Optional[dict] = None) -> str:
        command = params.get("command", "").strip()

        if not command:
            return "请提供要执行的命令"

        # 危险命令检查
        cmd_lower = command.lower()
        for blocked in _BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                logger.warning(f"拦截危险命令: {blocked!r} in {command!r}")
                return f"命令被拦截: 不允许执行可能破坏系统的命令"

        os.makedirs(WORKSPACE, exist_ok=True)

        env = os.environ.copy()
        env["HOME"] = WORKSPACE
        env["PATH"] = f"{WORKSPACE}:/usr/local/bin:/usr/bin:/bin"

        try:
            result = subprocess.run(
                ["bash", "-c", command],
                cwd=WORKSPACE,
                env=env,
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
                preexec_fn=_set_limits,
            )

            output = (result.stdout or "") + (result.stderr or "")
            if not output.strip():
                output = "(无输出)"

            if len(output) > MAX_OUTPUT:
                output = output[:MAX_OUTPUT] + f"\n... (截断，共 {len(output)} 字符)"

            rc_info = f"退出码: {result.returncode}" if result.returncode != 0 else ""
            lines = [l for l in (rc_info, output.strip()) if l]
            return "\n".join(lines)

        except subprocess.TimeoutExpired:
            return f"命令超时 ({TIMEOUT}秒)，已终止"
        except Exception as e:
            logger.error(f"CLI 执行失败: command={command[:100]!r} error={e}")
            return f"执行错误: {e}"
