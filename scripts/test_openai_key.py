#!/usr/bin/env python3
"""
OpenAI API Key Validation Script
Tests that the OpenAI API key is valid and working.
"""

import os
import sys
from dotenv import load_dotenv

def test_openai_key():
    """Test OpenAI API key with a simple completion call."""
    
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        print("   Make sure you have a .env file with OPENAI_API_KEY set")
        return False
    
    if 'your_openai_api_key_here' in api_key or len(api_key) < 20:
        print("❌ OPENAI_API_KEY appears to be a placeholder")
        print("   Update .env with your actual OpenAI API key")
        return False
    
    print(f"🔑 API Key found: {api_key[:8]}...{api_key[-4:]}")
    
    try:
        from openai import OpenAI
        
        print("📡 Testing OpenAI API connection...")
        client = OpenAI(api_key=api_key)
        
        # Make a minimal test call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Say 'test successful' if you receive this."}
            ],
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip()
        
        print(f"✅ API Response: {result}")
        print(f"✅ OpenAI API key is valid and working!")
        print(f"   Model: {response.model}")
        print(f"   Usage: {response.usage.total_tokens} tokens")
        
        return True
        
    except ImportError:
        print("⚠️  OpenAI package not installed")
        print("   Install it with: pip install openai")
        return False
    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        print("   Check that your API key is correct and has sufficient quota")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  OpenAI API Key Validation")
    print("="*60 + "\n")
    
    success = test_openai_key()
    
    print("\n" + "="*60 + "\n")
    
    sys.exit(0 if success else 1)
