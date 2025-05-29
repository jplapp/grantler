import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from database import BotDatabase
from zulip_client import ZulipClient
from vertex_ai_client import VertexAIClient

class ZulipBot:
    def __init__(self, zulip_email: str, zulip_api_key: str, zulip_site: str, 
                 gcp_project: str, gcp_location: str, 
                 vertex_model: str = "gemini-1.5-pro", style_instructions: Optional[str] = None,
                 channel_filter: Optional[str] = None):
        self.db = BotDatabase()
        self.zulip = ZulipClient(zulip_email, zulip_api_key, zulip_site)
        self.ai = VertexAIClient(gcp_project, gcp_location, vertex_model, style_instructions)
        self.user_id = self.zulip.user_id
        self.channel_filter = channel_filter
        self.logger = logging.getLogger(__name__)
        
        # Get user's full name for AI context
        self.user_name = self._get_user_name()
    
    def _get_user_name(self) -> str:
        """Get the user's full name from Zulip."""
        try:
            result = self.zulip.client.get_profile()
            if result['result'] == 'success':
                return result.get('full_name', 'User')
            else:
                self.logger.error(f"Failed to get user profile: {result.get('msg', 'Unknown error')}")
                return os.getenv('USER_FULL_NAME', 'User')
        except Exception as e:
            self.logger.error(f"Error getting user name: {e}")
            return os.getenv('USER_FULL_NAME', 'User')
    
    def process_unread_messages_and_create_drafts(self):
        """Feature 1: Fetch all recent messages and create/update drafts for all conversations."""
        self.logger.info("Processing all recent conversations and creating drafts...")
        
        # Get all recent messages (not just unread)
        all_recent_messages = self.zulip.get_all_recent_messages(channel_filter=self.channel_filter)
        
        # Skip private messages if we're filtering by channel
        if self.channel_filter:
            all_messages = all_recent_messages
            self.logger.info(f"Filtering to channel: {self.channel_filter}")
        else:
            all_private_messages = self.zulip.get_all_private_messages()
            all_messages = all_recent_messages + all_private_messages
        
        # Group messages by conversation thread
        conversations = self._group_messages_by_conversation(all_messages)
        
        for thread_key, messages in conversations.items():
            if not messages:
                continue
                
            latest_message = max(messages, key=lambda x: x['timestamp'])
            
            # Check if we already have a draft for this conversation
            existing_thread = self.db.get_conversation_thread(thread_key)
            
            # Skip if we already have a draft and no new messages since then
            if existing_thread and existing_thread.get('draft_id'):
                existing_last_message_id = existing_thread.get('last_message_id')
                if existing_last_message_id and existing_last_message_id >= latest_message['id']:
                    self.logger.debug(f"Skipping {thread_key} - already have draft and no new messages")
                    continue
            
            # Get full conversation context
            conversation_messages = self._get_conversation_context(messages[0])
            
            # Generate reply using AI
            context_text = self.ai._format_conversation_context(conversation_messages)
            conversation_type = "stream" if messages[0].get('type') == 'stream' else "private"
            
            reply_content = self.ai.generate_reply(context_text, self.user_name, conversation_type)
            
            if reply_content:
                # Create draft message
                draft_id = self._create_draft(messages[0], reply_content)
                
                if draft_id:
                    # Mark message as processed
                    self.db.mark_message_processed(
                        latest_message['id'],
                        latest_message.get('stream_id'),
                        latest_message.get('subject'),
                        latest_message['sender_id'],
                        str(latest_message['timestamp']),
                        draft_created=True
                    )
                    
                    # Update conversation thread
                    stream_id = latest_message.get('stream_id')
                    topic = latest_message.get('subject')
                    self.db.update_conversation_thread(
                        thread_key, stream_id, topic,
                        latest_message['id'], str(latest_message['timestamp']),
                        needs_reply=True, draft_id=draft_id
                    )
                    
                    self.logger.info(f"Created draft for conversation: {thread_key}")
                else:
                    self.logger.warning(f"Failed to create draft for conversation: {thread_key}")
    
    def generate_unread_summary(self) -> str:
        """Feature 2: Generate summary of unread messages and post to johannes_bot channel."""
        self.logger.info("Generating unread messages summary...")
        
        # Get all unread messages (excluding johannes_bot channel to avoid self-reference)
        unread_mentions = self.zulip.get_unread_messages(channel_filter=None)  # Get from all channels
        unread_privates = self.zulip.get_private_messages()
        all_unread = unread_mentions + unread_privates
        
        # Filter out messages from johannes_bot channel to avoid summarizing our own summaries
        filtered_unread = [msg for msg in all_unread if msg.get('display_recipient') != 'johannes_bot']
        
        if not filtered_unread:
            summary = "No unread messages to summarize."
        else:
            # Generate summary using AI
            summary = self.ai.generate_summary(filtered_unread, self.user_name)
            summary = summary or "Could not generate summary."
        
        # Create a unique topic name with timestamp
        from datetime import datetime
        topic = f"Summary {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Post summary to johannes_bot channel
        success = self.zulip.send_message("johannes_bot", topic, summary)
        
        if success:
            self.logger.info(f"Posted summary to johannes_bot channel in topic: {topic}")
            return f"Summary posted to johannes_bot channel in topic: {topic}"
        else:
            self.logger.error("Failed to post summary to johannes_bot channel")
            return summary  # Return the summary text if posting failed
    
    def check_open_conversations(self):
        """Feature 3: Check for open conversations requiring replies."""
        self.logger.info("Checking for open conversations requiring replies...")
        
        # Get all recent messages to check for conversations
        all_recent_messages = self.zulip.get_all_recent_messages(channel_filter=self.channel_filter)
        
        if self.channel_filter:
            all_messages = all_recent_messages
        else:
            all_private_messages = self.zulip.get_all_private_messages()
            all_messages = all_recent_messages + all_private_messages
        conversations = self._group_messages_by_conversation(all_messages)
        
        for thread_key, messages in conversations.items():
            if not messages:
                continue
            
            # Get full conversation to check if reply is needed
            conversation_messages = self._get_conversation_context(messages[0])
            
            needs_reply = self.zulip.needs_reply_in_thread(conversation_messages)
            
            if needs_reply:
                latest_message = max(conversation_messages, key=lambda x: x['timestamp'])
                stream_id = latest_message.get('stream_id')
                topic = latest_message.get('subject')
                
                # Update database to track this conversation
                self.db.update_conversation_thread(
                    thread_key, stream_id, topic,
                    latest_message['id'], str(latest_message['timestamp']),
                    needs_reply=True
                )
                
                self.logger.info(f"Found conversation needing reply: {thread_key}")
    
    def _group_messages_by_conversation(self, messages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group messages by conversation thread."""
        conversations = {}
        
        for msg in messages:
            thread_key = self._get_thread_key(msg)
            if thread_key not in conversations:
                conversations[thread_key] = []
            conversations[thread_key].append(msg)
        
        return conversations
    
    def _get_thread_key(self, message: Dict[str, Any]) -> str:
        """Generate a unique key for a conversation thread."""
        if message.get('type') == 'stream':
            return f"stream_{message.get('stream_id')}_{message.get('subject', '')}"
        else:
            # For private messages, create key based on participants
            recipients = message.get('display_recipient', [])
            if isinstance(recipients, list):
                recipient_ids = sorted([r.get('id') for r in recipients if r.get('id') != self.user_id])
                return f"private_{'_'.join(map(str, recipient_ids))}"
            else:
                return f"private_{message.get('sender_id', 'unknown')}"
    
    def _get_conversation_context(self, sample_message: Dict[str, Any], 
                                 context_limit: int = 20) -> List[Dict[str, Any]]:
        """Get full conversation context for a message."""
        if sample_message.get('type') == 'stream':
            return self.zulip.get_thread_messages(
                sample_message['stream_id'], 
                sample_message['subject'],
                num_before=context_limit
            )
        else:
            # For private messages, we'd need to implement a method to get the conversation
            # For now, return the sample message
            return [sample_message]
    
    def _create_draft(self, message: Dict[str, Any], content: str) -> Optional[int]:
        """Create a draft message."""
        # Always create a new draft (no checking for existing ones)
        if message.get('type') == 'stream' and 'stream_id' in message and 'subject' in message:
            return self.zulip.create_draft(
                'stream',
                [],
                message['subject'],
                content,
                message['stream_id']
            )
        else:
            # For private messages or messages missing required stream fields
            self.logger.debug(f"Treating as private message. Type: {message.get('type')}, has stream_id: {'stream_id' in message}, has subject: {'subject' in message}")
            recipients = message.get('display_recipient', [])
            if isinstance(recipients, list):
                recipient_ids = [r.get('id') for r in recipients if r.get('id') != self.user_id]
                if recipient_ids:
                    return self.zulip.create_draft('private', recipient_ids, '', content)
            else:
                # Single recipient private message
                sender_id = message.get('sender_id')
                if sender_id and sender_id != self.user_id:
                    return self.zulip.create_draft('private', [sender_id], '', content)
            
            self.logger.warning(f"Could not create draft for message: type={message.get('type')}, stream_id={'stream_id' in message}, subject={'subject' in message}, recipients={recipients}")
            return None
    
    def _get_thread_key_from_draft(self, draft: Dict[str, Any]) -> str:
        """Extract thread key from a draft."""
        if draft.get('type') == 'stream':
            # For stream drafts, 'to' contains the stream ID
            stream_id = draft.get('to')
            topic = draft.get('topic', '')
            return f"stream_{stream_id}_{topic}"
        else:
            # For private message drafts
            recipients = draft.get('to', [])
            if isinstance(recipients, list):
                # This is simplified - you might need to get user IDs from emails
                return f"private_{'_'.join(sorted(recipients))}"
            else:
                return f"private_{recipients}"