"""代码执行连接器 — 沙箱执行 Python/Shell 代码，仅允许操作 workspace/ 目录。"""

import os
import subprocess
import tempfile
import shutil
from typing import Optional

from plugins.base import BasePlugin
from utils.logger import logger

WORKSPACE = "/app/workspace"
MAX_OUTPUT = 8000
TIMEOUT = 30  # 秒


class CodeRunnerPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "code_runner"

    @property
    def description(self) -> str:
        return "在沙箱中执行 Python 或 Shell 代码，访问 workspace 目录"

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
                    "在安全沙箱中执行代码。可以读写 /app/workspace 目录下的文件。"
                    "支持 Python(.py)和 Shell(.sh)。会自动创建缺失的文件。"
                    "结果只返回最后 5000 字符。执行超时 15 秒。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "language": {
                            "type": "string",
                            "enum": ["python", "shell"],
                            "description": "代码语言: python 或 shell"
                        },
                        "code": {
                            "type": "string",
                            "description": "要执行的代码。如果是 python，可以 import os/json/datetime/re/math/json 等标准库。如果是 shell，不要用交互式命令。"
                        },
                        "filename": {
                            "type": "string",
                            "description": "可选。如果代码需要写到文件里再执行(例如需要持久化)，填文件名(如 script.py)。不填则直接执行后丢弃。"
                        }
                    },
                    "required": ["language", "code"]
                }
            }
        }

    async def execute(self, params: dict, context: Optional[dict] = None) -> str:
        language = params.get("language", "python")
        code = params.get("code", "")
        filename = params.get("filename", "")

        if not code:
            return "请提供要执行的代码"

        os.makedirs(WORKSPACE, exist_ok=True)

        # 写入临时文件执行
        suffix = ".py" if language == "python" else ".sh"
        if filename:
            filepath = os.path.join(WORKSPACE, filename)
        else:
            fd, filepath = tempfile.mkstemp(suffix=suffix, dir=WORKSPACE)
            os.close(fd)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)

            if language == "python":
                cmd = ["python3", filepath]
            else:
                cmd = ["bash", filepath]

            env = os.environ.copy()
            env["HOME"] = WORKSPACE
            env["PATH"] = f"{WORKSPACE}:/usr/local/bin:/usr/bin:/bin"

            result = subprocess.run(
                cmd,
                cwd=WORKSPACE,
                env=env,
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
            )

            output = (result.stdout or "") + (result.stderr or "")
            if not output.strip():
                output = "(无输出)"

            if len(output) > MAX_OUTPUT:
                output = output[:MAX_OUTPUT] + f"\n... (截断，共 {len(output)} 字符)"

            return f"退出码: {result.returncode}\n{output.strip()}"

        except subprocess.TimeoutExpired:
            return f"执行超时 ({TIMEOUT}秒)，已终止"
        except FileNotFoundError:
            return f"执行环境错误: python3 或 bash 不可用"
        except Exception as e:
            logger.error(f"代码执行失败: {e}")
            return f"执行错误: {e}"
        finally:
            if not filename and os.path.exists(filepath):
                os.remove(filepath)
