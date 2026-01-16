"""
Test OpenAI API Key

Verifies that your OpenAI API key is valid and checks token availability.
"""

import os
import sys

def test_openai_key():
    """Test OpenAI API key validity and token availability."""
    
    # Check if key is set
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        print("\nSet it with:")
        print("  export OPENAI_API_KEY='sk-...'")
        return False
    
    print(f"✓ API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    # Try to import OpenAI
    try:
        from openai import OpenAI
        print("✓ OpenAI library installed")
    except ImportError:
        print("❌ OpenAI library not installed")
        print("\nInstall with:")
        print("  pip install openai")
        return False
    
    # Initialize client
    try:
        client = OpenAI(api_key=api_key)
        print("✓ OpenAI client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return False
    
    # Test with minimal API call
    print("\nTesting API call (minimal tokens)...")
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Cheaper model for testing
            messages=[
                {"role": "user", "content": "Say 'OK' if you can read this."}
            ],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        print(f"✅ API KEY IS VALID!")
        print(f"\n📊 Test Results:")
        print(f"   Model: {response.model}")
        print(f"   Response: {result}")
        print(f"   Tokens used: {tokens_used}")
        print(f"   Prompt tokens: {response.usage.prompt_tokens}")
        print(f"   Completion tokens: {response.usage.completion_tokens}")
        
        # Check account info (if available)
        print(f"\n💡 API Key Status:")
        print(f"   ✓ Key is active and working")
        print(f"   ✓ Can access GPT-3.5-Turbo")
        
        # Test GPT-4 access (optional)
        print(f"\nTesting GPT-4 access...")
        try:
            response_gpt4 = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": "Say 'OK'"}
                ],
                max_tokens=5
            )
            print(f"   ✅ GPT-4 access: YES")
            print(f"   Model: {response_gpt4.model}")
        except Exception as e:
            if "model_not_found" in str(e) or "does not exist" in str(e):
                print(f"   ⚠️  GPT-4 access: NO (not enabled for this key)")
            else:
                print(f"   ⚠️  GPT-4 test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ API call failed: {e}")
        
        # Parse common errors
        error_str = str(e).lower()
        
        if "invalid" in error_str or "incorrect" in error_str:
            print("\n💡 This API key appears to be INVALID")
            print("   Check that you copied it correctly")
        
        elif "quota" in error_str or "exceeded" in error_str:
            print("\n💡 This API key has EXCEEDED its quota")
            print("   You may need to add credits or wait for reset")
        
        elif "rate" in error_str:
            print("\n💡 Rate limit hit (too many requests)")
            print("   Wait a moment and try again")
        
        else:
            print(f"\n💡 Unknown error - check OpenAI status page")
        
        return False


def check_pricing_tier():
    """Display current pricing for reference."""
    print("\n" + "="*60)
    print("💰 OpenAI Pricing Reference (as of Jan 2026)")
    print("="*60)
    print("\nGPT-4 Turbo:")
    print("  • Input:  $10.00 per 1M tokens")
    print("  • Output: $30.00 per 1M tokens")
    print("\nGPT-3.5 Turbo:")
    print("  • Input:  $0.50 per 1M tokens")
    print("  • Output: $1.50 per 1M tokens")
    print("\nBeer Game estimate (per week, per AI player):")
    print("  • Prompt: ~500 tokens")
    print("  • Response: ~100 tokens")
    print("  • Cost per decision (GPT-4): ~$0.008")
    print("  • Cost per 10-week game: ~$0.08 per AI player")
    print("="*60)


if __name__ == "__main__":
    print("="*60)
    print("🔑 OpenAI API Key Validator")
    print("="*60)
    print()
    
    # Test key
    success = test_openai_key()
    
    # Show pricing
    check_pricing_tier()
    
    # Exit code
    if success:
        print("\n✅ All checks passed! Your API key is ready to use.")
        sys.exit(0)
    else:
        print("\n❌ API key validation failed. Fix the issues above.")
        sys.exit(1)
