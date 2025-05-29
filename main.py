#!/usr/bin/env python3

import os
import sys
import logging
import click
from typing import Optional
from dotenv import load_dotenv

from zulip_bot import ZulipBot

# Load environment variables
load_dotenv()

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('zulip_bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_bot_instance(channel_filter: Optional[str] = None) -> ZulipBot:
    """Create and return a ZulipBot instance with environment configuration."""
    required_env_vars = [
        'ZULIP_EMAIL', 'ZULIP_API_KEY', 'ZULIP_SITE',
        'GOOGLE_CLOUD_PROJECT', 'GOOGLE_CLOUD_LOCATION'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        click.echo(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        click.echo("Please check your .env file or set these variables.")
        sys.exit(1)
    
    return ZulipBot(
        zulip_email=os.getenv('ZULIP_EMAIL'),
        zulip_api_key=os.getenv('ZULIP_API_KEY'),
        zulip_site=os.getenv('ZULIP_SITE'),
        gcp_project=os.getenv('GOOGLE_CLOUD_PROJECT'),
        gcp_location=os.getenv('GOOGLE_CLOUD_LOCATION'),
        vertex_model=os.getenv('VERTEX_AI_MODEL', 'gemini-1.5-pro'),
        style_instructions=os.getenv('BOT_STYLE_INSTRUCTIONS'),
        channel_filter=channel_filter
    )

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(verbose):
    """Zulip AI Bot - Automated reply drafting using Google Vertex AI."""
    setup_logging(verbose)

@cli.command()
def draft_replies():
    """Process unread messages and create reply drafts."""
    click.echo("🤖 Processing unread messages and creating drafts...")
    
    try:
        bot = get_bot_instance()  # No channel filter for drafts
        bot.process_unread_messages_and_create_drafts()
        click.echo("✅ Finished processing unread messages.")
    except Exception as e:
        click.echo(f"❌ Error processing messages: {e}")
        sys.exit(1)

@cli.command()
def summarize():
    """Generate a summary of unread messages and post to johannes_bot channel."""
    click.echo("📝 Generating summary of unread messages...")
    
    try:
        bot = get_bot_instance()
        result = bot.generate_unread_summary()
        click.echo(f"✅ {result}")
        
    except Exception as e:
        click.echo(f"❌ Error generating summary: {e}")
        sys.exit(1)

@cli.command()
def check_conversations():
    """Check for open conversations that need replies."""
    click.echo("🔍 Checking for open conversations requiring replies...")
    
    try:
        bot = get_bot_instance()  # No channel filter for checking conversations
        bot.check_open_conversations()
        click.echo("✅ Finished checking conversations.")
    except Exception as e:
        click.echo(f"❌ Error checking conversations: {e}")
        raise
        sys.exit(1)

@cli.command()
def run_all():
    """Run all bot functions: check conversations, create drafts, and show summary."""
    click.echo("🚀 Running complete bot workflow...")
    
    try:
        bot = get_bot_instance()  # No channel filter for complete workflow
        
        # Step 1: Check for conversations needing replies
        click.echo("1️⃣ Checking conversations...")
        bot.check_open_conversations()
        
        # Step 2: Process unread messages and create drafts
        click.echo("2️⃣ Creating reply drafts...")
        bot.process_unread_messages_and_create_drafts()
        
        # Step 3: Generate summary
        click.echo("3️⃣ Generating summary...")
        summary = bot.generate_unread_summary()
        
        click.echo("\n" + "="*60)
        click.echo("📋 SUMMARY OF UNREAD MESSAGES")
        click.echo("="*60)
        click.echo(summary)
        click.echo("="*60)
        
        click.echo("\n✅ Bot workflow completed successfully!")
        
    except Exception as e:
        click.echo(f"❌ Error running bot workflow: {e}")
        sys.exit(1)

@cli.command()
def setup():
    """Interactive setup to create .env file."""
    click.echo("🛠️  Zulip AI Bot Setup")
    click.echo("="*40)
    
    if os.path.exists('.env'):
        if not click.confirm('.env file already exists. Overwrite?'):
            return
    
    # Collect configuration
    config = {}
    
    click.echo("\n📧 Zulip Configuration:")
    config['ZULIP_EMAIL'] = click.prompt('Your Zulip email')
    config['ZULIP_API_KEY'] = click.prompt('Your Zulip API key', hide_input=True)
    config['ZULIP_SITE'] = click.prompt('Your Zulip site URL (e.g., https://your-org.zulipchat.com)')
    click.echo('✨ User ID and name will be automatically fetched from the Zulip API')
    
    click.echo("\n☁️  Google Cloud Configuration:")
    config['GOOGLE_CLOUD_PROJECT'] = click.prompt('Google Cloud project ID')
    config['GOOGLE_CLOUD_LOCATION'] = click.prompt('Google Cloud location', default='us-central1')
    config['VERTEX_AI_MODEL'] = click.prompt('Vertex AI model', default='gemini-1.5-pro')
    
    click.echo("\n🤖 Bot Style Configuration:")
    default_style = "Write in a professional but friendly tone. Keep responses concise and helpful."
    config['BOT_STYLE_INSTRUCTIONS'] = click.prompt(
        'How should the bot write replies? (style instructions)', 
        default=default_style
    )
    
    
    # Write .env file
    with open('.env', 'w') as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")
    
    click.echo("\n✅ Configuration saved to .env file!")
    click.echo("💡 You can now run the bot with: python main.py run-all")

if __name__ == '__main__':
    cli()