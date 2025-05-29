import zulip
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

class ZulipClient:
    def __init__(self, email: str, api_key: str, site: str):
        self.logger = logging.getLogger(__name__)
        print(email, api_key, site)
        self.client = zulip.Client(email=email, api_key=api_key, site=site)
        self.user_id = self._get_current_user_id()
    
    def _get_current_user_id(self) -> int:
        """Fetch the current user's ID from Zulip API."""
        try:
            result = self.client.get_profile()
            if result['result'] == 'success':
                return result['user_id']
            else:
                self.logger.error(f"Failed to get user profile: {result.get('msg', 'Unknown error')}")
                raise Exception(f"Failed to get user ID: {result.get('msg', 'Unknown error')}")
        except Exception as e:
            self.logger.error(f"Error fetching user ID: {e}")
            raise
    
    def get_unread_messages(self, anchor: str = "newest", num_before: int = 100, 
                           channel_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch unread messages for the user."""
        try:
            # Build narrow conditions
            narrow = [
                {'operator': 'is', 'operand': 'unread'}
            ]
            
            # Add channel filter if specified
            if channel_filter:
                narrow.append({'operator': 'stream', 'operand': channel_filter})
            
            request = {
                'anchor': anchor,
                'num_before': num_before,
                'num_after': 0,
                'narrow': narrow
            }
            
            result = self.client.get_messages(request)
            if result['result'] == 'success':
                return result['messages']
            else:
                self.logger.error(f"Failed to fetch messages: {result.get('msg', 'Unknown error')}")
                return []
        except Exception as e:
            self.logger.error(f"Error fetching unread messages: {e}")
            return []
    
    def get_private_messages(self, anchor: str = "newest", num_before: int = 100) -> List[Dict[str, Any]]:
        """Fetch private messages."""
        try:
            request = {
                'anchor': anchor,
                'num_before': num_before,
                'num_after': 0,
                'narrow': [
                    {'operator': 'is', 'operand': 'private'},
                    {'operator': 'is', 'operand': 'unread'}
                ]
            }
            
            result = self.client.get_messages(request)
            if result['result'] == 'success':
                return result['messages']
            else:
                self.logger.error(f"Failed to fetch private messages: {result.get('msg', 'Unknown error')}")
                return []
        except Exception as e:
            self.logger.error(f"Error fetching private messages: {e}")
            return []

    def get_all_recent_messages(self, anchor: str = "newest", num_before: int = 500, 
                               channel_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch all recent messages (not just unread)."""
        try:
            # Build narrow conditions - no unread filter
            narrow = []
            
            # Add channel filter if specified
            if channel_filter:
                narrow.append({'operator': 'stream', 'operand': channel_filter})
            
            request = {
                'anchor': anchor,
                'num_before': num_before,
                'num_after': 0,
                'narrow': narrow
            }
            
            result = self.client.get_messages(request)
            if result['result'] == 'success':
                return result['messages']
            else:
                self.logger.error(f"Failed to fetch recent messages: {result.get('msg', 'Unknown error')}")
                return []
        except Exception as e:
            self.logger.error(f"Error fetching recent messages: {e}")
            return []

    def get_all_private_messages(self, anchor: str = "newest", num_before: int = 500) -> List[Dict[str, Any]]:
        """Fetch all recent private messages (not just unread)."""
        try:
            request = {
                'anchor': anchor,
                'num_before': num_before,
                'num_after': 0,
                'narrow': [
                    {'operator': 'is', 'operand': 'private'}
                ]
            }
            
            result = self.client.get_messages(request)
            if result['result'] == 'success':
                return result['messages']
            else:
                self.logger.error(f"Failed to fetch all private messages: {result.get('msg', 'Unknown error')}")
                return []
        except Exception as e:
            self.logger.error(f"Error fetching all private messages: {e}")
            return []
    
    def get_thread_messages(self, stream_id: int, topic: str, 
                           anchor: str = "newest", num_before: int = 50) -> List[Dict[str, Any]]:
        """Get all messages in a specific thread."""
        try:
            # Get stream name from stream ID
            stream_info = self.get_stream_info(stream_id)
            if not stream_info:
                self.logger.error(f"Could not get stream info for stream_id: {stream_id}")
                return []
            
            stream_name = stream_info['name']
            
            request = {
                'anchor': anchor,
                'num_before': num_before,
                'num_after': 0,
                'narrow': [
                    {'operator': 'stream', 'operand': stream_name},
                    {'operator': 'topic', 'operand': topic}
                ]
            }
            
            result = self.client.get_messages(request)
            if result['result'] == 'success':
                return result['messages']
            else:
                self.logger.error(f"Failed to fetch thread messages: {result.get('msg', 'Unknown error')}")
                return []
        except Exception as e:
            self.logger.error(f"Error fetching thread messages: {e}")
            return []
    
    def create_scheduled_message(self, message_type: str, to: List[str], topic: str, 
                                content: str, stream_id: Optional[int] = None) -> Optional[int]:
        """Create a scheduled message for 10 years in the future."""
        try:
            import time
            # Schedule for 10 years in the future
            ten_years_from_now = int(time.time()) + (10 * 365 * 24 * 60 * 60)
            
            message_data = {
                'type': 'stream' if message_type == 'stream' else 'direct',
                'content': content,
                'scheduled_delivery_timestamp': ten_years_from_now
            }
            
            if message_type == 'stream':
                message_data['to'] = stream_id
                message_data['topic'] = topic
            else:  # private message
                message_data['to'] = to
            
            # Use the direct API call to create scheduled message
            result = self.client.call_endpoint(
                url='scheduled_messages',
                method='POST',
                request=message_data
            )
            
            if result['result'] == 'success':
                message_id = result.get('scheduled_message_id')
                self.logger.info(f"Created scheduled message for 10 years from now with ID: {message_id}")
                return message_id
            else:
                self.logger.error(f"Failed to create scheduled message: {result.get('msg', 'Unknown error')} - Full response: {result}")
                return None
        except Exception as e:
            self.logger.error(f"Error creating scheduled message: {e}")
            return None
    
    def update_draft(self, draft_id: int, content: str) -> bool:
        """Update an existing draft."""
        try:
            # Use the direct API call since zulip-python doesn't have edit_draft
            result = self.client.call_endpoint(
                url=f'drafts/{draft_id}',
                method='PATCH',
                request={'content': content}
            )
            
            if result['result'] == 'success':
                return True
            else:
                self.logger.error(f"Failed to update draft: {result.get('msg', 'Unknown error')}")
                return False
        except Exception as e:
            self.logger.error(f"Error updating draft: {e}")
            return False
    
    def get_drafts(self) -> List[Dict[str, Any]]:
        """Get all drafts."""
        try:
            # Use the direct API call since zulip-python doesn't have get_drafts
            result = self.client.call_endpoint(
                url='drafts',
                method='GET'
            )
            
            if result['result'] == 'success':
                return result.get('drafts', [])
            else:
                self.logger.error(f"Failed to fetch drafts: {result.get('msg', 'Unknown error')}")
                return []
        except Exception as e:
            self.logger.error(f"Error fetching drafts: {e}")
            return []
    
    def create_draft(self, message_type: str, to: List[str], topic: str, 
                    content: str, stream_id: Optional[int] = None) -> Optional[int]:
        """Create a draft message."""
        try:
            if message_type == 'stream':
                # Validate required fields for stream drafts
                if not stream_id or not topic or topic.strip() == '':
                    self.logger.error(f"Missing required fields for stream draft: stream_id={stream_id}, topic='{topic}'")
                    return None
                    
                draft_data = {
                    'type': 'stream',
                    'content': content,
                    'to': [stream_id],
                    'topic': topic.strip()
                }
            else:  # private message
                # Validate required fields for private drafts
                if not to or len(to) == 0:
                    self.logger.error(f"Missing recipients for private draft: to={to}")
                    return None
                    
                draft_data = {
                    'type': 'private',
                    'content': content,
                    'to': to,
                    'topic': ''  # Private messages don't have a topic
                }
            
            # Wrap in 'drafts' array as required by the API
            request_data = {
                'drafts': [draft_data]
            }
            
            # Use the direct API call to create draft
            result = self.client.call_endpoint(
                url='drafts',
                method='POST',
                request=request_data
            )
            
            if result['result'] == 'success':
                # The response contains an array of created drafts
                draft_ids = result.get('ids', [])
                if draft_ids:
                    draft_id = draft_ids[0]
                    self.logger.info(f"Created draft with ID: {draft_id}")
                    return draft_id
                else:
                    self.logger.error("No draft ID returned in response")
                    return None
            else:
                self.logger.error(f"Failed to create draft {request_data}: {result.get('msg', 'Unknown error')} - Full response: {result}")
                return None
        except Exception as e:
            self.logger.error(f"Error creating draft: {e}")
            return None

    def delete_draft(self, draft_id: int) -> bool:
        """Delete a draft."""
        try:
            # Use the direct API call since zulip-python doesn't have delete_draft
            result = self.client.call_endpoint(
                url=f'drafts/{draft_id}',
                method='DELETE'
            )
            
            if result['result'] == 'success':
                return True
            else:
                self.logger.error(f"Failed to delete draft: {result.get('msg', 'Unknown error')}")
                return False
        except Exception as e:
            self.logger.error(f"Error deleting draft: {e}")
            return False
    
    def send_message(self, stream_name: str, topic: str, content: str) -> bool:
        """Send a message to a stream."""
        try:
            message = {
                'type': 'stream',
                'to': stream_name,
                'topic': topic,
                'content': content
            }
            result = self.client.send_message(message)
            if result['result'] == 'success':
                return True
            else:
                self.logger.error(f"Failed to send message: {result.get('msg', 'Unknown error')}")
                return False
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            return False
    
    def mark_as_read(self, message_ids: List[int]) -> bool:
        """Mark messages as read."""
        try:
            result = self.client.mark_all_as_read()
            return result['result'] == 'success'
        except Exception as e:
            self.logger.error(f"Error marking messages as read: {e}")
            return False
    
    def get_stream_info(self, stream_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a stream."""
        try:
            result = self.client.get_streams()
            if result['result'] == 'success':
                for stream in result['streams']:
                    if stream['stream_id'] == stream_id:
                        return stream
                return None
            else:
                return None
        except Exception as e:
            self.logger.error(f"Error getting stream info: {e}")
            return None
    
    def needs_reply_in_thread(self, messages: List[Dict[str, Any]]) -> bool:
        """Check if the user needs to reply in a thread."""
        if not messages:
            return False
        
        # Sort messages by timestamp
        sorted_messages = sorted(messages, key=lambda x: x['timestamp'])
        
        # Check if the user was mentioned and hasn't replied since
        user_mentioned = False
        user_last_reply = None
        last_mention = None
        
        for msg in sorted_messages:
            if msg['sender_id'] == self.user_id:
                user_last_reply = msg['timestamp']
            
            # Check if user was mentioned in this message
            if 'mentions' in msg and any(mention['id'] == self.user_id for mention in msg['mentions']):
                user_mentioned = True
                last_mention = msg['timestamp']
        
        # User needs to reply if they were mentioned and haven't replied since the mention
        if user_mentioned and last_mention:
            if user_last_reply is None or user_last_reply < last_mention:
                return True
        
        return False