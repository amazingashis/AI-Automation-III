"""
Test script to check LMStudio connectivity and debug the "Failed to fetch" error.
"""

import requests
import json

def test_lmstudio_connection():
    """Test connection to LMStudio server."""
    
    base_url = "http://localhost:1234/v1"
    model = "google/gemma-3n-e4b"
    
    print(f"Testing connection to LMStudio at: {base_url}")
    print(f"Using model: {model}")
    print("-" * 50)
    
    # Test 1: Check if server is responding
    try:
        print("Test 1: Checking server health...")
        response = requests.get(f"{base_url.replace('/v1', '')}/health", timeout=10)
        print(f"✓ Server responded with status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to LMStudio server")
        print("  Make sure LMStudio is running and accessible")
        return False
    except Exception as e:
        print(f"✗ Server health check failed: {e}")
    
    # Test 2: Check models endpoint
    try:
        print("\nTest 2: Checking available models...")
        response = requests.get(f"{base_url}/models", timeout=10)
        if response.status_code == 200:
            models = response.json()
            print(f"✓ Found {len(models.get('data', []))} available models")
            for model_info in models.get('data', []):
                print(f"  - {model_info.get('id', 'Unknown')}")
        else:
            print(f"✗ Models endpoint returned: {response.status_code}")
    except Exception as e:
        print(f"✗ Models check failed: {e}")
    
    # Test 3: Try a simple chat completion
    try:
        print("\nTest 3: Testing chat completion...")
        headers = {'Content-Type': 'application/json'}
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": "Hello, can you respond with just 'Hi there!'?"}
            ],
            "max_tokens": 50,
            "temperature": 0.1
        }
        
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"✓ Chat completion successful: {content}")
            return True
        else:
            print(f"✗ Chat completion failed: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"✗ Chat completion test failed: {e}")
    
    return False

def test_different_urls():
    """Test different URL variations."""
    
    urls_to_test = [
        "http://localhost:1234/v1",
        "http://127.0.0.1:1234/v1",
        "http://localhost:1234",
        "http://127.0.0.1:1234"
    ]
    
    print("\nTesting different URL variations:")
    print("-" * 50)
    
    for url in urls_to_test:
        try:
            print(f"Testing: {url}")
            response = requests.get(f"{url.replace('/v1', '')}/health", timeout=5)
            print(f"  ✓ Success: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"  ✗ Connection failed")
        except Exception as e:
            print(f"  ✗ Error: {e}")

if __name__ == "__main__":
    print("LMStudio Connection Test")
    print("=" * 50)
    
    success = test_lmstudio_connection()
    
    if not success:
        test_different_urls()
        
        print("\nTroubleshooting Tips:")
        print("-" * 50)
        print("1. Make sure LMStudio is running")
        print("2. Check that a model is loaded in LMStudio")
        print("3. Verify LMStudio server is enabled")
        print("4. Check firewall settings")
        print("5. Try different port numbers if 1234 is not working")
        print("6. Look at LMStudio console for error messages")
    else:
        print("\n✓ LMStudio connection test passed!")
        print("The mapping generation should work now.")
