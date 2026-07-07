"""通用工具函数。"""

import re
import os
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Optional


def extract_urls(text: str) -> list[str]:
    url_pattern = re.compile(r'https?://[^\s<>"\'，。！？、；：（）《》【】]+')
    return url_pattern.findall(text)


def generate_chat_id(telegram_chat_id: int, user_id: Optional[int] = None) -> str:
    key = f"{telegram_chat_id}:{user_id}" if user_id else str(telegram_chat_id)
    return hashlib.md5(key.encode()).hexdigest()[:16]


def truncate_text(text: str, max_length: int = 4000) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length - 50] + "\n\n... (内容过长已截断)"


def parse_command_args(text: str) -> tuple[str, str]:
    text = text.strip()
    if not text.startswith("/"):
        return "", text
    parts = text.split(maxsplit=1)
    command = parts[0][1:]
    args = parts[1] if len(parts) > 1 else ""
    return command.lower(), args


def escape_markdown(text: str) -> str:
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    return text


# ===== Markdown → Telegram HTML 转换 =====

def md_to_html(text: str) -> str:
    """AI 输出的 Markdown → Telegram HTML 格式，容错处理。"""
    import html

    # 先转义 HTML，防止注入
    text = html.escape(text, quote=False)

    # 代码块 ```...``` （放在最前面，防止代码内容被后续规则误匹配）
    text = re.sub(r'```(\w*)\n?(.*?)```', r'<pre>\2</pre>', text, flags=re.DOTALL)

    # 行内代码 `...`
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

    # 表格 |...| → ASCII 对齐 + <pre>
    try:
        text = _convert_tables(text)
    except Exception:
        pass  # 表格转换失败时保留原文本

    # 标题 ### / ## / # → 粗体
    text = re.sub(r'^#{1,3} (.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)

    # 分割线 --- / *** → 横线
    text = re.sub(r'^[\-\*]{3,}$', '————————————————', text, flags=re.MULTILINE)

    # 引用 > → 缩进 + 竖线（支持嵌套 > > >）
    def _f(m):
        depth = len(re.findall(r'&gt; ', m.group(1)))
        return ('  ' * (depth - 1)) + '  ┃ ' + m.group(2)
    text = re.sub(r'^((?:&gt; )+)(.+)$', _f, text, flags=re.MULTILINE)

    # 粗体 **...**
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

    # 斜体 *...* (不能匹配 **)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)

    # 斜体 _..._ (下划线风格)
    text = re.sub(r'(?<![\w\\])_([^_]+)_(?![\w\\])', r'<i>\1</i>', text)

    # 删除线 ~~...~~
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)

    # 链接 [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

    # 无序列表
    text = re.sub(r'^[\-\*] (.+)$', lambda m: f'  \u2022 {m.group(1)}', text, flags=re.MULTILINE)

    # 数字列表
    text = re.sub(r'^(\d+)\. (.+)$', r'  \1. \2', text, flags=re.MULTILINE)

    return text


def _convert_tables(text: str) -> str:
    """将 Markdown 表格转为 tabulate ASCII 表格，用 <pre> 包裹。"""
    lines = text.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('|') and '|' in line[1:]:
            table_lines = [line]
            j = i + 1
            has_separator = False
            # 先找到分隔符行
            while j < len(lines) and lines[j].strip().startswith('|'):
                if re.match(r'^[\|\s\-:]+$', lines[j].strip()):
                    has_separator = True
                    break
                table_lines.append(lines[j])
                j += 1
            if has_separator:
                j += 1  # 跳过分隔符
                # 收集数据行
                while j < len(lines) and lines[j].strip().startswith('|'):
                    table_lines.append(lines[j])
                    j += 1
                # table_lines = [表头, 数据行1, 数据行2, ...]（分隔符不在里面）
                if len(table_lines) >= 2:
                    header_line = table_lines[0]
                    data_lines = table_lines[1:]  # ← 修复：不再多切一层
                    formatted = _tabulate(header_line, data_lines)
                    if formatted:
                        result.append(f"<pre>{formatted}</pre>")
                        i = j
                        continue
        result.append(line)
        i += 1
    return '\n'.join(result)


