import logging
import traceback
from filters.base_filter import BaseFilter
from filters.context import MessageContext

logger = logging.getLogger(__name__)

class FilterChain:
    """
    过滤器链，用于组织和执行多个过滤器
    """
    
    def __init__(self):
        self.filters = []
        
    def add_filter(self, filter_obj):
        if not isinstance(filter_obj, BaseFilter):
            raise TypeError("过滤器必须是BaseFilter的子类")
        self.filters.append(filter_obj)
        return self
        
    async def process(self, client, event, chat_id, rule):
        context = MessageContext(client, event, chat_id, rule)
        
        logger.info(f"开始过滤器链处理，共 {len(self.filters)} 个过滤器")
        
        for filter_obj in self.filters:
            try:
                should_continue = await filter_obj.process(context)
                if not should_continue:
                    logger.info(f"过滤器 {filter_obj.name} 中断了处理链")
                    return False
            except Exception as e:
                logger.error(f"过滤器 {filter_obj.name} 处理出错: {str(e)}")
                logger.debug(f"异常堆栈:\n{traceback.format_exc()}")
                context.errors.append({
                    'filter': filter_obj.name,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
                context.processing_failed = True
                context.should_forward = False
                return False
        
        if context.should_forward:
            logger.info("过滤器链处理完成，将转发消息")
        else:
            logger.info("过滤器链处理完成，消息不满足转发条件")
        return context.should_forward