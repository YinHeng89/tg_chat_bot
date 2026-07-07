"""Web API — FastAPI 管理后台，所有数据来自 SQLite。"""

import json
import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.config import core_config
from core.llm import llm_manager
from plugins.registry import plugin_registry
from storage.database import (
    get_stats, get_blacklist, add_blacklist, remove_blacklist,
    get_model_configs, get_model_config, update_model_config, add_model_config, delete_model_config,
    get_setting, set_setting, get_all_settings,
    get_plugin_configs, set_plugin_enabled,
    get_enabled_models,
    get_bots, create_bot, update_bot, delete_bot, get_bot,
)
from web.auth import (
    verify_password, create_access_token, verify_token, update_admin_password,
    get_setup_status, setup_password, reset_password,
)
from utils.logger import logger

app = FastAPI(title="TG AI Chat Bot - 管理面板 API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== 模型 =====

# ===== 健康检查 =====

@app.get("/healthz")
async def healthz():
    """存活检查：进程是否运行。"""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    """就绪检查：数据库是否可访问。"""
    try:
        from storage.database import get_db
        db = await get_db()
        await db.execute("SELECT 1")
        await db.close()
        return {"status": "ready", "database": "ok"}
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}


class SettingUpdate(BaseModel):
    key: str
    value: str

class ModelConfigUpdate(BaseModel):
    display_name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    is_enabled: Optional[bool] = None

class PluginToggle(BaseModel):
    name: str
    enabled: bool

class BlacklistReq(BaseModel):
    user_id: int
    reason: str = ""

class BatchSettingsUpdate(BaseModel):
    settings: dict

class BotCreate(BaseModel):
    name: str
    bot_token: str

class BotUpdate(BaseModel):
    name: Optional[str] = None
    bot_token: Optional[str] = None
    is_active: Optional[bool] = None


# ===== 认证 =====

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证信息")
    payload = verify_token(authorization.replace("Bearer ", ""))
    if not payload:
        raise HTTPException(status_code=401, detail="认证已过期")
    return payload


@app.post("/api/models/test")
async def test_model(req: dict, user=Depends(get_current_user)):
    """测试模型是否可用：发送一句话获取回复。"""
    provider = req.get("provider", "")
    base_url = req.get("base_url", "").rstrip("/")
    api_key = req.get("api_key", "")
    model_name = req.get("model_name", "")
    if not api_key or not base_url or not model_name:
        raise HTTPException(status_code=400, detail="缺少必要信息")

    try:
        from core.llm import _create_backend
        config = {"provider": provider, "api_key": api_key, "base_url": base_url, "model_name": model_name, "name": "Test"}
        backend = _create_backend(config)
        result = await backend.chat([
            {"role": "user", "content": "你好，请回复1+1="}
        ], max_tokens=50)
        return {
            "success": True,
            "reply": result.text[:200],
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
        }
    except Exception as e:
        return {"success": False, "error": str(e)[:300]}


@app.post("/api/models/query-list")
async def query_models(req: dict, user=Depends(get_current_user)):
    """查询某个服务商的可用模型列表。"""
    provider = req.get("provider", "openai")
    base_url = req.get("base_url", "").rstrip("/")
    api_key = req.get("api_key", "")
    if not base_url and not api_key:
        return {"models": []}

    try:
        if provider == "ollama":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{base_url}/api/tags")
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
        else:
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{base_url}/models", headers=headers)
                data = resp.json()
                models = [m["id"] for m in data.get("data", [])]
                models.sort()
        from utils.helpers import supports_vision
        vision_map = {m: supports_vision(m) for m in models}
        return {"models": models[:100], "vision": vision_map}
    except Exception as e:
        return {"models": [], "error": str(e)}


@app.get("/api/auth/status")
async def auth_status():
    """检查是否需要首次设置密码。"""
    return await get_setup_status()


@app.post("/api/auth/setup")
async def auth_setup(req: dict):
    """首次设置：创建密码，返回恢复码（仅显示一次，请妥善保存）。"""
    password = req.get("password", "")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")

    # 检查是否已经设置过
    status = await get_setup_status()
    if not status["need_setup"]:
        raise HTTPException(status_code=400, detail="已经设置过密码")

    try:
        result = await setup_password(password)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/reset-password")
async def auth_reset_password(req: dict):
    """通过恢复码重置密码，返回新恢复码（旧恢复码立即失效）。"""
    recovery_code = req.get("recovery_code", "").strip().upper()
    new_password = req.get("new_password", "")

    if not recovery_code or not new_password:
        raise HTTPException(status_code=400, detail="请提供恢复码和新密码")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")

    try:
        result = await reset_password(recovery_code, new_password)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
