class MessageContext:
    
    def __init__(self, client, event, chat_id, rule):
        self.client = client
        self.event = event
        self.chat_id = chat_id
        self.rule = rule
        
        message = getattr(event, 'message', None)
        message_text = message.text if message and hasattr(message, 'text') else ''
        
        self.original_message_text = message_text
        self.message_text = message_text
        self.check_message_text = message_text
        
        self.media_files = []
        self.sender_info = ''
        self.time_info = ''
        self.original_link = ''
        
        self.buttons = message.buttons if message and hasattr(message, 'buttons') else None
        
        self.should_forward = True
        self.processing_failed = False
        self.media_blocked = False
        
        grouped_id = message.grouped_id if message and hasattr(message, 'grouped_id') else None
        self.is_media_group = grouped_id is not None
        self.media_group_id = grouped_id
        self.media_group_messages = []
        self.ai_media_messages = []
        self.primary_message = message
        
        self.skipped_media = []
        self.errors = []
        self.forwarded_messages = []
        self.comment_link = None