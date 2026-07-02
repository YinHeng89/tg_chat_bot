# 🤖 TG AI Chat Bot

> 轻量级 Telegram AI 聊天机器人，支持多 Bot 管理、多模型切换、插件扩展和 Web 管理面板。

---

## 功能总览

| 功能 | 说明 |
|------|------|
| 🤖 **多 Bot 管理** | Web 面板热添加/删除/启停多个 Bot，每个 Bot 独立配置 |
| 🧠 **多模型支持** | OpenAI / Claude / DeepSeek / Ollama 等 12+ 提供商，主备自动切换 |
| 💬 **智能对话** | 私聊自动回复，群聊 @提及或 `/chat` 触发，独立会话记忆 |
| 🧩 **插件系统** | 9 个内置连接器，支持 AI 自动调用 + 手动命令 |
| 🌐 **联网搜索** | DuckDuckGo 实时搜索 |
| 🖼️ **图片理解** | 多模态模型分析图片内容 |
| 🎨 **图片生成** | AI 文生图（DALL·E 等） |
| 📝 **Memos 备忘录** | 查询/创建/编辑备忘录，AI 可读写 |
| ⚙️ **Web 管理面板** | React 前端可视化配置模型、插件、Bot、个性设定 |
| 🛡️ **安全管控** | JWT 认证、黑名单、频率限制、白名单模式 |

---

## 目录结构

```
tg_chat_bot/
├── main.py                     # 启动入口
├── requirements.txt            # Python 依赖
├── Dockerfile                  # 多阶段构建（前端+后端）
├── docker-compose.yml          # 开发环境
├── docker-compose.prod.yml     # 生产环境
├── publish.sh                  # 多架构镜像构建发布脚本
├── .env.example                # 环境变量模板
├── .env                        # 实际配置（不提交）
│
├── bot/                        # Telegram Bot 层
│   ├── handler.py              # 消息路由分发
│   ├── commands.py             # 命令处理
│   ├── conversation.py         # 对话逻辑编排
│   └── filters.py              # 自定义过滤器
│
├── core/                       # 核心逻辑层
│   ├── llm.py                  # LLM 管理器（多模型抽象）
│   ├── memory.py               # 会话记忆管理
│   ├── config.py               # 核心配置
│   └── bot_manager.py          # 多 Bot 实例管理
│
├── plugins/                    # 连接器（插件）
│   ├── base.py                 # 插件基类
│   ├── registry.py             # 插件注册中心
│   ├── web_search.py           # 联网搜索
│   ├── url_summary.py          # 链接内容总结
│   ├── weather.py              # 天气查询
│   ├── calculator.py           # 数学计算器
│   ├── translate.py            # 翻译
│   ├── image_understand.py     # 图片理解
│   ├── image_gen.py            # 图片生成
│   ├── code_runner.py          # 代码沙箱执行
│   └── memos.py                # Memos 备忘录
│
├── storage/                    # 存储层
│   ├── database.py             # SQLite 数据库操作
│   └── models.py               # 表结构和初始数据
│
├── utils/                      # 工具
│   ├── logger.py               # 日志配置
│   └── helpers.py              # 通用函数
│
├── web/                        # FastAPI 后端
│   ├── api.py                  # REST API
│   └── auth.py                 # JWT 认证
│
└── frontend/                   # React 前端（Vite）
    └── src/
        ├── App.jsx             # 路由和布局
        ├── pages/              # 页面组件
        │   ├── Dashboard.jsx   # 仪表盘
        │   ├── Bots.jsx        # Bot 管理
        │   ├── ModelConfig.jsx # 模型配置
        │   ├── Connectors.jsx  # 插件管理
        │   ├── Settings.jsx    # 全局设置
        │   ├── Personality.jsx # 个性配置
        │   ├── Blacklist.jsx   # 黑名单
        │   ├── Sessions.jsx    # 会话查看
        │   └── Diagnostics.jsx # 系统诊断
        └── components/         # 通用组件
```

---

## 快速开始

### 前置条件