def _tabulate(header_line: str, data_lines: list[str]) -> str:
    """用 tabulate 格式化表格（自动处理中文宽度）。失败返回原文本。"""
    try:
        from tabulate import tabulate

        def parse_row(row: str) -> list[str]:
            return [c.strip() for c in row.strip().strip('|').split('|')]

        headers = parse_row(header_line)
        rows = [parse_row(r) for r in data_lines]
        if not headers or not rows:
            return ''

        max_cols = max(len(headers), max((len(r) for r in rows), default=0))
        headers += [''] * (max_cols - len(headers))
        rows = [r + [''] * (max_cols - len(r)) for r in rows]

        return tabulate(rows, headers=headers, tablefmt="grid", stralign="left")
    except Exception:
        # fallback：原样返回 Markdown 表格文本，不丢数据
        return '\n'.join([header_line] + data_lines)


def supports_vision(model_name: str) -> bool:
    """根据模型名推断是否支持图片/多模态（名称启发式，比盲猜靠谱）。"""
    if not model_name:
        return False
    m = model_name.lower()
    # OpenAI
    if any(x in m for x in ('gpt-4o', 'gpt-4-turbo', 'gpt-4-vision', 'o1', 'o3', 'o4')):
        return True
    if 'gpt-3' in m:
        return False
    # Anthropic (Claude 3+ 均支持 vision)
    if 'claude-3' in m or 'claude-4' in m or 'claude-sonnet' in m or 'claude-opus' in m:
        return True
    if 'claude-2' in m or 'claude-1' in m:
        return False
    # Google Gemini
    if 'gemini' in m and 'vision' in m:
        return True
    if 'gemini-2' in m or 'gemini-1.5' in m:
        return True  # Gemini 1.5+ 全系多模态
    # Qwen
    if 'qwen-vl' in m or 'qvq' in m:
        return True
    if 'qwen' in m and 'vl' not in m and 'qvq' not in m:
        return False  # Qwen 纯文本模型不支持
    # GLM
    if 'glm-4v' in m or 'cogview' in m or 'cogvlm' in m:
        return True
    # Step
    if 'step-1v' in m:
        return True
    # MiniMax
    if 'minimax' in m:
        return False  # 目前不支持 vision
    # Ollama
    if any(x in m for x in ('llava', 'bakllava', 'cogvlm', 'minicpm-v', 'gemma3')):
        return True
    if 'llama' in m and 'vision' in m:
        return True
    # DeepSeek
    if 'deepseek' in m:
        return False  # 目前不支持 vision
    # Moonshot / Kimi
    if 'moonshot' in m or 'kimi' in m:
        return False  # 目前不支持 vision
    # 百度的 ERNIE
    if 'ernie-4' in m:
        return True  # ERNIE 4.0 支持多模态
    # 字节豆包
    if 'doubao' in m and 'vision' in m:
        return True
    if 'doubao' in m:
        return False  # 普通豆包不支持
    # 未知模型：保守返回 False
    return False


# ===== 时区 =====

_timezone: ZoneInfo | None = None
_timezone_name: str = ""


def get_timezone() -> ZoneInfo:
    """获取配置的时区（默认 Asia/Shanghai），缓存结果。"""
    global _timezone, _timezone_name
    tz_name = os.environ.get("TZ", "") or "Asia/Shanghai"
    if _timezone is None or tz_name != _timezone_name:
        try:
            _timezone = ZoneInfo(tz_name)
            _timezone_name = tz_name
        except (ZoneInfoNotFoundError, KeyError):
            _timezone = ZoneInfo("Asia/Shanghai")
            _timezone_name = "Asia/Shanghai"
    return _timezone


def get_now() -> datetime:
    """获取配置时区的当前时间（naive datetime，用于与 DB 中的本地时间比较）。"""
    tz = get_timezone()
    return datetime.now(tz).replace(tzinfo=None)


def get_now_str(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """获取配置时区当前时间的格式化字符串。"""
    return get_now().strftime(fmt)


def check_wcwidth():
    """启动时检查 wcwidth 是否安装（tabulate 中文对齐依赖）。"""
    try:
        import wcwidth  # noqa: F401
    except ImportError:
        import warnings
        warnings.warn("wcwidth 未安装，中文表格可能错位。请运行: pip install wcwidth")
