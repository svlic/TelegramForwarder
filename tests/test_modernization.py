import os
import tempfile
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

import ai
from ai.openai_base_provider import CustomOpenAIProvider
from message_listener import handle_user_message
from models import models
from models.models import Base, Chat, ForwardRule
from utils import constants


class ConfigValidationTests(unittest.TestCase):
    def test_validate_config_rejects_invalid_timezone(self):
        environment = {
            'USER_ID': '123',
            'ADMINS': '',
            'CUSTOM_AI_API_KEY': '',
            'CUSTOM_AI_API_BASE': '',
        }
        with (
            patch.dict(os.environ, environment, clear=True),
            patch.object(constants, 'API_ID', '100'),
            patch.object(constants, 'API_HASH', 'hash'),
            patch.object(constants, 'PHONE_NUMBER', '+8613800000000'),
            patch.object(constants, 'BOT_TOKEN', 'token'),
            patch.object(constants, 'DEFAULT_TIMEZONE', 'Not/AZone'),
            patch.object(constants, 'AI_MODELS', []),
        ):
            with self.assertRaisesRegex(ValueError, 'IANA'):
                constants.validate_config()


class AIProviderLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        ai._provider = None

    async def test_factory_reuses_provider_and_close_releases_client(self):
        first = await ai.get_ai_provider()
        second = await ai.get_ai_provider()
        self.assertIs(first, second)

        client = MagicMock()
        client.close = AsyncMock()
        first.client = client
        await first.close()

        client.close.assert_awaited_once_with()
        self.assertIsNone(first.client)

    async def test_model_is_selected_per_request(self):
        async def response_stream():
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content='ok'))]
            )

        create = AsyncMock(side_effect=[response_stream(), response_stream()])
        provider = CustomOpenAIProvider()
        provider.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )

        self.assertEqual(await provider.process_message('one', model='model-a'), 'ok')
        self.assertEqual(await provider.process_message('two', model='model-b'), 'ok')
        self.assertEqual(create.await_args_list[0].kwargs['model'], 'model-a')
        self.assertEqual(create.await_args_list[1].kwargs['model'], 'model-b')


class AlembicInitializationTests(unittest.TestCase):
    def tearDown(self):
        models.dispose_db()

    def test_new_database_is_created_and_versioned(self):
        with tempfile.TemporaryDirectory() as directory:
            database_url = f"sqlite:///{os.path.join(directory, 'forward.db')}"
            with patch.object(models, 'DATABASE_URL', database_url):
                engine = models.init_db()
                tables = set(inspect(engine).get_table_names())
                self.assertEqual(
                    tables,
                    set(Base.metadata.tables) | {'alembic_version'},
                )
                with engine.connect() as connection:
                    version = connection.exec_driver_sql(
                        'SELECT version_num FROM alembic_version'
                    ).scalar_one()
                self.assertEqual(version, '20260919_0001')

    def test_existing_unversioned_database_is_preserved_and_stamped(self):
        with tempfile.TemporaryDirectory() as directory:
            database_url = f"sqlite:///{os.path.join(directory, 'legacy.db')}"
            legacy_engine = create_engine(database_url)
            Base.metadata.create_all(legacy_engine)
            LegacySession = sessionmaker(bind=legacy_engine)
            with LegacySession() as session:
                session.add(Chat(telegram_chat_id='123', name='preserved'))
                session.commit()
            legacy_engine.dispose()

            with patch.object(models, 'DATABASE_URL', database_url):
                engine = models.init_db()
                with engine.connect() as connection:
                    version = connection.exec_driver_sql(
                        'SELECT version_num FROM alembic_version'
                    ).scalar_one()
                    name = connection.exec_driver_sql(
                        "SELECT name FROM chats WHERE telegram_chat_id = '123'"
                    ).scalar_one()

                self.assertEqual(version, '20260919_0001')
                self.assertEqual(name, 'preserved')


class ForwardSessionBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_forwarding_starts_after_database_session_closes(self):
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        with Session() as session:
            source = Chat(telegram_chat_id='123', name='source')
            target = Chat(telegram_chat_id='456', name='target')
            session.add_all([source, target])
            session.flush()
            session.add(ForwardRule(source_chat_id=source.id, target_chat_id=target.id))
            session.commit()

        closed = {'value': False}

        @contextmanager
        def tracked_session():
            session = Session()
            try:
                yield session
            finally:
                session.close()
                closed['value'] = True

        async def assert_closed_before_forward(*_args):
            self.assertTrue(closed['value'])
            return True

        event = SimpleNamespace(
            message=SimpleNamespace(grouped_id=None, text='hello'),
            get_chat=AsyncMock(return_value=SimpleNamespace(id=123)),
        )
        with (
            patch('message_listener.get_db_session', tracked_session),
            patch('message_listener._handle_pending_state', AsyncMock(return_value=False)),
            patch('message_listener.process_forward_rule', side_effect=assert_closed_before_forward),
        ):
            await handle_user_message(event, bot_client=object())

        engine.dispose()


if __name__ == '__main__':
    unittest.main()
