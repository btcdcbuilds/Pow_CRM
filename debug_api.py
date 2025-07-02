#!/usr/bin/env python3
"""
Simple Antpool API Debug Script
Run this locally to test your API credentials and see exactly what's happening
"""

import time
import hmac
import hashlib
import requests
import json

# Your API credentials
API_KEY = "7653a14dbf4a48fa91dde7fdff262341"
API_SECRET = "75c3fd4dadc44c80ab66cbd9a148ec2f"
USER_ID = "powdigitalio@proton.me"

def generate_signature(user_id, api_key, api_secret, nonce):
    """Generate HMAC-SHA256 signature exactly like Antpool example"""
    message = user_id + api_key + str(nonce)
    signature = hmac.new(
        api_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().upper()
    return signature

def test_api_call():
    """Test a simple API call with detailed logging"""
    print("=== Antpool API Debug Test ===")
    print(f"API Key: {API_KEY}")
    print(f"API Secret: {API_SECRET[:10]}...")
    print(f"User ID: {USER_ID}")
    print()
    
    # Generate nonce (milliseconds)
    nonce = int(time.time() * 1000)
    print(f"Nonce (milliseconds): {nonce}")
    
    # Generate signature
    signature = generate_signature(USER_ID, API_KEY, API_SECRET, nonce)
    print(f"Generated signature: {signature}")
    print()
    
    # Prepare request
    url = "https://antpool.com/api/account.htm"
    params = {
        'key': API_KEY,
        'nonce': nonce,
        'signature': signature,
        'coin': 'BTC'
    }
    
    print(f"Request URL: {url}")
    print(f"Request params: {json.dumps(params, indent=2)}")
    print()
    
    # Make request
    print("Making API request...")
    try:
        response = requests.post(url, data=params, timeout=30)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response JSON: {json.dumps(data, indent=2)}")
                
                if data.get('code') == 0:
                    print("✅ SUCCESS: API call worked!")
                    return True
                else:
                    print(f"❌ API ERROR: {data.get('message', 'Unknown error')}")
                    return False
            except json.JSONDecodeError:
                print(f"❌ INVALID JSON: {response.text}")
                return False
        else:
            print(f"❌ HTTP ERROR: {response.status_code}")
            print(f"Response text: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ REQUEST FAILED: {e}")
        return False

def test_signature_generation():
    """Test signature generation with known values"""
    print("=== Testing Signature Generation ===")
    
    # Test with fixed values
    test_user_id = "test_user"
    test_api_key = "test_key"
    test_api_secret = "test_secret"
    test_nonce = 1234567890000
    
    message = test_user_id + test_api_key + str(test_nonce)
    expected_signature = hmac.new(
        test_api_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().upper()
    
    print(f"Test message: {message}")
    print(f"Test signature: {expected_signature}")
    print()

if __name__ == "__main__":
    # Test signature generation first
    test_signature_generation()
    
    # Test actual API call
    success = test_api_call()
    
    if success:
        print("\n🎉 API test successful! Your credentials work.")
    else:
        print("\n💥 API test failed. Check the error messages above.")

