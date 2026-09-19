import logging
from models.models import get_db_session, ForwardRule, RuleSync
from managers.state_manager import state_manager
from utils.common import get_ai_settings_text, get_bot_client
from handlers.button.button_helpers import create_ai_settings_buttons, create_other_settings_buttons
from utils.auto_delete import async_delete_user_message
logger = logging.getLogger(__name__)

async def handle_prompt_setting(event, client, sender_id, chat_id, current_state, message):
    """处理设置提示词的逻辑"""
    logger.info(f"开始处理提示词设置,用户ID:{sender_id},聊天ID:{chat_id},当前状态:{current_state}")
    
    if not current_state:
        logger.info("当前无状态,返回False")
        return False

    rule_id = None
    field_name = None 
    prompt_type = None
    template_type = None

    if current_state.startswith("set_summary_prompt:"):
        rule_id = current_state.split(":")[1]
        field_name = "summary_prompt"
        prompt_type = "AI总结"
        template_type = "ai"
        logger.info(f"检测到设置总结提示词,规则ID:{rule_id}")
    elif current_state.startswith("set_ai_prompt:"):
        rule_id = current_state.split(":")[1]
        field_name = "ai_prompt"
        prompt_type = "AI"
        template_type = "ai"
        logger.info(f"检测到设置AI提示词,规则ID:{rule_id}")
    elif current_state.startswith("set_ai_model:"):
        rule_id = current_state.split(":")[1]
        field_name = "ai_model"
        prompt_type = "AI模型"
        template_type = "ai"
        logger.info(f"检测到设置AI模型,规则ID:{rule_id}")
    elif current_state.startswith("set_userinfo_template:"):
        rule_id = current_state.split(":")[1]
        field_name = "userinfo_template"
        prompt_type = "用户信息"
        template_type = "userinfo"
        logger.info(f"检测到设置用户信息模板,规则ID:{rule_id}")
    elif current_state.startswith("set_time_template:"):
        rule_id = current_state.split(":")[1]
        field_name = "time_template"
        prompt_type = "时间"
        template_type = "time"
        logger.info(f"检测到设置时间模板,规则ID:{rule_id}")
    elif current_state.startswith("set_original_link_template:"):
        rule_id = current_state.split(":")[1]
        field_name = "original_link_template"
        prompt_type = "原始链接"
        template_type = "link"
        logger.info(f"检测到设置原始链接模板,规则ID:{rule_id}")
    else:
        logger.info(f"未知的状态类型:{current_state}")
        return False

    logger.info(f"处理设置{prompt_type}提示词/模板,规则ID:{rule_id},字段名:{field_name}")
    with get_db_session() as session:
        logger.info(f"查询规则ID:{rule_id}")
        rule = session.get(ForwardRule, int(rule_id))
        if not rule:
            logger.warning(f"未找到规则ID:{rule_id}")
            return True

        old_prompt = getattr(rule, field_name) if hasattr(rule, field_name) else None
        new_prompt = event.message.text
        logger.info(f"找到规则,原提示词/模板长度:{len(old_prompt) if old_prompt else 0}")
        logger.info(f"准备更新为新提示词/模板长度:{len(new_prompt) if new_prompt else 0}")
        setattr(rule, field_name, new_prompt)

        if rule.enable_sync:
            sync_rules = session.query(RuleSync).filter(RuleSync.rule_id == rule.id).all()
            for sync_rule in sync_rules:
                target_rule = session.get(ForwardRule, sync_rule.sync_rule_id)
                if target_rule:
                    setattr(target_rule, field_name, new_prompt)
        session.commit()

    logger.info(f"已更新规则{rule_id}的{prompt_type}提示词/模板")
    await state_manager.clear_state(sender_id, chat_id)

    message_chat_id = event.message.chat_id
    bot_client = await get_bot_client()
    try:
        await async_delete_user_message(bot_client, message_chat_id, event.message.id, 0)
    except Exception as e:
        logger.error(f"删除用户消息失败: {str(e)}")

    await message.delete()
    logger.info("准备发送更新后的设置消息")
    if template_type == "ai":
        await client.send_message(
            chat_id,
            await get_ai_settings_text(rule),
            buttons=await create_ai_settings_buttons(rule)
        )
    elif template_type in ["userinfo", "time", "link"]:
        await client.send_message(
            chat_id,
            f"已更新规则 {rule_id} 的{prompt_type}模板",
            buttons=await create_other_settings_buttons(rule_id=rule_id)
        )

    logger.info("设置消息发送成功")
    return True