async def login(req: dict):
    """登录：需要密码。如果未设置密码则提示首次设置。"""
    status = await get_setup_status()
    if status["need_setup"]:
        raise HTTPException(status_code=400, detail="请先设置管理密码（SETUP_REQUIRED）")

    password = req.get("password", "")
    if not await verify_password(password):
        raise HTTPException(status_code=401, detail="密码错误")
    token = create_access_token({"role": "admin"})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/api/auth/change-password")
async def change_password(req: dict, user=Depends(get_current_user)):
    old_pwd = req.get("old_password", "")
    new_pwd = req.get("new_password", "")
    if not old_pwd or not new_pwd:
        raise HTTPException(status_code=400, detail="请提供新旧密码")
    if not await verify_password(old_pwd):
        raise HTTPException(status_code=400, detail="旧密码错误")
    if len(new_pwd) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    await update_admin_password(new_pwd)
    return {"success": True}


@app.get("/api/auth/verify")
async def verify(user=Depends(get_current_user)):
    return {"valid": True}


# ===== 仪表盘 =====

@app.get("/api/dashboard")
async def dashboard(user=Depends(get_current_user)):
    stats_7d = await get_stats(7)
    stats_30d = await get_stats(30)
    models = await get_model_configs()
    plugins = await get_plugin_configs()

    from storage.database import get_db
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM sessions")
        total_sessions = (await cursor.fetchone())[0]
    finally:
        await db.close()

    return {
        "stats_7d": stats_7d,
        "stats_30d": stats_30d,
        "models": [{"id": m["id"], "name": m["name"], "provider": m["provider"],
                     "model_name": m["model_name"], "is_enabled": bool(m["is_enabled"])} for m in models],
        "plugins": [{"name": p["name"], "enabled": bool(p["enabled"])} for p in plugins],
        "total_sessions": total_sessions,
        "available_backends": [b._name for b in llm_manager.backends],
    }


# ===== 全局设置 =====

@app.get("/api/settings")
async def get_all(user=Depends(get_current_user)):
    """获取所有设置 + 模型配置。"""
    data = await core_config.get_all_dict()
    # 脱敏模型配置
    models = await get_model_configs()
    data["model_configs"] = [
        {
            "id": m["id"],
            "name": m["name"],
            "provider": m["provider"],
            "api_key": "***" + m["api_key"][-4:] if len(m["api_key"]) > 4 else "",
            "base_url": m["base_url"],
            "model_name": m["model_name"],
            "is_enabled": bool(m["is_enabled"]),
        }
        for m in models
    ]
    data["plugins"] = [
        {"name": p["name"], "enabled": bool(p["enabled"])}
        for p in await get_plugin_configs()
    ]
    return data


@app.post("/api/settings/set")
async def set_one(req: SettingUpdate, user=Depends(get_current_user)):
    await set_setting(req.key, req.value)
    await core_config.refresh()
    return {"success": True, "key": req.key}


@app.post("/api/settings/batch")
async def set_batch(req: BatchSettingsUpdate, user=Depends(get_current_user)):
    for key, value in req.settings.items():
        await set_setting(key, value)
        if key.endswith(":allowed_models"):
            bot_id = key.split(":")[0]
            logger.info(f"Bot #{bot_id} 模型选择已更新: {value}")
    await core_config.refresh()
    return {"success": True, "updated": list(req.settings.keys())}


# ===== 机器人实例管理 =====

from core.bot_manager import bot_manager
import httpx


@app.post("/api/bots/verify")
async def verify_bot(req: dict, user=Depends(get_current_user)):
    """验证 Bot Token 并获取信息。"""
    token = req.get("bot_token", "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="请先输入 Token 再验证哦")

    # 提取纯 token（支持粘贴完整 URL 如 https://t.me/bot?token=xxx）
    for part in token.split("?"):
        if ":" in part and len(part) > 30:
            token = part.split("=")[-1] if "=" in part else part
            break

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            data = resp.json()

        if not data.get("ok"):
            code = data.get("error_code", "")
            if code == 401:
                raise HTTPException(status_code=400, detail="Token 好像不太对，检查一下再试试吧")
            raise HTTPException(status_code=400, detail="验证没通过，可能 Token 有误，重新粘贴看看？")

        result = data["result"]
        return {
            "valid": True,
            "id": result["id"],
            "username": result.get("username", ""),
            "first_name": result.get("first_name", ""),
            "can_join_groups": result.get("can_join_groups", True),
        }
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="正在连接 Telegram 服务器，当前网络可能不通，请确保容器能访问外网后再试")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="连接等待时间较长，可能是网络延迟导致，点击重试看看")


