import logging
from filters.filter_chain import FilterChain
from filters.keyword_filter import KeywordFilter
from filters.replace_filter import ReplaceFilter
from filters.ai_filter import AIFilter
from filters.info_filter import InfoFilter
from filters.media_filter import MediaFilter
from filters.sender_filter import SenderFilter

from filters.delay_filter import DelayFilter
from filters.edit_filter import EditFilter
from filters.comment_button_filter import CommentButtonFilter
from filters.init_filter import InitFilter
from filters.reply_filter import ReplyFilter
from filters.text_normalize_filter import TextNormalizeFilter
logger = logging.getLogger(__name__)

async def process_forward_rule(client, event, chat_id, rule):
    """
    处理转发规则

    Args:
        client: 机器人客户端
        event: 消息事件
        chat_id: 聊天ID
        rule: 转发规则

    Returns:
        bool: 处理是否成功
    """
    logger.info(f'使用过滤器链处理规则 ID: {rule.id}')

    # 创建过滤器链
    filter_chain = FilterChain()

    for filter_instance in (
        InitFilter(),
        DelayFilter(),
        TextNormalizeFilter(),
        KeywordFilter(),
        ReplaceFilter(),
        MediaFilter(),
        AIFilter(),
        InfoFilter(),
        CommentButtonFilter(),
        EditFilter(),
        SenderFilter(),
        ReplyFilter(),
    ):
        filter_chain.add_filter(filter_instance)

    # 执行过滤器链
    result = await filter_chain.process(client, event, chat_id, rule)

    return result