- Python 3.10+
- Telegram Bot Token（[BotFather](https://t.me/BotFather) 创建获取）
- LLM API Key（OpenAI / DeepSeek 等）

### Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone <repo-url>
cd tg_chat_bot

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入真实值

# 3. 启动
docker compose -f docker-compose.yml up -d
```

### 本地开发

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 构建前端（首次或修改前端后）
cd frontend && npm install && npm run build && cd ..

# 3. 启动
python main.py
```

访问 `http://localhost:8000` 进入 Web 管理面板。

---

## 环境变量

```ini
# 管理面板
WEB_JWT_SECRET=openssl rand -hex 32 生成
WEB_ADMIN_PASSWORD=你的管理密码

# Memos 备忘录（可选）
MEMOS_API_URL=https://你的memos地址
MEMOS_API_KEY=你的memos API Key
```

> 模型配置（API Key / Base URL 等）在 Web 面板中管理，无需手动填写 `.env`。

---

## Web 管理面板

| 页面 | 功能 |
|------|------|
| **仪表盘** | 7天/30天统计、Token 消耗、活跃会话数 |
| **Bot 管理** | 添加/删除/启停 Bot，验证 Token |
| **模型配置** | 添加多个 LLM 提供商，设主模型+备用 fallback |
| **连接器** | 9 个插件的启用/禁用开关，AI 自动调用或手动命令 |
| **个性设定** | 配置 Bot 角色（贴心伙伴/技术专家/创意达人/知识导师/自定义） |
| **黑名单** | 拉黑/解除用户 |
| **系统诊断** | Bot 连接状态、Token 配置检查 |
| **会话查看** | 查看近期对话记录 |

---

## 内置连接器

| 连接器 | 自动调用 | 手动命令 | 功能 |
|--------|:------:|----------|------|
| `web_search` | ✅ | `/search` | DuckDuckGo 联网搜索 |
| `url_summary` | ✅ | - | 自动识别 URL 并提取摘要 |
| `weather` | ✅ | `/weather` | wttr.in 天气查询 |
| `calculator` | ✅ | `/calc` | 数学表达式计算 |
| `translate` | ✅ | `/translate` | 多语言翻译 |
| `image_understand` | ✅ | - | 多模态图片分析 |
| `image_gen` | ✅ | `/draw` | AI 文生图 |
| `code_runner` | ✅ | - | 代码沙箱执行 |
| `memos` | ✅ | `/memos` | Memos 备忘录读写 |

---

## 命令列表

### 通用命令

| 命令 | 说明 |
|------|------|
| `/start` | 开始对话 |
| `/help` | 查看帮助 |
| `/chat <内容>` | 群聊中触发对话 |
| `/clear` | 清空当前会话上下文 |
| `/history` | 查看最近 10 条对话历史 |
| `/status` | 查看 Bot 运行状态（模型/插件/Token） |

### 连接器命令

| 命令 | 说明 |
|------|------|
| `/search <关键词>` | 联网搜索 |
| `/weather <城市>` | 天气查询 |
| `/translate <内容>` | 翻译 |
| `/calc <表达式>` | 计算器 |
| `/draw <描述>` | AI 生成图片 |
| `/connectors` | 查看所有连接器状态 |

### 管理员命令

| 命令 | 说明 |
|------|------|
| `/admin` | 管理员面板（最近 7 天统计） |
| `/switch_model <模型>` | 切换默认模型 |
| `/list_models` | 查看所有模型状态 |
| `/stats [天数]` | 查看使用统计，默认 7 天 |
| `/blacklist add/remove <ID>` | 黑名单管理 |
| `/connector enable/disable <名称>` | 启用/禁用连接器 |

---

## 编写自定义连接器

```python
# plugins/my_plugin.py
from plugins.base import BasePlugin

class MyPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "my_plugin"

    @property
    def description(self) -> str:
        return "我的自定义连接器"

    @property
    def auto_trigger(self) -> bool:
        return True

    @property
    def manual_command(self) -> str:
        return "mycmd"

    async def execute(self, params: dict, context=None) -> str:
        query = params.get("query", "")
        return f"处理结果: {query}"
```

然后在 `plugins/registry.py` 的 `_register_builtin()` 中注册即可。

---

## 部署

### Docker Compose

```bash
# 开发环境
docker compose -f docker-compose.yml up -d

# 生产环境（使用预构建镜像）
docker compose -f docker-compose.prod.yml up -d
```

### 数据持久化

- 数据库：`tg_bot_data/data/`
- 日志：`tg_bot_data/logs/`
- 工作区：`tg_bot_data/workspace/`

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 框架 | python-telegram-bot v21+ |
| Web 后端 | FastAPI + JWT |
| Web 前端 | React + Vite |
| LLM | openai SDK（兼容 OpenAI API 格式） |
| 存储 | SQLite (aiosqlite) |
| 搜索 | DuckDuckGo |
| HTTP | httpx |
| 日志 | loguru |
| 部署 | Docker + Docker Compose |

---

## 路线图

- [x] 多 Bot 热管理
- [x] 多模型支持 + 备用 fallback
- [x] Web 管理面板
- [x] 插件系统（Function Calling）
- [x] 会话记忆隔离（bot_id + chat_id）
- [x] 群聊智能回复
- [x] 频率限制 / 黑名单
- [x] 个性角色配置
- [x] Memos 备忘录连接器
- [x] Docker 多架构部署
- [ ] RAG 知识库集成
- [ ] 语音消息支持

---

## 许可证

MIT License
