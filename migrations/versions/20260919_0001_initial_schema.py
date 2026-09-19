"""Establish the current schema as the Alembic baseline."""

from alembic import op
import sqlalchemy as sa

from enums.enums import AddMode, ForwardMode, HandleMode, MessageMode, PreviewMode


revision = '20260919_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'chats',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('telegram_chat_id', sa.String(), nullable=False, unique=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('current_add_id', sa.String(), nullable=True),
    )
    op.create_table(
        'forward_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_chat_id', sa.Integer(), sa.ForeignKey('chats.id'), nullable=False),
        sa.Column('target_chat_id', sa.Integer(), sa.ForeignKey('chats.id'), nullable=False),
        sa.Column('forward_mode', sa.Enum(ForwardMode), nullable=False),
        sa.Column('message_mode', sa.Enum(MessageMode), nullable=False),
        sa.Column('is_replace', sa.Boolean(), nullable=True),
        sa.Column('is_preview', sa.Enum(PreviewMode), nullable=False),
        sa.Column('is_original_link', sa.Boolean(), nullable=True),
        sa.Column('is_delete_original', sa.Boolean(), nullable=True),
        sa.Column('is_original_sender', sa.Boolean(), nullable=True),
        sa.Column('userinfo_template', sa.String(), nullable=True),
        sa.Column('time_template', sa.String(), nullable=True),
        sa.Column('original_link_template', sa.String(), nullable=True),
        sa.Column('is_original_time', sa.Boolean(), nullable=True),
        sa.Column('add_mode', sa.Enum(AddMode), nullable=False),
        sa.Column('enable_rule', sa.Boolean(), nullable=True),
        sa.Column('is_filter_user_info', sa.Boolean(), nullable=True),
        sa.Column('handle_mode', sa.Enum(HandleMode), nullable=False),
        sa.Column('enable_comment_button', sa.Boolean(), nullable=True),
        sa.Column('enable_media_type_filter', sa.Boolean(), nullable=True),
        sa.Column('enable_media_size_filter', sa.Boolean(), nullable=True),
        sa.Column('max_media_size', sa.Integer(), nullable=True),
        sa.Column('is_send_over_media_size_message', sa.Boolean(), nullable=True),
        sa.Column('enable_extension_filter', sa.Boolean(), nullable=True),
        sa.Column('extension_filter_mode', sa.Enum(AddMode), nullable=False),
        sa.Column('enable_reverse_blacklist', sa.Boolean(), nullable=True),
        sa.Column('enable_reverse_whitelist', sa.Boolean(), nullable=True),
        sa.Column('media_allow_text', sa.Boolean(), nullable=True),
        sa.Column('media_caption_filter', sa.Boolean(), nullable=True),
        sa.Column('is_ai', sa.Boolean(), nullable=True),
        sa.Column('ai_model', sa.String(), nullable=True),
        sa.Column('ai_prompt', sa.String(), nullable=True),
        sa.Column('enable_ai_upload_image', sa.Boolean(), nullable=True),
        sa.Column('is_summary', sa.Boolean(), nullable=True),
        sa.Column('summary_time', sa.String(length=5), nullable=True),
        sa.Column('summary_prompt', sa.String(), nullable=True),
        sa.Column('is_keyword_after_ai', sa.Boolean(), nullable=True),
        sa.Column('is_top_summary', sa.Boolean(), nullable=True),
        sa.Column('enable_delay', sa.Boolean(), nullable=True),
        sa.Column('delay_seconds', sa.Integer(), nullable=True),
        sa.Column('enable_sync', sa.Boolean(), nullable=True),
        sa.UniqueConstraint('source_chat_id', 'target_chat_id', name='unique_source_target'),
    )
    op.create_table(
        'keywords',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('forward_rules.id'), nullable=False),
        sa.Column('keyword', sa.String(), nullable=True),
        sa.Column('is_regex', sa.Boolean(), nullable=True),
        sa.Column('is_blacklist', sa.Boolean(), nullable=True),
        sa.UniqueConstraint(
            'rule_id', 'keyword', 'is_regex', 'is_blacklist',
            name='unique_rule_keyword_is_regex_is_blacklist',
        ),
    )
    op.create_table(
        'replace_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('forward_rules.id'), nullable=False),
        sa.Column('pattern', sa.String(), nullable=False),
        sa.Column('content', sa.String(), nullable=True),
        sa.UniqueConstraint('rule_id', 'pattern', 'content', name='unique_rule_pattern_content'),
    )
    op.create_table(
        'media_types',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('forward_rules.id'), nullable=False, unique=True),
        sa.Column('photo', sa.Boolean(), nullable=True),
        sa.Column('document', sa.Boolean(), nullable=True),
        sa.Column('video', sa.Boolean(), nullable=True),
        sa.Column('audio', sa.Boolean(), nullable=True),
        sa.Column('voice', sa.Boolean(), nullable=True),
    )
    op.create_table(
        'media_extensions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('forward_rules.id'), nullable=False),
        sa.Column('extension', sa.String(), nullable=False),
        sa.UniqueConstraint('rule_id', 'extension', name='unique_rule_extension'),
    )
    op.create_table(
        'rule_syncs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('forward_rules.id'), nullable=False),
        sa.Column('sync_rule_id', sa.Integer(), nullable=False),
    )


def downgrade():
    op.drop_table('rule_syncs')
    op.drop_table('media_extensions')
    op.drop_table('media_types')
    op.drop_table('replace_rules')
    op.drop_table('keywords')
    op.drop_table('forward_rules')
    op.drop_table('chats')
