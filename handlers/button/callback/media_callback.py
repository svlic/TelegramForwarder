import traceback

from handlers.button.button_helpers import create_media_size_buttons,create_media_settings_buttons,create_media_types_buttons,create_media_extensions_buttons
from models.models import ForwardRule, RuleSync
import logging
from utils.common import get_media_settings_text, get_db_ops

logger = logging.getLogger(__name__)


async def _refresh_media_settings(event, rule):
    await event.edit(await get_media_settings_text(), buttons=await create_media_settings_buttons(rule))


async def _toggle_media_rule_flag(event, session, rule_id, *, field_name, status_text, sync_log_label):
    rule = session.get(ForwardRule, int(rule_id))
    if not rule:
        await event.answer("规则不存在")
        return

    new_value = not getattr(rule, field_name)
    setattr(rule, field_name, new_value)

    if rule.enable_sync:
        logger.info(f"规则 {rule.id} 启用了同步功能，正在同步{sync_log_label}设置到关联规则")
        sync_rules = session.query(RuleSync).filter(RuleSync.rule_id == rule.id).all()
        for sync_rule in sync_rules:
            sync_rule_id = sync_rule.sync_rule_id
            target_rule = session.get(ForwardRule, sync_rule_id)
            if not target_rule:
                logger.warning(f"同步目标规则 {sync_rule_id} 不存在，跳过")
                continue

            try:
                setattr(target_rule, field_name, new_value)
                logger.info(f"同步规则 {sync_rule_id} 的{sync_log_label}设置已更新为 {new_value}")
            except Exception as e:
                logger.error(f"同步{sync_log_label}设置到规则 {sync_rule_id} 时出错: {str(e)}")
                continue

    session.commit()
    await _refresh_media_settings(event, rule)
    status = "开启" if new_value else "关闭"
    await event.answer(f"已{status}{status_text}")


async def callback_media_settings(event, rule_id, session, message, data):
    rule = session.get(ForwardRule, int(rule_id))
    if rule:
        await _refresh_media_settings(event, rule)
    return





async def callback_set_max_media_size(event, rule_id, session, message, data):
        await event.edit("请选择最大媒体大小(MB)：", buttons=await create_media_size_buttons(rule_id, page=0))
        return



async def callback_select_max_media_size(event, rule_id, session, message, data):
        parts = data.split(':', 2)
        if len(parts) == 3:
            _, rule_id, size = parts
            logger.info(f"设置规则 {rule_id} 的最大媒体大小为: {size}")
            rule = session.get(ForwardRule, int(rule_id))
            if rule:
                old_size = rule.max_media_size
                rule.max_media_size = int(size)
                session.commit()
                logger.info(f"数据库更新成功: {old_size} -> {size}")

                if rule.enable_sync:
                    logger.info(f"规则 {rule.id} 启用了同步功能，正在同步媒体大小设置到关联规则")
                    sync_rules = session.query(RuleSync).filter(RuleSync.rule_id == rule.id).all()

                    for sync_rule in sync_rules:
                        sync_rule_id = sync_rule.sync_rule_id
                        logger.info(f"正在同步媒体大小到规则 {sync_rule_id}")

                        target_rule = session.get(ForwardRule, sync_rule_id)
                        if not target_rule:
                            logger.warning(f"同步目标规则 {sync_rule_id} 不存在，跳过")
                            continue

                        try:
                            old_target_size = target_rule.max_media_size
                            target_rule.max_media_size = int(size)
                            logger.info(f"同步规则 {sync_rule_id} 的媒体大小从 {old_target_size} 到 {size}")
                        except Exception as e:
                            logger.error(f"同步媒体大小到规则 {sync_rule_id} 时出错: {str(e)}")
                            continue

                    session.commit()
                    logger.info("所有同步媒体大小更改已提交")

                await _refresh_media_settings(event, rule)
                await event.answer(f"已设置最大媒体大小为: {size}MB")
                logger.info("界面更新完成")
        return






async def callback_set_media_types(event, rule_id, session, message, data):
    rule = session.get(ForwardRule, int(rule_id))
    if not rule:
        await event.answer("规则不存在")
        return

    db_ops = await get_db_ops()
    success, msg, media_types = await db_ops.get_media_types(session, rule.id)

    if not success:
        await event.answer(f"获取媒体类型设置失败: {msg}")
        return

    await event.edit("请选择要屏蔽的媒体类型", buttons=await create_media_types_buttons(rule.id, media_types))

    return

