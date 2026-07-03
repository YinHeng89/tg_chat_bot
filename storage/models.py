"""数据模型定义 — SQLite 表结构和数据类。"""

from dataclasses import dataclass, field

# ===== 数据库表结构 SQL =====

CREATE_TABLES_SQL = """
-- 对话历史（bot_id + chat_id 隔离）
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id INTEGER DEFAULT 0,
    chat_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    model TEXT DEFAULT '',
    tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 会话摘要（bot_id + chat_id 隔离）
CREATE TABLE IF NOT EXISTS sessions (
    bot_id INTEGER DEFAULT 0,
    chat_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    model TEXT DEFAULT '',
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (bot_id, chat_id)
);

-- 机器人实例
CREATE TABLE IF NOT EXISTS bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT '',
    bot_token TEXT NOT NULL DEFAULT '',
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 使用统计
CREATE TABLE IF NOT EXISTS stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    model TEXT DEFAULT '',
    tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 黑名单
CREATE TABLE IF NOT EXISTS blacklist (
    user_id INTEGER PRIMARY KEY,
    reason TEXT DEFAULT '',
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 模型配置（主模型 + 备用模型）
CREATE TABLE IF NOT EXISTS model_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT '',
    provider TEXT NOT NULL DEFAULT 'openai',
    api_key TEXT DEFAULT '',
    base_url TEXT DEFAULT '',
    model_name TEXT DEFAULT '',
    is_enabled INTEGER DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    capabilities TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 全局设置（Key-Value）
CREATE TABLE IF NOT EXISTS bot_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插件设置
CREATE TABLE IF NOT EXISTS plugin_configs (
    name TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    config TEXT DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 默认设置（贴心伙伴角色的全局默认值，新 Bot 自动继承）
INSERT OR IGNORE INTO bot_settings (key, value) VALUES
    ('bot_name', 'AI 助手'),
    ('personality_role', 'companion'),
    ('soul', '["friendly","concise","warm"]'),
    ('identity', '我是你的贴心伙伴，一个友善热心的聊天助手。'),
    ('user_context', '用户希望轻松愉快地聊天，不喜欢太正式或太冷淡的回复。'),
    ('bot_system_prompt', '用温暖的语气回复，适当使用表情符号。如果用户情绪低落，主动安慰和鼓励。'),
    ('group_auto_reply', 'true'),
    ('group_reply_mode', 'mentioned'),
    ('max_history', '20'),
    ('rate_limit', '10'),
    ('whitelist_mode', 'false'),
    ('enabled_plugins', '["web_search","url_summary","weather","calculator","translate","image_understand","cli","memos"]'),
    ('search_engine', 'duckduckgo'),
    ('admin_ids', '[]');

-- 所有角色默认数据（全局，新 Bot 未自定义时继承）
INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('persona_roles', '{"companion":{"soul":["friendly","concise","warm"],"identity":"我是你的贴心伙伴，一个友善热心的聊天助手。","userContext":"用户希望轻松愉快地聊天，不喜欢太正式或太冷淡的回复。","systemPrompt":"用温暖的语气回复，适当使用表情符号。如果用户情绪低落，主动安慰和鼓励。"},"expert":{"soul":["professional","detailed","logical"],"identity":"我是一个专业技术顾问，擅长深度分析和严谨解答。","userContext":"用户是技术人员，追求准确性和深度，反感敷衍的回答。","systemPrompt":"回答要有理有据，引用可靠来源。遇到不确定的信息要明确说明。使用结构化格式（如分点、表格）呈现复杂信息。"},"creative":{"soul":["humorous","creative","enthusiastic"],"identity":"我是一个创意达人，风趣幽默，充满奇思妙想。","userContext":"用户喜欢新颖有趣的内容，讨厌千篇一律的套话。","systemPrompt":"多用比喻、故事和生动的例子来表达观点。适当加入幽默和网络流行语。鼓励用户跳出常规思维。"},"mentor":{"soul":["patient","detailed","warm"],"identity":"我是你的知识导师，耐心细致，善于引导和讲解。","userContext":"用户是学习者，需要循序渐进地理解知识，不喜欢被直接给答案。","systemPrompt":"用苏格拉底式提问引导用户思考。把复杂概念拆解成简单的步骤。多用类比帮助理解。对用户的进步给予肯定和鼓励。"},"custom":{"soul":[],"identity":"","userContext":"","systemPrompt":""}}');

-- 默认插件列表
INSERT OR IGNORE INTO plugin_configs (name, enabled) VALUES
    ('web_search', 1),
    ('url_summary', 1),
    ('weather', 1),
    ('calculator', 1),
    ('translate', 1),
    ('image_understand', 1),
    ('image_gen', 0),
    ('cli', 1),
    ('memos', 1);

CREATE INDEX IF NOT EXISTS idx_conversations_bot_chat ON conversations(bot_id, chat_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_stats_user_id ON stats(user_id);
CREATE INDEX IF NOT EXISTS idx_stats_created_at ON stats(created_at);
"""


@dataclass
class Message:
    """单条对话消息。"""
    role: str
    content: str
    model: str = ""
    tokens: int = 0


@dataclass
class Conversation:
    """一次对话会话。"""
    chat_id: str
    user_id: int
    messages: list[Message] = field(default_factory=list)
    model: str = ""
    message_count: int = 0
    total_tokens: int = 0

    def to_api_format(self, system_prompt: str = "") -> list[dict]:
        result = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        for msg in self.messages:
            result.append({"role": msg.role, "content": msg.content})
        return result