@app.get("/api/bots")
async def list_bots(user=Depends(get_current_user)):
    bots = await get_bots()
    return {"bots": bots, "running_count": bot_manager.running_count}


@app.post("/api/bots")
async def add_bot(req: BotCreate, user=Depends(get_current_user)):
    bot_id = await create_bot(req.name, req.bot_token)
    if not bot_id:
        raise HTTPException(status_code=500, detail="创建失败")
    # 实时启动
    bot_manager.add_bot(bot_id, req.name, req.bot_token)
    return {"success": True, "id": bot_id}


@app.post("/api/bots/{bot_id}")
async def edit_bot(bot_id: int, req: BotUpdate, user=Depends(get_current_user)):
    kwargs = {}
    if req.name is not None: kwargs["name"] = req.name
    if req.bot_token is not None: kwargs["bot_token"] = req.bot_token
    if req.is_active is not None: kwargs["is_active"] = req.is_active
    if kwargs:
        ok = await update_bot(bot_id, **kwargs)
        if not ok:
            raise HTTPException(status_code=500, detail="更新失败")

    # 实时启停
    bot = await get_bot(bot_id)
    if bot:
        bot_manager.toggle_bot(bot_id, bool(bot["is_active"]), bot["bot_token"])
    return {"success": True}


@app.delete("/api/bots/{bot_id}")
async def remove_bot(bot_id: int, user=Depends(get_current_user)):
    # 先停止
    bot_manager.remove_bot(bot_id)
    ok = await delete_bot(bot_id)
    if not ok:
        raise HTTPException(status_code=500, detail="删除失败")
    return {"success": True}


# ===== 模型配置 CRUD =====

@app.get("/api/models/{model_id}")
async def get_model_detail(model_id: int, user=Depends(get_current_user)):
    """获取单个模型详情，返回真实 API Key（编辑时用）。"""
    m = await get_model_config(model_id)
    if not m:
        raise HTTPException(status_code=404, detail="模型不存在")
    return {
        "id": m["id"], "name": m["name"], "provider": m["provider"],
        "api_key": m["api_key"], "base_url": m["base_url"],
        "model_name": m["model_name"], "is_enabled": bool(m["is_enabled"]),
        "sort_order": m["sort_order"],
    }


@app.get("/api/models")
async def get_models(user=Depends(get_current_user)):
    models = await get_model_configs()
    primary_id_str = await get_setting("primary_model_id", "")
    primary_model_id = int(primary_id_str) if primary_id_str and primary_id_str.isdigit() else None
    if not primary_model_id and models:
        primary_model_id = models[0]["id"]  # 无配置时默认第一个
    from utils.helpers import supports_vision
    return {
        "models": [
            {
                "id": m["id"],
                "name": m["name"],
                "provider": m["provider"],
                "api_key": "***" + m["api_key"][-4:] if len(m["api_key"]) > 4 else "",
                "has_api_key": bool(m["api_key"]),
                "base_url": m["base_url"],
                "model_name": m["model_name"],
                "is_enabled": bool(m["is_enabled"]),
                "sort_order": m["sort_order"],
                "is_primary": m["id"] == primary_model_id,
                "capabilities": json.loads(m.get("capabilities", "{}") or "{}") if m.get("capabilities") else {},
            }
            for m in models
        ],
        "primary": llm_manager.primary,
        "primary_model_id": primary_model_id,
    }


@app.post("/api/models/{model_id}")
async def update_model(model_id: int, req: dict, user=Depends(get_current_user)):
    kwargs = {}
    for key in ["name", "provider", "api_key", "base_url", "model_name", "is_enabled", "sort_order"]:
        if key in req and req[key] is not None:
            if key == "api_key" and req[key].startswith("***"):
                continue
            kwargs[key] = req[key]
    if kwargs:
        ok = await update_model_config(model_id, **kwargs)
        if not ok:
            raise HTTPException(status_code=500, detail="更新失败")
    await llm_manager.reload()
    return {"success": True}


async def _test_model_availability(provider: str, api_key: str, base_url: str, model_name: str) -> bool:
    """检测模型是否可用：发一个轻量请求。"""
    try:
        from core.llm import _create_backend
        config = {"provider": provider, "api_key": api_key, "base_url": base_url.rstrip("/"),
                  "model_name": model_name, "name": "Detect"}
        backend = _create_backend(config)
        await backend.chat([{"role": "user", "content": "hi"}], max_tokens=1)
        return True
    except Exception as e:
        err = str(e)[:200]
        logger.warning(f"模型 {model_name} 可用性检测失败: {err}")
        if "location" in err.lower() or "FAILED_PRECONDITION" in err:
            logger.info(f"模型 {model_name} 可能是区域限制，不影响使用列表")
        return False