async def callback_toggle_media_type(event, rule_id, session, message, data):
    try:
        parts = data.split(':')
        if len(parts) < 3:
            await event.answer("数据格式错误")
            return
        _ = parts[0]
        rule_id = parts[1]
        media_type = parts[2]
        if media_type not in ['photo', 'document', 'video', 'audio', 'voice']:
            await event.answer(f"无效的媒体类型: {media_type}")
            return

        rule = session.get(ForwardRule, int(rule_id))
        if not rule:
            await event.answer("规则不存在")
            return

        db_ops = await get_db_ops()
        success, msg = await db_ops.toggle_media_type(session, rule.id, media_type)

        if not success:
            await event.answer(f"切换媒体类型失败: {msg}")
            return

        if rule.enable_sync:
            logger.info(f"规则 {rule.id} 启用了同步功能，正在同步媒体类型设置到关联规则")

            success, _, current_media_types = await db_ops.get_media_types(session, rule.id)
            if not success:
                logger.warning("获取媒体类型设置失败，无法同步")
            else:
                sync_rules = session.query(RuleSync).filter(RuleSync.rule_id == rule.id).all()

                for sync_rule in sync_rules:
                    sync_rule_id = sync_rule.sync_rule_id
                    logger.info(f"正在同步媒体类型 {media_type} 到规则 {sync_rule_id}")

                    target_rule = session.get(ForwardRule, sync_rule_id)
                    if not target_rule:
                        logger.warning(f"同步目标规则 {sync_rule_id} 不存在，跳过")
                        continue

                    try:
                        target_success, _, target_media_types = await db_ops.get_media_types(session, sync_rule_id)
                        if not target_success:
                            logger.warning(f"获取目标规则 {sync_rule_id} 的媒体类型设置失败，跳过")
                            continue

                        current_type_status = getattr(current_media_types, media_type)

                        if getattr(target_media_types, media_type) != current_type_status:
                            if current_type_status:
                                if not getattr(target_media_types, media_type):
                                    await db_ops.toggle_media_type(session, sync_rule_id, media_type)
                                    logger.info(f"同步规则 {sync_rule_id} 的媒体类型 {media_type} 已开启")
                            else:
                                if getattr(target_media_types, media_type):
                                    await db_ops.toggle_media_type(session, sync_rule_id, media_type)
                                    logger.info(f"同步规则 {sync_rule_id} 的媒体类型 {media_type} 已关闭")
                        else:
                            logger.info(f"目标规则 {sync_rule_id} 的媒体类型 {media_type} 状态已经是 {current_type_status}，无需更改")

                    except Exception as e:
                        logger.error(f"同步媒体类型到规则 {sync_rule_id} 时出错: {str(e)}")
                        continue

        success, _, media_types = await db_ops.get_media_types(session, rule.id)

        if not success:
            await event.answer("获取媒体类型设置失败")
            return

        await event.edit("请选择要屏蔽的媒体类型", buttons=await create_media_types_buttons(rule.id, media_types))
        await event.answer(msg)

    except Exception as e:
        logger.error(f"切换媒体类型时出错: {str(e)}")
        logger.error(f"错误详情: {traceback.format_exc()}")
        await event.answer(f"切换媒体类型时出错: {str(e)}")
    return


async def callback_set_media_extensions(event, rule_id, session, message, data):
    await event.edit("请选择要过滤的媒体扩展名：", buttons=await create_media_extensions_buttons(rule_id, page=0))
    return


async def callback_media_extensions_page(event, rule_id, session, message, data):
    _, rule_id, page = data.split(':')
    page = int(page)
    await event.edit("请选择要过滤的媒体扩展名：", buttons=await create_media_extensions_buttons(rule_id, page=page))
    return

