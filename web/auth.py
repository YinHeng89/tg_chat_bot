"""Web API 认证模块 — JWT token + 管理密码。"""

import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from storage.database import get_setting, set_setting
from utils.logger import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

import secrets

_SECRET_KEY = os.getenv("WEB_JWT_SECRET", "")
_SECRET_INITED = False


async def _init_secret_key():
    """如未设置环境变量，从 DB 读取或生成随机密钥。"""
    global _SECRET_KEY, _SECRET_INITED
    if _SECRET_INITED:
        return
    key = os.getenv("WEB_JWT_SECRET", "")
    if key:
        _SECRET_KEY = key
        _SECRET_INITED = True
        return
    key = await get_setting("web_jwt_secret", "")
    if not key:
        key = secrets.token_hex(32)
        await set_setting("web_jwt_secret", key)
        logger.info("已自动生成 JWT 密钥（持久化到数据库）")
    else:
        logger.info("从数据库加载 JWT 密钥")
    _SECRET_KEY = key
    _SECRET_INITED = True


_SECRET_INITED = bool(os.getenv("WEB_JWT_SECRET", ""))
if _SECRET_INITED:
    logger.info("从环境变量加载 JWT 密钥")


def get_secret_key() -> str:
    return _SECRET_KEY


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


async def verify_password(plain_password: str) -> bool:
    """验证管理密码（优先读 SQLite，fallback 环境变量默认值）。"""
    db_pwd = await get_setting("web_admin_password", "")
    if not db_pwd:
        db_pwd = os.getenv("WEB_ADMIN_PASSWORD", "admin_password")
    return plain_password == db_pwd


async def update_admin_password(new_password: str) -> bool:
    """更新管理密码。"""
    return await set_setting("web_admin_password", new_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
