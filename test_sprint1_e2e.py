#!/usr/bin/env python3
"""
End-to-end test for Sprint 1 functionality
"""

import os
import tempfile
import shutil
from app import app

def test_sprint1_end_to_end():
    """Test the complete Sprint 1 functionality"""
    print("Testing Sprint 1 end-to-end functionality...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set the app's data directory to our temp directory
        app.config['DATA_DIR'] = temp_dir
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            print("\n1. Testing home page...")
            response = client.get('/')
            assert response.status_code == 200, f"Home page failed: {response.status_code}"
            print("✓ Home page loads successfully")
            
            print("\n2. Testing new schedule creation...")
            response = client.get('/new')
            assert response.status_code == 302, f"New schedule creation failed: {response.status_code}"
            
            # Extract schedule ID from redirect location
            location = response.headers.get('Location')
            assert '/s/' in location, f"Unexpected redirect location: {location}"
            schedule_id = location.split('/s/')[-1]
            print(f"✓ New schedule created with ID: {schedule_id}")
            
            print("\n3. Testing schedule page...")
            response = client.get(f'/s/{schedule_id}')
            assert response.status_code == 200, f"Schedule page failed: {response.status_code}"
            
            # Extract user ID from session or response content
            # For now, we'll get it from the previous session
            with client.session_transaction() as sess:
                user_id = sess.get('user_id')
            
            assert user_id is not None, "User ID not found in session"
            print(f"✓ Schedule page loads successfully, user ID: {user_id}")
            
            print("\n4. Testing user page...")
            response = client.get(f'/u/{schedule_id}/{user_id}')
            assert response.status_code == 200, f"User page failed: {response.status_code}"
            print("✓ User page loads successfully")
            
            print("\n5. Testing file structure...")
            # Check that schedule directory was created
            schedule_dir = os.path.join(temp_dir, schedule_id)
            assert os.path.exists(schedule_dir), f"Schedule directory not created: {schedule_dir}"
            
            # Check that schedule.json exists
            schedule_file = os.path.join(schedule_dir, 'schedule.json')
            assert os.path.exists(schedule_file), f"Schedule file not created: {schedule_file}"
            print(f"✓ File structure correct: {schedule_dir}/schedule.json")
            
            print("\n6. Testing user data saving...")
            # Set a name in session first
            with client.session_transaction() as sess:
                sess['name'] = 'Test User'
                sess['user_id'] = user_id
            
            # Save some selections
            selections = ['mon-9', 'tue-10', 'wed-11']
            response = client.post(f'/u/{schedule_id}/{user_id}/selections',
                                 json=selections,
                                 content_type='application/json')
            assert response.status_code == 200, f"Saving selections failed: {response.status_code}"
            
            # Check that user file was created
            user_file = os.path.join(schedule_dir, f'{user_id}.json')
            assert os.path.exists(user_file), f"User file not created: {user_file}"
            print(f"✓ User data saved correctly: {schedule_dir}/{user_id}.json")
            
            print("\n7. Testing schedule info API...")
            response = client.get(f'/s/{schedule_id}/info')
            assert response.status_code == 200, f"Schedule info failed: {response.status_code}"
            
            data = response.get_json()
            assert data['count'] == 1, f"Expected 1 user, got {data['count']}"
            assert len(data['dayhours']) == 3, f"Expected 3 selections, got {len(data['dayhours'])}"
            print("✓ Schedule info API working correctly")
            
            print("\n✅ All Sprint 1 end-to-end tests passed!")

if __name__ == "__main__":
    test_sprint1_end_to_end()
