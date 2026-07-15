from sqlalchemy import text
from models.models import Keyword, ReplaceRule, ForwardRule, MediaTypes, MediaExtensions, RuleSync, get_db_session
import logging
from enums.enums import AddMode

logger = logging.getLogger(__name__)


class DBOperations:
    @classmethod
    async def create(cls):
        """创建DBOperations实例"""
        return cls()

    def _get_sync_rules(self, session, rule_id):
        return [sr.sync_rule_id for sr in session.query(RuleSync).filter(RuleSync.rule_id == rule_id).all()]

    async def _iterate_sync_targets(self, session, rule_id, operation_name):
        for sync_rule_id in self._get_sync_rules(session, rule_id):
            target_rule = session.get(ForwardRule, sync_rule_id)
            if not target_rule:
                logger.warning(f"Sync target rule {sync_rule_id} not found, skipping")
                continue
            logger.info(f"{operation_name} to rule {sync_rule_id}")
            yield sync_rule_id

    async def add_keywords(self, session, rule_id, keywords, is_regex=False, is_blacklist=False):
        """添加关键字到规则

        Args:
            session: 数据库会话
            rule_id: 规则ID
            keywords: 关键字列表
            is_regex: 是否是正则表达式
            is_blacklist: 是否为黑名单关键字

        Returns:
            tuple: (成功数量, 重复数量)
        """
        success_count = 0
        duplicate_count = 0

        # 获取当前规则
        rule = session.get(ForwardRule, rule_id)
        if not rule:
            logger.error(f"规则ID {rule_id} 不存在")
            return 0, 0

        # 处理单个规则的关键字添加
        for keyword in keywords:
            existing_keyword = session.query(Keyword).filter(
                Keyword.rule_id == rule_id,
                Keyword.keyword == keyword,
                Keyword.is_regex == is_regex,
                Keyword.is_blacklist == is_blacklist
            ).first()

            if existing_keyword:
                duplicate_count += 1
                continue

            new_keyword = Keyword(
                rule_id=rule_id,
                keyword=keyword,
                is_regex=is_regex,
                is_blacklist=is_blacklist
            )
            session.add(new_keyword)
            success_count += 1

        # Sync to linked rules if enabled
        if rule.enable_sync:
            logger.info(f"Rule {rule_id} sync enabled, syncing keywords to linked rules")
            async for sync_rule_id in self._iterate_sync_targets(session, rule_id, "Syncing keywords"):
                sync_success, sync_duplicate = 0, 0
                for keyword in keywords:
                    try:
                        existing = session.query(Keyword).filter(
                            Keyword.rule_id == sync_rule_id,
                            Keyword.keyword == keyword,
                            Keyword.is_regex == is_regex,
                            Keyword.is_blacklist == is_blacklist
                        ).first()
                        if existing:
                            sync_duplicate += 1
                            continue
                        session.add(Keyword(
                            rule_id=sync_rule_id,
                            keyword=keyword,
                            is_regex=is_regex,
                            is_blacklist=is_blacklist
                        ))
                        session.flush()
                        sync_success += 1
                    except Exception as e:
                        logger.error(f"Sync keyword to rule {sync_rule_id} error: {str(e)}")
                logger.info(f"Sync rule {sync_rule_id}: success={sync_success}, duplicate={sync_duplicate}")

        return success_count, duplicate_count

    async def get_keywords_all(self, session, rule_id):
        return session.query(Keyword).filter(
            Keyword.rule_id == rule_id
        ).all()

    async def get_keywords(self, session, rule_id, add_mode):
        return session.query(Keyword).filter(
            Keyword.rule_id == rule_id,
            Keyword.is_blacklist == (add_mode == 'blacklist')
        ).all()

    async def delete_keywords(self, session, rule_id, indices):
        """删除指定索引的关键字

        Args:
            session: 数据库会话
            rule_id: 规则ID
            indices: 要删除的索引列表（1-based）

        Returns:
            tuple: (删除数量, 剩余关键字列表)
        """
        # 获取当前规则
        rule = session.get(ForwardRule, rule_id)
        if not rule:
            logger.error(f"规则ID {rule_id} 不存在")
            return 0, []

        # 获取当前规则的关键字
        keywords = await self.get_keywords(session, rule_id, 'blacklist' if rule.add_mode == AddMode.BLACKLIST else 'whitelist')
        if not keywords:
            return 0, []

        deleted_count = 0
        max_id = len(keywords)

        unique_indices = sorted(set(indices), reverse=True)

        # 保存要删除的关键字信息，用于后续同步
        keywords_to_delete = []
        for idx in unique_indices:
            if 1 <= idx <= max_id:
                keyword = keywords[idx - 1]
                keywords_to_delete.append({
                    'keyword': keyword.keyword,
                    'is_regex': keyword.is_regex,
                    'is_blacklist': keyword.is_blacklist
                })
                session.delete(keyword)
                deleted_count += 1

        # Sync deletion to linked rules if enabled
        if rule.enable_sync and keywords_to_delete:
            logger.info(f"Rule {rule_id} sync enabled, syncing deletion to linked rules")
            async for sync_rule_id in self._iterate_sync_targets(session, rule_id, "Syncing keyword deletion"):
                sync_deleted = 0
                for kw_info in keywords_to_delete:
                    try:
                        for target_kw in session.query(Keyword).filter(
                            Keyword.rule_id == sync_rule_id,
                            Keyword.keyword == kw_info['keyword'],
                            Keyword.is_regex == kw_info['is_regex'],
                            Keyword.is_blacklist == kw_info['is_blacklist']
                        ).all():
                            session.delete(target_kw)
                            sync_deleted += 1
                    except Exception as e:
                        logger.error(f"Sync delete keyword from rule {sync_rule_id} error: {str(e)}")
                logger.info(f"Sync delete from rule {sync_rule_id}: deleted {sync_deleted}")

        return deleted_count, await self.get_keywords(session, rule_id, 'blacklist' if rule.add_mode == AddMode.BLACKLIST else 'whitelist')

    async def add_replace_rules(self, session, rule_id, patterns, contents=None):
        """添加替换规则

        Args:
            session: 数据库会话
            rule_id: 规则ID
            patterns: 匹配模式列表
            contents: 替换内容列表（可选）

        Returns:
            tuple: (成功数量, 重复数量)
        """
        # 获取当前规则
        rule = session.get(ForwardRule, rule_id)
        if not rule:
            logger.error(f"规则ID {rule_id} 不存在")
            return 0, 0

        success_count = 0
        duplicate_count = 0

        if contents is None:
            contents = [''] * len(patterns)

        # 添加替换规则到主规则
        added_rules = []  # 存储成功添加的规则，用于后续同步
        for pattern, content in zip(patterns, contents):
            # 检查是否已存在相同的替换规则
            existing_rule = session.query(ReplaceRule).filter(
                ReplaceRule.rule_id == rule_id,
                ReplaceRule.pattern == pattern,
                ReplaceRule.content == content
            ).first()

            if existing_rule:
                duplicate_count += 1
                continue

            new_rule = ReplaceRule(
                rule_id=rule_id,
                pattern=pattern,
                content=content
            )
            session.add(new_rule)
            success_count += 1
            added_rules.append({'pattern': pattern, 'content': content})

        # Sync to linked rules if enabled
        if rule.enable_sync and added_rules:
            logger.info(f"Rule {rule_id} sync enabled, syncing replace rules to linked rules")
            async for sync_rule_id in self._iterate_sync_targets(session, rule_id, "Syncing replace rules"):
                sync_success, sync_duplicate = 0, 0
                for rule_info in added_rules:
                    try:
                        existing = session.query(ReplaceRule).filter(
                            ReplaceRule.rule_id == sync_rule_id,
                            ReplaceRule.pattern == rule_info['pattern'],
                            ReplaceRule.content == rule_info['content']
                        ).first()
                        if existing:
                            sync_duplicate += 1
                            continue
                        session.add(ReplaceRule(
                            rule_id=sync_rule_id,
                            pattern=rule_info['pattern'],
                            content=rule_info['content']
                        ))
                        session.flush()
                        sync_success += 1
                    except Exception as e:
                        logger.error(f"Sync replace rule to rule {sync_rule_id} error: {str(e)}")
                logger.info(f"Sync rule {sync_rule_id}: success={sync_success}, duplicate={sync_duplicate}")

        return success_count, duplicate_count

    async def get_replace_rules(self, session, rule_id):
        """获取规则的所有替换规则

        Args:
            session: 数据库会话
            rule_id: 规则ID

        Returns:
            list: 替换规则列表
        """
        return session.query(ReplaceRule).filter(
            ReplaceRule.rule_id == rule_id
        ).all()

    async def delete_replace_rules(self, session, rule_id, indices):
        """删除指定索引的替换规则

        Args:
            session: 数据库会话
            rule_id: 规则ID
            indices: 要删除的索引列表（1-based）

        Returns:
            tuple: (删除数量, 剩余替换规则列表)
        """
        # 获取当前规则
        rule = session.get(ForwardRule, rule_id)
        if not rule:
            logger.error(f"规则ID {rule_id} 不存在")
            return 0, []

        rules = await self.get_replace_rules(session, rule_id)
        if not rules:
            return 0, []

        deleted_count = 0
        max_id = len(rules)

        unique_indices = sorted(set(indices), reverse=True)

        # 保存要删除的替换规则信息，用于后续同步
        rules_to_delete = []
        for idx in unique_indices:
            if 1 <= idx <= max_id:
                replace_rule = rules[idx - 1]
                rules_to_delete.append({
                    'pattern': replace_rule.pattern,
                    'content': replace_rule.content
                })
                session.delete(replace_rule)
                deleted_count += 1

        # Sync deletion to linked rules if enabled
        if rule.enable_sync and rules_to_delete:
            logger.info(f"Rule {rule_id} sync enabled, syncing replace rule deletion to linked rules")
            async for sync_rule_id in self._iterate_sync_targets(session, rule_id, "Syncing replace rule deletion"):
                sync_deleted = 0
                for rule_info in rules_to_delete:
                    try:
                        for target_rule in session.query(ReplaceRule).filter(
                            ReplaceRule.rule_id == sync_rule_id,
                            ReplaceRule.pattern == rule_info['pattern'],
                            ReplaceRule.content == rule_info['content']
                        ).all():
                            session.delete(target_rule)
                            sync_deleted += 1
                    except Exception as e:
                        logger.error(f"Sync delete replace rule from rule {sync_rule_id} error: {str(e)}")
                logger.info(f"Sync delete from rule {sync_rule_id}: deleted {sync_deleted}")

        return deleted_count, await self.get_replace_rules(session, rule_id)

    async def get_media_types(self, session, rule_id):
        """获取媒体类型设置"""
        try:
            rule = session.get(ForwardRule, rule_id)
            if not rule:
                return False, "规则不存在", None

            media_types = session.query(MediaTypes).filter_by(rule_id=rule_id).first()
            if not media_types:
                # 如果不存在则创建默认设置
                media_types = MediaTypes(
                    rule_id=rule_id,
                    photo=False,
                    document=False,
                    video=False,
                    audio=False,
                    voice=False
                )
                session.add(media_types)
                session.commit()

            return True, "获取媒体类型设置成功", media_types
        except Exception as e:
            logger.error(f"获取媒体类型设置时出错: {str(e)}")
            session.rollback()
            return False, f"获取媒体类型设置时出错: {str(e)}", None

    async def update_media_types(self, session, rule_id, media_types_dict):
        """更新媒体类型设置"""
        try:
            rule = session.get(ForwardRule, rule_id)
            if not rule:
                return False, "规则不存在"

            media_types = session.query(MediaTypes).filter_by(rule_id=rule_id).first()
            if not media_types:
                media_types = MediaTypes(rule_id=rule_id)
                session.add(media_types)

            # 更新媒体类型设置
            for field in ['photo', 'document', 'video', 'audio', 'voice']:
                if field in media_types_dict:
                    setattr(media_types, field, media_types_dict[field])

            session.commit()
            return True, "更新媒体类型设置成功"
        except Exception as e:
            logger.error(f"更新媒体类型设置时出错: {str(e)}")
            session.rollback()
            return False, f"更新媒体类型设置时出错: {str(e)}"

    async def toggle_media_type(self, session, rule_id, media_type):
        """切换特定媒体类型的启用状态"""
        try:
            if media_type not in ['photo', 'document', 'video', 'audio', 'voice']:
                return False, f"无效的媒体类型: {media_type}"

            success, msg, media_types = await self.get_media_types(session, rule_id)
            if not success:
                return False, msg

            # 切换状态
            current_value = getattr(media_types, media_type)
            setattr(media_types, media_type, not current_value)

            session.commit()
            return True, f"媒体类型 {media_type} 切换为 {not current_value}"
        except Exception as e:
            logger.error(f"切换媒体类型时出错: {str(e)}")
            session.rollback()
            return False, f"切换媒体类型时出错: {str(e)}"

    async def add_media_extensions(self, session, rule_id, extensions):
        """添加媒体扩展名

        Args:
            session: 数据库会话
            rule_id: 规则ID
            extensions: 扩展名列表，比如 ['jpg', 'png', 'pdf']

        Returns:
            (bool, str): 成功状态和消息
        """
        try:
            added_count = 0
            for ext in extensions:
                # 确保扩展名不带点，去除可能存在的点
                ext = ext.lstrip('.')

                # 检查是否已存在相同的扩展名
                existing = session.execute(
                    text("SELECT id FROM media_extensions WHERE rule_id = :rule_id AND extension = :extension"),
                    {"rule_id": rule_id, "extension": ext}
                )

                if existing.first() is None:
                    # 添加新的扩展名
                    new_extension = MediaExtensions(rule_id=rule_id, extension=ext)
                    session.add(new_extension)
                    added_count += 1

            if added_count > 0:
                session.commit()
                return True, f"成功添加 {added_count} 个媒体扩展名"
            else:
                return False, "所有扩展名已存在，未添加任何新扩展名"

        except Exception as e:
            session.rollback()
            logger.error(f"添加媒体扩展名失败: {str(e)}")
            return False, f"添加媒体扩展名失败: {str(e)}"

    async def get_media_extensions(self, session, rule_id):
        """获取规则的媒体扩展名列表

        Args:
            session: 数据库会话
            rule_id: 规则ID

        Returns:
            list: 媒体扩展名对象列表
        """
        try:
            # 使用SQLAlchemy文本SQL查询，不需要await
            result = session.execute(
                text("SELECT id, extension FROM media_extensions WHERE rule_id = :rule_id ORDER BY id"),
                {"rule_id": rule_id}
            )

            # 构建返回结果
            extensions = []
            for row in result:
                extensions.append({
                    "id": row[0],
                    "extension": row[1]
                })

            # 返回扩展名列表
            return extensions

        except Exception as e:
            # 记录错误并返回空列表
            logger.error(f"获取媒体扩展名失败: {str(e)}")
            return []

    async def delete_media_extensions(self, session, rule_id, indices):
        """删除媒体扩展名

        Args:
            session: 数据库会话
            rule_id: 规则ID
            indices: 要删除的扩展名ID列表

        Returns:
            (bool, str): 成功状态和消息
        """
        try:
            if not indices:
                return False, "未指定要删除的扩展名"

            for index in indices:
                # 查找并删除扩展名
                result = session.execute(
                    text("SELECT id FROM media_extensions WHERE id = :id AND rule_id = :rule_id"),
                    {"id": index, "rule_id": rule_id}
                )

                extension = result.first()
                if extension:
                    session.execute(
                        text("DELETE FROM media_extensions WHERE id = :id"),
                        {"id": extension[0]}
                    )

            session.commit()
            return True, f"成功删除 {len(indices)} 个媒体扩展名"
        except Exception as e:
            session.rollback()
            logger.error(f"删除媒体扩展名失败: {str(e)}")
            return False, f"删除媒体扩展名失败: {str(e)}"

    # 规则同步相关操作
    async def add_rule_sync(self, session, rule_id, sync_rule_id):
        """添加规则同步关系

        Args:
            session: 数据库会话
            rule_id: 源规则ID
            sync_rule_id: 目标规则ID（要同步到的规则）

        Returns:
            tuple: (bool, str) - (成功状态, 消息)
        """
        try:
            # 检查源规则是否存在
            source_rule = session.get(ForwardRule, rule_id)
            if not source_rule:
                return False, f"源规则ID {rule_id} 不存在"

            # 检查目标规则是否存在
            target_rule = session.get(ForwardRule, sync_rule_id)
            if not target_rule:
                return False, f"目标规则ID {sync_rule_id} 不存在"

            # 检查是否已存在相同的同步关系
            existing_sync = session.query(RuleSync).filter(
                RuleSync.rule_id == rule_id,
                RuleSync.sync_rule_id == sync_rule_id
            ).first()

            if existing_sync:
                return False, "同步关系已存在"

            # 创建新的同步关系
            new_sync = RuleSync(
                rule_id=rule_id,
                sync_rule_id=sync_rule_id
            )

            # 启用规则的同步功能
            source_rule.enable_sync = True

            session.add(new_sync)
            session.commit()

            logger.info(f"已添加规则同步: 从规则 {rule_id} 到规则 {sync_rule_id}")
            return True, "成功添加同步关系"

        except Exception as e:
            session.rollback()
            logger.error(f"添加规则同步关系时出错: {str(e)}")
            return False, f"添加同步关系失败: {str(e)}"

    async def get_rule_syncs(self, session, rule_id):
        """获取指定规则的同步关系列表

        Args:
            session: 数据库会话
            rule_id: 规则ID

        Returns:
            list: 同步关系列表
        """
        try:
            # 获取该规则的所有同步目标
            syncs = session.query(RuleSync).filter(
                RuleSync.rule_id == rule_id
            ).all()

            return syncs

        except Exception as e:
            logger.error(f"获取规则同步关系时出错: {str(e)}")
            return []

    async def delete_rule_sync(self, session, rule_id, sync_rule_id):
        """删除规则同步关系

        Args:
            session: 数据库会话
            rule_id: 源规则ID
            sync_rule_id: 目标规则ID

        Returns:
            tuple: (bool, str) - (成功状态, 消息)
        """
        try:
            # 查找同步关系
            sync = session.query(RuleSync).filter(
                RuleSync.rule_id == rule_id,
                RuleSync.sync_rule_id == sync_rule_id
            ).first()

            if not sync:
                return False, "指定的同步关系不存在"

            # 删除同步关系
            session.delete(sync)

            # 检查规则是否还有其他同步关系
            remaining_syncs = session.query(RuleSync).filter(
                RuleSync.rule_id == rule_id
            ).count()

            # 如果没有其他同步关系，关闭规则的同步功能
            if remaining_syncs == 0:
                rule = session.get(ForwardRule, rule_id)
                if rule:
                    rule.enable_sync = False

            session.commit()

            logger.info(f"已删除规则同步: 从规则 {rule_id} 到规则 {sync_rule_id}")
            return True, "成功删除同步关系"

        except Exception as e:
            session.rollback()
            logger.error(f"删除规则同步关系时出错: {str(e)}")
            return False, f"删除同步关系失败: {str(e)}"