@app.post("/api/models/{model_id}/recheck")
async def recheck_model(model_id: int, user=Depends(get_current_user)):
    """重新检测模型可用性，更新 capabilities.available 并返回结果。"""
    m = await get_model_config(model_id)
    if not m:
        raise HTTPException(status_code=404, detail="模型不存在")
    if not m["api_key"] or not m["base_url"]:
        raise HTTPException(status_code=400, detail="请先配置 API Key 和 Base URL")
    try:
        caps = json.loads(m.get("capabilities") or "{}") if m.get("capabilities") else {}
    except Exception:
        caps = {}
    caps["available"] = await _test_model_availability(
        m["provider"], m["api_key"], m.get("base_url", ""), m["model_name"]
    )
    await update_model_config(model_id, capabilities=json.dumps(caps))
    await llm_manager.reload()
    return {"success": True, "available": caps["available"], "capabilities": caps}


@app.post("/api/models")
async def add_model(req: dict, user=Depends(get_current_user)):
    model_id = await add_model_config(req.get("name", "New Model"), req.get("provider", "openai"))
    if not model_id:
        raise HTTPException(status_code=500, detail="添加失败")
    # 补充保存其他字段（api_key、base_url、model_name、is_enabled）
    kwargs = {}
    for key in ["api_key", "base_url", "model_name"]:
        if key in req and req[key]:
            kwargs[key] = req[key]
    if "is_enabled" in req:
        kwargs["is_enabled"] = req["is_enabled"]
    if kwargs:
        await update_model_config(model_id, **kwargs)
    # 自动检测模型可用性
    model_name = req.get("model_name", "")
    api_key = req.get("api_key", "")
    base_url = req.get("base_url", "")
    provider = req.get("provider", "")
    if model_name:
        caps = {"vision": False, "available": False}
        if api_key and base_url:
            caps["available"] = await _test_model_availability(provider, api_key, base_url, model_name)
        try:
            await update_model_config(model_id, capabilities=json.dumps(caps))
        except Exception:
            pass  # 旧库无 capabilities 列时忽略
    # 第一次添加模型时自动设为主模型
    existing = await get_model_configs()
    if len(existing) == 1:
        await set_setting("primary_model_id", str(model_id))
    await llm_manager.reload()
    return {"success": True, "id": model_id}


@app.post("/api/models/{model_id}/set-primary")
async def set_primary_model(model_id: int, user=Depends(get_current_user)):
    """切换主模型：只改 primary_model_id，不改 sort_order。"""
    await set_setting("primary_model_id", str(model_id))
    await llm_manager.reload()
    return {"success": True, "primary_model_id": model_id}


@app.post("/api/models/{model_id}/vision")
async def toggle_model_vision(model_id: int, req: dict, user=Depends(get_current_user)):
    """手动切换模型视觉能力：绿色=支持，灰色=不支持。"""
    cfg = await get_model_config(model_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="模型不存在")
    try:
        caps = json.loads(cfg.get("capabilities") or "{}")
    except Exception:
        caps = {}
    caps["vision"] = bool(req.get("vision", not caps.get("vision", False)))
    await update_model_config(model_id, capabilities=json.dumps(caps))
    await llm_manager.reload()
    return {"success": True, "capabilities": caps}


@app.delete("/api/models/{model_id}")
async def remove_model(model_id: int, user=Depends(get_current_user)):
    ok = await delete_model_config(model_id)
    if not ok:
        raise HTTPException(status_code=500, detail="删除失败")
    await llm_manager.reload()
    return {"success": True}


# ===== 插件管理 =====

@app.get("/api/plugins")
async def get_plugins(user=Depends(get_current_user)):
    plugins = await get_plugin_configs()
    registry_plugins = plugin_registry.get_all()
    plugin_map = {p["name"]: p for p in plugins}

    # 合并 registry 的描述信息
    result = []
    seen = set()
    for p in plugins:
        info = {"name": p["name"], "enabled": bool(p["enabled"])}
        for rp in registry_plugins:
            if rp["name"] == p["name"]:
                info.update({
                    "description": rp["description"],
                    "manual_command": rp["manual_command"],
                    "auto_trigger": rp["auto_trigger"],
                })
                break
        result.append(info)
        seen.add(p["name"])

    # 补充 registry 中有但 DB 中没有的新插件
    for rp in registry_plugins:
        if rp["name"] not in seen:
            result.append({
                "name": rp["name"],
                "enabled": False,
                "description": rp["description"],
                "manual_command": rp["manual_command"],
                "auto_trigger": rp["auto_trigger"],
            })

    return {"plugins": result}


