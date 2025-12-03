#!/usr/bin/env python3
"""
Test script for AIChatbot OpenAI API functionality
Tests the AI conversation features without hardware dependencies
"""

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI, APIConnectionError

# Load environment variables
load_dotenv()

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ ERROR: OPENAI_API_KEY not found in .env file")
    print("Please add your API key to the .env file:")
    print("OPENAI_API_KEY=your_api_key_here")
    sys.exit(1)

client = OpenAI(api_key=api_key)

# Configuration (matching AIChatbot.py)
TTS_MODEL = "tts-1"  # Using standard TTS model
VOICE_NAME = "echo"
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

if not ASSISTANT_ID:
    print("⚠️  WARNING: ASSISTANT_ID not found in .env file")
    print("Please add your Assistant ID to the .env file:")
    print("ASSISTANT_ID=asst_xxxxxxxxxxxxx")
    print("\n💡 You can create an assistant at: https://platform.openai.com/assistants")
    print("   Or use the OpenAI API to create one programmatically.")
    print()

print("=" * 60)
print("🤖 AI Chatbot Assistant API Test Mode")
print("=" * 60)
print(f"✅ OpenAI API Key loaded")
if ASSISTANT_ID:
    print(f"🤖 Assistant ID: {ASSISTANT_ID}")
else:
    print(f"❌ Assistant ID: Not configured")
print(f"🔊 TTS Model: {TTS_MODEL}")
print(f"🎤 Voice: {VOICE_NAME}")
print("=" * 60)
print()


