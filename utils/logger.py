"""日志配置 — 使用 loguru，比标准 logging 更简洁。"""

import re
import sys
from loguru import logger

# 敏感信息模式
_SENSITIVE_PATTERNS = [
    (re.compile(r"(api_key|API_KEY|apikey)=([\w\-_]{8,})", re.IGNORECASE), r"\1=***MASKED***"),
    (re.compile(r"(password|secret|token)=([\w\-_]{6,})", re.IGNORECASE), r"\1=***MASKED***"),
    (re.compile(r'(sk-[A-Za-z0-9_\-]{20,})'), r"sk-***MASKED***"),
    (re.compile(r'(eyJ[A-Za-z0-9_\-=]+\.[A-Za-z0-9_\-=]+\.?[A-Za-z0-9_\-.+/=]*)'), r"JWT-***MASKED***"),
]


def sanitize_log(message: str) -> str:
    """脱敏日志中的 API Key、Token、密码等敏感信息。"""
    for pattern, replacement in _SENSITIVE_PATTERNS:
        message = pattern.sub(replacement, message)
    return message


def _sensitive_filter(record):
    """loguru filter：自动脱敏日志消息。"""
    record["message"] = sanitize_log(str(record["message"]))
    return True


# 移除默认 handler
logger.remove()

# 添加控制台输出（不落盘，Docker 日志自行管理）
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    filter=_sensitive_filter,
)

# 添加文件输出（自动轮转、压缩、限制总容量）
logger.add(
    "logs/bot_{time:YYYY-MM-DD}.log",
    rotation="5 MB",           # 单文件超 5MB 立即轮转
    retention="7 days",        # 只保留最近 7 天
    compression="zip",         # 轮转后自动 zip 压缩
    enqueue=True,              # 异步安全写入，避免阻塞
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    filter=_sensitive_filter,
)