@app.post("/api/plugins/toggle")
async def toggle_plugin(req: PluginToggle, user=Depends(get_current_user)):
    await set_plugin_enabled(req.name, req.enabled)
    if req.enabled:
        plugin_registry.enable(req.name)
    else:
        plugin_registry.disable(req.name)
    return {"success": True}


# ===== 黑名单 =====

@app.get("/api/blacklist")
async def get_bl(user=Depends(get_current_user)):
    return {"blacklist": await get_blacklist()}


@app.post("/api/blacklist/add")
async def add_bl(req: BlacklistReq, user=Depends(get_current_user)):
    await add_blacklist(req.user_id, req.reason)
    return {"success": True}


@app.post("/api/blacklist/remove")
async def remove_bl(req: BlacklistReq, user=Depends(get_current_user)):
    await remove_blacklist(req.user_id)
    return {"success": True}


# ===== 会话 =====

@app.get("/api/sessions")
async def get_sessions(user=Depends(get_current_user)):
    from storage.database import get_db
    from core.bot_manager import bot_manager
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM sessions ORDER BY updated_at DESC LIMIT 50")
        rows = await cursor.fetchall()
        sessions = [dict(r) for r in rows]

        # 解析缺失的 chat_title（历史数据）
        need_resolve = [s for s in sessions if not s.get("chat_title")]
        if need_resolve and bot_manager._apps:
            bot = next(iter(bot_manager._apps.values())).bot  # 用任意一个运行中的 Bot
            for s in need_resolve:
                try:
                    chat = await bot.get_chat(s["chat_id"])
                    title = chat.title if chat.type in ("group", "supergroup", "channel") else (
                        chat.first_name or f"@{chat.username}" if chat.username else str(s["chat_id"])
                    )
                    s["chat_title"] = title
                    await db.execute(
                        "UPDATE sessions SET chat_title = ? WHERE bot_id = ? AND chat_id = ?",
                        (title, s["bot_id"], s["chat_id"])
                    )
                except Exception:
                    pass  # Bot 可能不在该群/无权限，保持空值
            await db.commit()

        return {"sessions": sessions}
    finally:
        await db.close()


@app.delete("/api/sessions/{chat_id}")
async def delete_session(chat_id: str, user=Depends(get_current_user)):
    # 清空该 chat_id 下所有 bot 的会话
    from storage.database import get_db
    db = await get_db()
    try:
        await db.execute("DELETE FROM conversations WHERE chat_id = ?", (chat_id,))
        await db.execute("DELETE FROM sessions WHERE chat_id = ?", (chat_id,))
        await db.commit()
    finally:
        await db.close()
    return {"success": True}


# ===== 诊断 =====

@app.get("/api/diagnostics")
async def diagnostics(user=Depends(get_current_user)):
    """Bot 连接状态诊断。"""
    from core.bot_manager import bot_manager
    from storage.database import get_bots

    bots = await get_bots()
    active_bots = [b for b in bots if b["is_active"]]
    running = bot_manager.running_count

    result = {
        "total_bots": len(bots),
        "active_bots": len(active_bots),
        "running_instances": running,
        "bots": [],
    }

    for b in bots:
        info = {
            "id": b["id"],
            "name": b["name"],
            "is_active": bool(b["is_active"]),
            "is_running": b["id"] in [k for k in bot_manager._apps if k == b["id"]],
            "checks": [],
        }

        token = b.get("bot_token", "")
        if not token:
            info["checks"].append({"item": "Token", "ok": False, "msg": "未配置 Token"})
        else:
            info["checks"].append({"item": "Token", "ok": True, "msg": "已配置"})

        if bool(b["is_active"]):
            if info["is_running"]:
                info["checks"].append({"item": "轮询状态", "ok": True, "msg": "正在运行"})
            else:
                info["checks"].append({"item": "轮询状态", "ok": False, "msg": "未启动（可能是 Conflict）"})
        else:
            info["checks"].append({"item": "轮询状态", "ok": None, "msg": "Bot 已禁用"})

        result["bots"].append(info)

    return result


# ===== 统计 =====

@app.get("/api/stats")
async def get_stats_api(days: int = 7, user=Depends(get_current_user)):
    return await get_stats(days)


# ===== 静态文件 =====

frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))
