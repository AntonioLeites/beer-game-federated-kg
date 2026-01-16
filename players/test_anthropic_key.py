"""
Test Anthropic API Key

Verifies that your Anthropic API key is valid and checks token availability.
"""

import os
import sys

def test_anthropic_key():
    """Test Anthropic API key validity and token availability."""
    
    # Check if key is set
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("❌ ANTHROPIC_API_KEY environment variable not set")
        print("\nSet it with:")
        print("  export ANTHROPIC_API_KEY='sk-ant-...'")
        return False
    
    print(f"✓ API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    # Try to import Anthropic
    try:
        from anthropic import Anthropic
        print("✓ Anthropic library installed")
    except ImportError:
        print("❌ Anthropic library not installed")
        print("\nInstall with:")
        print("  pip install anthropic")
        return False
    
    # Initialize client
    try:
        client = Anthropic(api_key=api_key)
        print("✓ Anthropic client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return False
    
    # Test with minimal API call
    print("\nTesting API call (minimal tokens)...")
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",  # Latest Sonnet
            max_tokens=10,
            messages=[
                {"role": "user", "content": "Say 'OK' if you can read this."}
            ]
        )
        
        result = response.content[0].text
        tokens_input = response.usage.input_tokens
        tokens_output = response.usage.output_tokens
        tokens_total = tokens_input + tokens_output
        
        print(f"✅ API KEY IS VALID!")
        print(f"\n📊 Test Results:")
        print(f"   Model: {response.model}")
        print(f"   Response: {result}")
        print(f"   Input tokens: {tokens_input}")
        print(f"   Output tokens: {tokens_output}")
        print(f"   Total tokens: {tokens_total}")
        
        print(f"\n💡 API Key Status:")
        print(f"   ✓ Key is active and working")
        print(f"   ✓ Can access Claude Sonnet 4")
        
        # Test Claude Opus (if available)
        print(f"\nTesting Claude Opus access...")
        try:
            response_opus = client.messages.create(
                model="claude-opus-4-20250514",
                max_tokens=5,
                messages=[
                    {"role": "user", "content": "Say 'OK'"}
                ]
            )
            print(f"   ✅ Claude Opus access: YES")
            print(f"   Model: {response_opus.model}")
        except Exception as e:
            error_str = str(e).lower()
            if "model_not_found" in error_str or "does not exist" in error_str:
                print(f"   ℹ️  Claude Opus: Not available (Sonnet is sufficient)")
            else:
                print(f"   ⚠️  Opus test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ API call failed: {e}")
        
        # Parse common errors
        error_str = str(e).lower()
        
        if "invalid" in error_str or "authentication" in error_str:
            print("\n💡 This API key appears to be INVALID")
            print("   Check that you copied it correctly")
        
        elif "credit" in error_str or "balance" in error_str:
            print("\n💡 This API key has NO CREDITS remaining")
            print("   Add credits at: https://console.anthropic.com/settings/billing")
        
        elif "rate" in error_str:
            print("\n💡 Rate limit hit (too many requests)")
            print("   Wait a moment and try again")
        
        else:
            print(f"\n💡 Unknown error - check Anthropic status page")
        
        return False


def check_pricing_tier():
    """Display current pricing for reference."""
    print("\n" + "="*60)
    print("💰 Anthropic Pricing Reference (as of Jan 2026)")
    print("="*60)
    print("\nClaude Sonnet 4:")
    print("  • Input:  $3.00 per 1M tokens")
    print("  • Output: $15.00 per 1M tokens")
    print("\nClaude Opus 4:")
    print("  • Input:  $15.00 per 1M tokens")
    print("  • Output: $75.00 per 1M tokens")
    print("\nClaude Haiku 4:")
    print("  • Input:  $0.25 per 1M tokens")
    print("  • Output: $1.25 per 1M tokens")
    print("\n🆓 FREE TIER:")
    print("  • New accounts: $5 credit (500k Sonnet tokens)")
    print("  • ~600 Beer Game decisions with Sonnet")
    print("\nBeer Game estimate (per week, per AI player):")
    print("  • Prompt: ~500 tokens")
    print("  • Response: ~100 tokens")
    print("  • Cost per decision (Sonnet): ~$0.003")
    print("  • Cost per 10-week game: ~$0.03 per AI player")
    print("  • 3× CHEAPER than GPT-4! 💰")
    print("="*60)


def show_setup_instructions():
    """Show instructions for getting API key."""
    print("\n" + "="*60)
    print("🔑 How to Get Anthropic API Key")
    print("="*60)
    print("\n1. Go to: https://console.anthropic.com/")
    print("2. Sign up or login")
    print("3. Go to 'API Keys' section")
    print("4. Click 'Create Key'")
    print("5. Copy key (starts with 'sk-ant-')")
    print("6. Set environment variable:")
    print("   export ANTHROPIC_API_KEY='sk-ant-...'")
    print("\n💡 New accounts get $5 FREE credit!")
    print("="*60)


if __name__ == "__main__":
    print("="*60)
    print("🔑 Anthropic API Key Validator")
    print("="*60)
    print()
    
    # Test key
    success = test_anthropic_key()
    
    # Show pricing
    check_pricing_tier()
    
    if not success:
        # Show setup instructions
        show_setup_instructions()
    
    # Exit code
    if success:
        print("\n✅ All checks passed! Your API key is ready to use.")
        print("\n💡 Next steps:")
        print("   1. Use ClaudePlayer instead of GPT4Player")
        print("   2. Run: python experiments/experiment_algo_vs_claude.py")
        sys.exit(0)
    else:
        print("\n❌ API key validation failed. Fix the issues above.")
        sys.exit(1)