async def callback_toggle_media_extension(event, rule_id, session, message, data):
    try:
        parts = data.split(':')
        if len(parts) < 3:
            await event.answer("数据格式错误")
            return
        _ = parts[0]
        rule_id = parts[1]
        extension = parts[2]

        current_page = 0
        if len(parts) > 3 and parts[3].isdigit():
            current_page = int(parts[3])

        rule = session.get(ForwardRule, int(rule_id))
        if not rule:
            await event.answer("规则不存在")
            return

        db_ops = await get_db_ops()
        selected_extensions = await db_ops.get_media_extensions(session, rule.id)
        selected_extension_list = [ext["extension"] for ext in selected_extensions]

        was_selected = extension in selected_extension_list
        if was_selected:
            extension_id = next((ext["id"] for ext in selected_extensions if ext["extension"] == extension), None)
            if extension_id:
                success, msg = await db_ops.delete_media_extensions(session, rule.id, [extension_id])
                if success:
                    await event.answer(f"已移除扩展名: {extension}")

                    if rule.enable_sync:
                        logger.info(f"规则 {rule.id} 启用了同步功能，正在同步媒体扩展名移除到关联规则")

                        sync_rules = session.query(RuleSync).filter(RuleSync.rule_id == rule.id).all()

                        for sync_rule in sync_rules:
                            sync_rule_id = sync_rule.sync_rule_id
                            logger.info(f"正在同步移除媒体扩展名 {extension} 到规则 {sync_rule_id}")

                            target_rule = session.get(ForwardRule, sync_rule_id)
                            if not target_rule:
                                logger.warning(f"同步目标规则 {sync_rule_id} 不存在，跳过")
                                continue

                            try:
                                target_extensions = await db_ops.get_media_extensions(session, sync_rule_id)
                                target_extension_list = [ext["extension"] for ext in target_extensions]

                                if extension in target_extension_list:
                                    target_extension_id = next((ext["id"] for ext in target_extensions if ext["extension"] == extension), None)
                                    if target_extension_id:
                                        await db_ops.delete_media_extensions(session, sync_rule_id, [target_extension_id])
                                        logger.info(f"同步规则 {sync_rule_id} 的媒体扩展名 {extension} 已移除")
                                    else:
                                        logger.warning(f"目标规则 {sync_rule_id} 中找不到扩展名 {extension} 的ID")
                                else:
                                    logger.info(f"目标规则 {sync_rule_id} 中不存在扩展名 {extension}，无需删除")
                            except Exception as e:
                                logger.error(f"同步移除媒体扩展名到规则 {sync_rule_id} 时出错: {str(e)}")
                                continue
                else:
                    await event.answer(f"移除扩展名失败: {msg}")
        else:
            success, msg = await db_ops.add_media_extensions(session, rule.id, [extension])
            if success:
                await event.answer(f"已添加扩展名: {extension}")

                if rule.enable_sync:
                    logger.info(f"规则 {rule.id} 启用了同步功能，正在同步媒体扩展名添加到关联规则")

                    sync_rules = session.query(RuleSync).filter(RuleSync.rule_id == rule.id).all()

                    for sync_rule in sync_rules:
                        sync_rule_id = sync_rule.sync_rule_id
                        logger.info(f"正在同步添加媒体扩展名 {extension} 到规则 {sync_rule_id}")

                        target_rule = session.get(ForwardRule, sync_rule_id)
                        if not target_rule:
                            logger.warning(f"同步目标规则 {sync_rule_id} 不存在，跳过")
                            continue

                        try:
                            target_extensions = await db_ops.get_media_extensions(session, sync_rule_id)
                            target_extension_list = [ext["extension"] for ext in target_extensions]

                            if extension not in target_extension_list:
                                await db_ops.add_media_extensions(session, sync_rule_id, [extension])
                                logger.info(f"同步规则 {sync_rule_id} 的媒体扩展名 {extension} 已添加")
                            else:
                                logger.info(f"目标规则 {sync_rule_id} 中已存在扩展名 {extension}，无需添加")
                        except Exception as e:
                            logger.error(f"同步添加媒体扩展名到规则 {sync_rule_id} 时出错: {str(e)}")
                            continue
            else:
                await event.answer(f"添加扩展名失败: {msg}")

        await event.edit("请选择要过滤的媒体扩展名：", buttons=await create_media_extensions_buttons(rule_id, page=current_page))

    except Exception as e:
        logger.error(f"切换媒体扩展名时出错: {str(e)}")
        logger.error(f"错误详情: {traceback.format_exc()}")
        await event.answer(f"切换媒体扩展名时出错: {str(e)}")
    return

async def callback_toggle_media_allow_text(event, rule_id, session, message, data):
    try:
        await _toggle_media_rule_flag(
            event,
            session,
            rule_id,
            field_name="media_allow_text",
            status_text="放行文本",
            sync_log_label="'放行文本'",
        )
    except Exception as e:
        logger.error(f"切换放行文本设置时出错: {str(e)}")
        logger.error(f"错误详情: {traceback.format_exc()}")
        await event.answer(f"切换放行文本设置时出错: {str(e)}")
    return

async def callback_toggle_media_caption_filter(event, rule_id, session, message, data):
    try:
        await _toggle_media_rule_flag(
            event,
            session,
            rule_id,
            field_name="media_caption_filter",
            status_text="Caption过滤",
            sync_log_label="Caption过滤",
        )
    except Exception as e:
        logger.error(f"切换Caption过滤设置时出错: {str(e)}")
        await event.answer(f"切换Caption过滤设置时出错: {str(e)}")
    return
