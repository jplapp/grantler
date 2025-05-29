# Zulip AI Bot

An intelligent Zulip bot that uses Google Vertex AI to automatically draft replies to your messages and provide summaries of unread content.

## Demo

![Demo Video](output_trimmed.mp4)

*Watch the bot in action: creating AI-powered draft replies for all conversations*

## Features

1. **Automated Reply Drafting**: Fetches unread messages where you're mentioned or in private conversations, generates contextual replies using AI, and saves them as drafts in Zulip.

2. **Message Summarization**: Provides intelligent summaries of your unread messages to help you quickly understand what needs attention.

3. **Conversation Tracking**: Monitors open conversations where you still need to reply, including:
   - Private conversations with missing replies
   - Channel discussions where you were mentioned but haven't responded

## Setup

### Prerequisites

- Python 3.8+
- Zulip account with API access
- Google Cloud Project with Vertex AI enabled
- Google Cloud credentials configured

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd zulip-ai-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Google Cloud credentials:
```bash
# Set up Application Default Credentials
gcloud auth application-default login

# Or set the environment variable for service account key
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"
```

4. Configure the bot:
```bash
python main.py setup
```

This will guide you through setting up your `.env` file with:
- Zulip credentials (email, API key, site URL, user ID)
- Google Cloud settings (project ID, location, model)
- User information

### Getting Zulip Credentials

1. **API Key**: Go to Zulip Settings → Account & privacy → API key
2. **User ID**: You can find this in your Zulip profile URL or by calling the API
3. **Site URL**: Your organization's Zulip URL (e.g., `https://yourorg.zulipchat.com`)

## Usage

### Run All Features
```bash
python main.py run-all
```
This will check conversations, create drafts, and show a summary.

### Individual Commands

**Create reply drafts for unread messages:**
```bash
python main.py draft-replies
```

**Get a summary of unread messages:**
```bash
python main.py summarize
```

**Check for conversations needing replies:**
```bash
python main.py check-conversations
```

**Interactive setup:**
```bash
python main.py setup
```

### Options

Add `--verbose` or `-v` to any command for detailed logging:
```bash
python main.py -v run-all
```

## How It Works

### Database Tracking
The bot uses SQLite to track:
- Processed messages to avoid duplicates
- Conversation threads and their states
- Draft IDs for updating existing drafts

### AI Integration
- Uses Google Vertex AI (Gemini) to generate contextual replies
- Maintains conversation context for better responses
- Adapts tone and style based on the conversation type

### Draft Management
- Creates new drafts or updates existing ones for the same conversation
- Handles both stream/channel messages and private messages
- Links drafts to conversation threads in the database

## Configuration

### Environment Variables

Create a `.env` file with:

```env
# Zulip Configuration
ZULIP_EMAIL=your-email@example.com
ZULIP_API_KEY=your_api_key
ZULIP_SITE=https://your-org.zulipchat.com
BOT_USER_ID=your_user_id

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_AI_MODEL=gemini-1.5-pro

# User Configuration
USER_FULL_NAME=Your Full Name
```

## Automation

You can run this bot periodically using cron or a similar scheduler:

```bash
# Add to crontab to run every 30 minutes
*/30 * * * * cd /path/to/zulip-ai-bot && python main.py run-all
```

## Troubleshooting

### Common Issues

1. **Authentication Error**: Ensure your Zulip API key is correct and has the necessary permissions.

2. **Google Cloud Error**: Verify that:
   - Vertex AI is enabled in your project
   - You have proper authentication set up
   - The specified model is available in your region

3. **Permission Error**: Make sure your Zulip user has permission to create drafts and access the messages.

### Logs

Check `zulip_bot.log` for detailed error messages and debugging information.

## Development

The bot consists of several modular components:

- `database.py`: SQLite database management
- `zulip_client.py`: Zulip API wrapper
- `vertex_ai_client.py`: Google Vertex AI integration
- `zulip_bot.py`: Main bot logic
- `main.py`: CLI interface

## License

[Add your license information here]
