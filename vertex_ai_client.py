import vertexai
from vertexai.generative_models import GenerativeModel, Part
import logging
from typing import List, Dict, Any, Optional

class VertexAIClient:
    def __init__(self, project_id: str, location: str, model_name: str = "gemini-1.5-pro", 
                 style_instructions: Optional[str] = None):
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.style_instructions = style_instructions or "Write in a professional and helpful tone."
        self.logger = logging.getLogger(__name__)
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        self.model = GenerativeModel(model_name)
    
    def generate_reply(self, conversation_context: str, user_name: str, 
                      conversation_type: str = "stream") -> Optional[str]:
        """Generate a reply based on conversation context."""
        try:
            prompt = self._build_reply_prompt(conversation_context, user_name, conversation_type)
            
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return response.text.strip()
            else:
                self.logger.error("No response generated from Vertex AI")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating reply: {e}")
            return None
    
    def generate_summary(self, messages: List[Dict[str, Any]], 
                        user_name: str) -> Optional[str]:
        """Generate a summary of unread messages."""
        try:
            prompt = self._build_summary_prompt(messages, user_name)
            
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return response.text.strip()
            else:
                self.logger.error("No summary generated from Vertex AI")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            return None
    
    def _build_reply_prompt(self, conversation_context: str, user_name: str, 
                           conversation_type: str) -> str:
        """Build a prompt for generating replies."""
        base_prompt = f"""You are an AI assistant helping {user_name} draft replies for Zulip messages. 

Context: This is a {"stream/channel" if conversation_type == "stream" else "private"} conversation.

Conversation history:
{conversation_context}

Please draft a thoughtful and appropriate reply as {user_name}. The reply should:
1. Be contextually appropriate and address the main points or questions raised
2. Match the tone of the conversation
3. Use {user_name}'s voice and perspective
4. Follow these style guidelines: {self.style_instructions}

Only provide the reply text, no additional formatting or explanations."""

        return base_prompt
    
    def _build_summary_prompt(self, messages: List[Dict[str, Any]], user_name: str) -> str:
        """Build a prompt for generating message summaries."""
        message_text = self._format_messages_for_summary(messages)
        
        prompt = f"""You are an AI assistant helping {user_name} get a summary of unread Zulip messages.

Here are the unread messages:

{message_text}

Please provide a concise summary that includes:
1. Key topics or discussions
2. Important questions or requests directed at {user_name}
3. Any urgent or time-sensitive items
4. A brief overview of what's happening in different conversations

Format the summary in a clear, organized way that helps {user_name} quickly understand what needs attention."""

        return prompt
    
    def _format_messages_for_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages for summary generation."""
        formatted_messages = []
        
        for msg in messages:
            timestamp = msg.get('timestamp', 'Unknown time')
            sender = msg.get('sender_full_name', 'Unknown sender')
            content = msg.get('content', '')
            
            # Include stream/topic info if available
            location = ""
            if 'stream_id' in msg and 'subject' in msg:
                location = f" in #{msg.get('display_recipient', 'unknown')} > {msg.get('subject', 'unknown topic')}"
            elif msg.get('type') == 'private':
                recipients = msg.get('display_recipient', [])
                if isinstance(recipients, list):
                    recipient_names = [r.get('full_name', 'Unknown') for r in recipients]
                    location = f" (private message with {', '.join(recipient_names)})"
            
            formatted_messages.append(f"[{timestamp}] {sender}{location}: {content}")
        
        return "\n\n".join(formatted_messages)
    
    def _format_conversation_context(self, messages: List[Dict[str, Any]]) -> str:
        """Format conversation messages for context."""
        formatted_messages = []
        
        # Sort messages by timestamp
        sorted_messages = sorted(messages, key=lambda x: x.get('timestamp', 0))
        
        for msg in sorted_messages:
            sender = msg.get('sender_full_name', 'Unknown sender')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', 'Unknown time')
            
            formatted_messages.append(f"{sender} [{timestamp}]: {content}")
        
        return "\n".join(formatted_messages)