"""自定义过滤器。"""

from telegram import Chat


def is_group_chat(chat: Chat) -> bool:
    """判断是否为群聊。"""
    return chat.type in ("group", "supergroup")


def is_private_chat(chat: Chat) -> bool:
    """判断是否为私聊。"""
    return chat.type == "private"


def is_channel(chat: Chat) -> bool:
    """判断是否为频道。"""
    return chat.type == "channel"
