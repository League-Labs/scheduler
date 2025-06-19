#!/usr/bin/env python3

import requests
import json

# Test the blackout functionality
def test_blackouts():
    base_url = "http://127.0.0.1:5000"
    
    print("Testing blackout functionality...")
    
    # Use an existing schedule from the test data
    schedule_id = "dzEP5I"
    password = "cQhVUE"
    
    print(f"Using existing schedule - ID: {schedule_id}, Password: {password}")
    
    # Test blackout endpoints
    print("\n1. Testing GET /s/{schedule_id}/blackouts")
    blackout_response = requests.get(f"{base_url}/s/{schedule_id}/blackouts")
    print(f"Status: {blackout_response.status_code}")
    print(f"Response: {blackout_response.text}")
    
    print("\n2. Testing POST /s/{schedule_id}/blackouts (with password)")
    test_blackouts_data = ["M08", "T09", "W10"]
    blackout_post_response = requests.post(
        f"{base_url}/s/{schedule_id}/blackouts",
        json=test_blackouts_data,
        headers={'Content-Type': 'application/json'}
    )
    print(f"Status: {blackout_post_response.status_code}")
    print(f"Response: {blackout_post_response.text}")
    
    # Test with password in data
    print("\n3. Testing POST /s/{schedule_id}/blackouts (with password in payload)")
    payload = {"blackouts": test_blackouts_data, "pw": password}
    blackout_post_response2 = requests.post(
        f"{base_url}/s/{schedule_id}/update",
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    print(f"Status: {blackout_post_response2.status_code}")
    print(f"Response: {blackout_post_response2.text}")
    
    # Test schedule info endpoint
    print("\n4. Testing GET /s/{schedule_id}/info")
    info_response = requests.get(f"{base_url}/s/{schedule_id}/info")
    print(f"Status: {info_response.status_code}")
    if info_response.status_code == 200:
        info_data = info_response.json()
        print(f"Blackouts in response: {info_data.get('blackouts', [])}")
    else:
        print(f"Response: {info_response.text}")
    
    print(f"\n5. Visit the schedule page: {base_url}/s/{schedule_id}?pw={password}")
    print(f"6. Visit the schedule page without password: {base_url}/s/{schedule_id}")

if __name__ == "__main__":
    test_blackouts()