def test_api_connection():
    """Test if we can connect to OpenAI API"""
    print("🔌 Testing API connection...")
    try:
        # Simple test - list models
        models = client.models.list()
        print("✅ API connection successful!")
        return True
    except APIConnectionError as e:
        print(f"❌ API connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def create_assistant(name="Chatbot Assistant", instructions=None):
    """Helper function to create an assistant"""
    if instructions is None:
        instructions = (
            "You are a calm, expressive AI. "
            "Respond concisely in 1 sentence unless necessary. "
            "Do NOT start with greetings like 'Hello', 'Hi', or 'How can I help you today?'. "
            "Just answer the user's request directly. "
            "Also output emotion as one of: happy, sad, neutral, angry, surprised. "
            "Format: <text> [emotion: <label>]"
        )
    
    print(f"\n🔧 Creating assistant: {name}...")
    try:
        assistant = client.beta.assistants.create(
            name=name,
            instructions=instructions,
            model="gpt-4o-mini",
        )
        print(f"✅ Assistant created!")
        print(f"📋 Assistant ID: {assistant.id}")
        print(f"\n💡 Add this to your .env file:")
        print(f"ASSISTANT_ID={assistant.id}")
        return assistant.id
    except Exception as e:
        print(f"❌ Error creating assistant: {e}")
        return None


def test_assistant_api(user_message, verbose=True, thread=None):
    """Test Assistant API (matching AIChatbot.py implementation)"""
    if verbose:
        print(f"\n💬 Testing Assistant API...")
        print(f"📤 User: {user_message}")
    
    if not ASSISTANT_ID:
        print("❌ ASSISTANT_ID not configured. Cannot test Assistant API.")
        return None, None, None
    
    try:
        import time
        import re
        
        # 1) Create a thread only if it doesn't exist yet
        if thread is None:
            thread = client.beta.threads.create()
            if verbose:
                print(f"📝 Thread created: {thread.id}")
        elif verbose:
            print(f"📝 Using existing thread: {thread.id}")
        
        # 2) Add user message to thread
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )
        if verbose:
            print("✅ Message added to thread")
        
        # 3) Create a run
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
        )
        if verbose:
            print(f"🚀 Run created: {run.id} (status: {run.status})")
        
        # 4) Poll for completion
        while run.status in ("queued", "in_progress"):
            time.sleep(0.8)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if verbose:
                print(f"   Status: {run.status}")
        
        if run.status != "completed":
            print(f"❌ Run failed with status: {run.status}")
            if hasattr(run, 'last_error'):
                print(f"   Error: {run.last_error}")
            return None, None, thread
        
        # 5) Read the latest assistant message
        messages = client.beta.threads.messages.list(thread_id=thread.id, order="desc", limit=1)
        latest = messages.data[0]
        response_text = latest.content[0].text.value
        
        # Extract emotion (if present)
        match = re.search(r"\[emotion:\s*(\w+)\]", response_text, re.IGNORECASE)
        emotion = match.group(1).lower() if match else "neutral"
        
        # Strip label before displaying
        reply_text = re.sub(r"\[emotion:.*\]", "", response_text).strip()
        
        if verbose:
            print(f"📥 Bot: {reply_text}")
            print(f"😊 Emotion: {emotion}")
            print("✅ Assistant API call successful!")
        else:
            # Simple output for interactive mode
            print(f"Bot: {reply_text}")
        
        return reply_text, emotion, thread
        
    except APIConnectionError as e:
        print(f"❌ API connection error: {e}")
        return None, None, thread
    except Exception as e:
        print(f"❌ Error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return None, None, thread


def test_tts(text, output_file="test_speech.mp3"):
    """Test text-to-speech generation"""
    print(f"\n🔊 Testing TTS...")
    print(f"📝 Text: {text}")
    
    try:
        response = client.audio.speech.create(
            model=TTS_MODEL,
            voice=VOICE_NAME,
            input=text
        )
        
        # Save to file
        response.stream_to_file(output_file)
        print(f"✅ TTS successful! Audio saved to: {output_file}")
        print(f"💡 You can play it with: afplay {output_file} (macOS)")
        return True
        
    except APIConnectionError as e:
        print(f"❌ API connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_transcription(audio_file):
    """Test audio transcription (if audio file provided)"""
    if not os.path.exists(audio_file):
        print(f"\n⚠️  Audio file not found: {audio_file}")
        print("💡 Skipping transcription test")
        return None
    
    print(f"\n🎤 Testing transcription...")
    print(f"📁 File: {audio_file}")
    
    try:
        with open(audio_file, "rb") as audio_file_obj:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file_obj
            )
        
        transcribed_text = result.text.strip()
        print(f"📝 Transcribed: {transcribed_text}")
        print("✅ Transcription successful!")
        return transcribed_text
        
    except APIConnectionError as e:
        print(f"❌ API connection error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def interactive_mode():
    """Interactive chat mode"""
    # Initialize thread variable - will be created on first use
    thread = None
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            reply, emotion, thread = test_assistant_api(user_input, verbose=False, thread=thread)
            
            if reply:
                print()  # Add spacing between messages
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print()


def main():
    """Main test function"""
    print("\n🧪 Running API tests...\n")
    
    # Test 1: API Connection
    if not test_api_connection():
        print("\n❌ API connection failed. Please check your API key and internet connection.")
        return
    
    # Check if assistant ID is configured
    if not ASSISTANT_ID:
        print("\n" + "=" * 60)
        print("⚠️  ASSISTANT_ID not configured")
        print("=" * 60)
        choice = input("\nWould you like to create a new assistant? (y/n): ").strip().lower()
        if choice == 'y':
            assistant_id = create_assistant()
            if assistant_id:
                print("\n✅ Please add ASSISTANT_ID to your .env file and run the test again.")
            return
        else:
            print("\n💡 You can:")
            print("   1. Create an assistant at: https://platform.openai.com/assistants")
            print("   2. Or run this script again and choose 'y' to create one programmatically")
            print("   3. Then add ASSISTANT_ID=asst_xxxxx to your .env file")
            return
    
    # Test 2: Assistant API - Initial test with "Hi"
    if not ASSISTANT_ID:
        print("\n⚠️  Skipping Assistant API tests (ASSISTANT_ID not configured)")
        print("💡 Add ASSISTANT_ID to .env file to test Assistant API")
    else:
        print("\n" + "=" * 60)
        print("📋 Initial Assistant API Test")
        print("=" * 60)
        
        # Test with "Hi" message (creates a new thread for this initial test)
        test_assistant_api("Hi")
        print()
    
    # Interactive mode
    if ASSISTANT_ID:
        print("=" * 60)
        print("💬 Starting Interactive Chat Mode")
        print("=" * 60)
        print("Type your messages (or 'quit' to exit)")
        print()
        interactive_mode()
    else:
        print("\n💡 Add ASSISTANT_ID to .env file to use interactive mode")


if __name__ == "__main__":
    main()

