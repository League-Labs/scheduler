#!/usr/bin/env python3
"""
Test script to verify Sprint 1 implementation:
- Files saved in schedule_id/user_id.json format
- Schedule page layout has URL and users list below schedule box
"""

import os
import json
import tempfile
import shutil
from app import app, get_schedule_path, get_user_path, get_schedule_directory, save_schedule_data, save_user_data, get_all_users_for_schedule

def test_file_structure():
    """Test that files are saved in the correct Sprint 1 structure"""
    print("Testing Sprint 1 file structure...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set the app's data directory to our temp directory
        app.config['DATA_DIR'] = temp_dir
        
        schedule_id = "test_schedule_123"
        user_id = "test_user_456"
        
        # Test schedule data saving
        schedule_data = {
            'id': schedule_id,
            'created_at': '2025-06-17T10:00:00',
            'creator_id': user_id
        }
        
        success = save_schedule_data(schedule_id, schedule_data)
        assert success, "Failed to save schedule data"
        
        # Check that schedule directory was created
        schedule_dir = get_schedule_directory(schedule_id)
        assert os.path.exists(schedule_dir), f"Schedule directory not created: {schedule_dir}"
        
        # Check that schedule.json exists in the correct location
        schedule_path = get_schedule_path(schedule_id)
        expected_path = os.path.join(temp_dir, schedule_id, "schedule.json")
        assert schedule_path == expected_path, f"Expected path {expected_path}, got {schedule_path}"
        assert os.path.exists(schedule_path), f"Schedule file not found: {schedule_path}"
        
        print(f"✓ Schedule directory created: {schedule_dir}")
        print(f"✓ Schedule file created: {schedule_path}")
        
        # Test user data saving
        user_data = {
            'name': 'Test User',
            'selections': ['mon-9', 'tue-10', 'wed-11'],
            'updated_at': '2025-06-17T10:30:00'
        }
        
        success = save_user_data(schedule_id, user_id, user_data)
        assert success, "Failed to save user data"
        
        # Check that user file exists in the correct location
        user_path = get_user_path(schedule_id, user_id)
        expected_user_path = os.path.join(temp_dir, schedule_id, f"{user_id}.json")
        assert user_path == expected_user_path, f"Expected user path {expected_user_path}, got {user_path}"
        assert os.path.exists(user_path), f"User file not found: {user_path}"
        
        print(f"✓ User file created: {user_path}")
        
        # Test getting all users for schedule
        users = get_all_users_for_schedule(schedule_id)
        assert len(users) == 1, f"Expected 1 user, got {len(users)}"
        assert users[0]['id'] == user_id, f"Expected user ID {user_id}, got {users[0]['id']}"
        assert users[0]['name'] == 'Test User', f"Expected name 'Test User', got {users[0]['name']}"
        
        print(f"✓ User list retrieved correctly: {users}")
        
        # Test with multiple users
        user_id_2 = "test_user_789"
        user_data_2 = {
            'name': 'Another User',
            'selections': ['thu-14', 'fri-15'],
            'updated_at': '2025-06-17T11:00:00'
        }
        
        save_user_data(schedule_id, user_id_2, user_data_2)
        users = get_all_users_for_schedule(schedule_id)
        assert len(users) == 2, f"Expected 2 users, got {len(users)}"
        
        print(f"✓ Multiple users handled correctly: {len(users)} users")
        
        # Check directory structure
        print("\nDirectory structure:")
        for root, dirs, files in os.walk(temp_dir):
            level = root.replace(temp_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f"{subindent}{file}")
        
        print("\n✅ All Sprint 1 file structure tests passed!")

def test_template_structure():
    """Test that both schedule and user templates have the correct layout"""
    print("\nTesting Sprint 1 template structure...")
    
    # Test schedule template
    schedule_template_path = "/Users/eric/proj/league/docker/scheduler/templates/schedule.html"
    
    with open(schedule_template_path, 'r') as f:
        schedule_content = f.read()
    
    # Check that schedule grid comes before URL display
    grid_pos = schedule_content.find('id="schedule-grid"')
    url_pos = schedule_content.find('Share this link with others')
    users_pos = schedule_content.find('Respondents ({{ users|length }})')
    
    assert grid_pos != -1, "Schedule grid not found in schedule template"
    assert url_pos != -1, "URL display not found in schedule template"
    assert users_pos != -1, "Users list not found in schedule template"
    
    assert grid_pos < url_pos, "Schedule grid should come before URL display in schedule template"
    assert url_pos < users_pos, "URL display should come before users list in schedule template"
    
    print("✓ Schedule template: Schedule grid appears before URL and users list")
    
    # Test user template
    user_template_path = "/Users/eric/proj/league/docker/scheduler/templates/user.html"
    
    with open(user_template_path, 'r') as f:
        user_content = f.read()
    
    # Check that schedule grid comes before URL display in user template too
    user_grid_pos = user_content.find('id="schedule-grid"')
    user_url_pos = user_content.find('Schedule link:')
    user_users_pos = user_content.find('All Respondents ({{ users|length }})')
    
    assert user_grid_pos != -1, "Schedule grid not found in user template"
    assert user_url_pos != -1, "URL display not found in user template"
    assert user_users_pos != -1, "Users list not found in user template"
    
    assert user_grid_pos < user_url_pos, "Schedule grid should come before URL display in user template"
    assert user_url_pos < user_users_pos, "URL display should come before users list in user template"
    
    print("✓ User template: Schedule grid appears before URL and users list")
    print("✅ Template structure test passed!")

if __name__ == "__main__":
    test_file_structure()
    test_template_structure()
    print("\n🎉 All Sprint 1 tests passed successfully!")
