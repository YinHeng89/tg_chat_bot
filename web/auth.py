"""Web API 认证模块 — JWT token + 管理密码（bcrypt 哈希）+ 恢复码。"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from storage.database import get_setting, set_setting
from utils.logger import logger

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
_MAX_PASSWORD_LENGTH = 72  # bcrypt 单次输入上限
_MIN_PASSWORD_LENGTH = 6

# 延迟初始化，避免 bcrypt 版本兼容性在 import 时报错
_pwd_context = None


def _get_pwd_context() -> CryptContext:
    global _pwd_context
    if _pwd_context is None:
        _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return _pwd_context


_SECRET_KEY = os.getenv("WEB_JWT_SECRET", "")
_SECRET_INITED = bool(_SECRET_KEY)

if _SECRET_INITED:
    logger.info("从环境变量加载 JWT 密钥")


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


def get_secret_key() -> str:
    return _SECRET_KEY


# ===== 恢复码 =====

def _generate_recovery_code() -> str:
    """生成恢复码：12 位大写字母+数字，格式 XXXX-XXXX-XXXX。"""
    raw = secrets.token_hex(6).upper()  # 12 位 hex
    return f"{raw[:4]}-{raw[4:8]}-{raw[8:12]}"


async def get_setup_status() -> dict:
    """检查是否需要首次设置。"""
    db_pwd = await get_setting("web_admin_password", "")
    return {"need_setup": not bool(db_pwd)}


async def setup_password(password: str) -> dict:
    """首次设置：创建密码，返回一次性恢复码。"""
    if not password or len(password) < _MIN_PASSWORD_LENGTH:
        raise ValueError(f"密码至少 {_MIN_PASSWORD_LENGTH} 位")

    # 检查是否已经设置过
    existing = await get_setting("web_admin_password", "")
    if existing:
        raise ValueError("已经设置过密码，请使用登录或重置功能")

    # 存储 bcrypt 哈希
    pwd = password[: _MAX_PASSWORD_LENGTH] if len(password) > _MAX_PASSWORD_LENGTH else password
    pc = _get_pwd_context()
    hashed = pc.hash(pwd)
    await set_setting("web_admin_password", hashed)

    # 生成恢复码并存储其哈希
    recovery_code = _generate_recovery_code()
    recovery_hash = pc.hash(recovery_code)
    await set_setting("web_recovery_code", recovery_hash)

    logger.info("首次密码设置完成，恢复码已生成")
    return {"success": True, "recovery_code": recovery_code}


async def reset_password(recovery_code: str, new_password: str) -> dict:
    """通过恢复码重置密码，重置成功后重新生成恢复码并返回。"""
    if not recovery_code or not new_password:
        raise ValueError("请提供恢复码和新密码")
    if len(new_password) < _MIN_PASSWORD_LENGTH:
        raise ValueError(f"新密码至少 {_MIN_PASSWORD_LENGTH} 位")

    recovery_hash = await get_setting("web_recovery_code", "")
    if not recovery_hash:
        raise ValueError("系统未初始化恢复码，请先设置密码")

    pc = _get_pwd_context()
    if not pc.verify(recovery_code, recovery_hash):
        raise ValueError("恢复码错误")

    # 重置密码
    pwd = new_password[: _MAX_PASSWORD_LENGTH] if len(new_password) > _MAX_PASSWORD_LENGTH else new_password
    hashed = pc.hash(pwd)
    await set_setting("web_admin_password", hashed)

    # 重新生成恢复码
    new_recovery_code = _generate_recovery_code()
    new_recovery_hash = pc.hash(new_recovery_code)
    await set_setting("web_recovery_code", new_recovery_hash)

    logger.info("通过恢复码重置密码成功，恢复码已重新生成")
    return {"success": True, "recovery_code": new_recovery_code}


# ===== 密码验证与更新 =====

async def verify_password(plain_password: str) -> bool:
    """验证管理密码（bcrypt 哈希，兼容旧明文自动迁移）。"""
    db_pwd = await get_setting("web_admin_password", "")
    if not db_pwd:
        return False
    # bcrypt hash
    if db_pwd.startswith("$2"):
        pc = _get_pwd_context()
        return pc.verify(plain_password, db_pwd)
    # 旧明文密码：验证成功后自动升级为哈希
    if plain_password == db_pwd:
        logger.info("检测到旧格式密码，自动迁移为 bcrypt 哈希")
        await _store_password_hash(plain_password)
        return True
    return False


async def _store_password_hash(password: str) -> bool:
    """存储密码的 bcrypt 哈希。"""
    pwd = password[: _MAX_PASSWORD_LENGTH] if len(password) > _MAX_PASSWORD_LENGTH else password
    pc = _get_pwd_context()
    hashed = pc.hash(pwd)
    return await set_setting("web_admin_password", hashed)


async def update_admin_password(new_password: str) -> bool:
    """更新管理密码（存储 bcrypt 哈希）。"""
    return await _store_password_hash(new_password)


# ===== JWT =====

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
