#!/usr/bin/env python3
"""
Debug script to check OAuth token storage and validation
"""
import os
import sys
from pathlib import Path

# Add the app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import (
    SessionLocal, User, decrypt_token, encrypt_token
)
from app.services.drive_client import get_drive_service
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_users():
    """Check all users in database and their token status"""
    db = SessionLocal()
    users = db.query(User).all()
    
    print(f"\n{'='*60}")
    print(f"Total users in database: {len(users)}")
    print(f"{'='*60}\n")
    
    if not users:
        print("❌ No users found in database. Login first!")
        return
    
    for user in users:
        print(f"\n📧 User: {user.email}")
        print(f"   Google ID: {user.google_id}")
        print(f"   Has access token: {bool(user.access_token)}")
        print(f"   Has refresh token: {bool(user.refresh_token)}")
        print(f"   First project created: {bool(user.first_project_created)}")
        
        # Try to decrypt tokens
        if user.access_token:
            try:
                decrypted = decrypt_token(user.access_token)
                print(f"   ✓ Access token decrypts successfully")
                print(f"     Starts with: {decrypted[:30]}...")
            except Exception as e:
                print(f"   ✗ Access token decryption failed: {e}")
        
        if user.refresh_token:
            try:
                decrypted = decrypt_token(user.refresh_token)
                print(f"   ✓ Refresh token decrypts successfully")
                print(f"     Starts with: {decrypted[:30]}...")
            except Exception as e:
                print(f"   ✗ Refresh token decryption failed: {e}")
        
        # Try to initialize Drive service
        if user.access_token and user.refresh_token:
            try:
                print(f"\n   Testing Drive API access...")
                service = get_drive_service(user)
                
                # Try to list files
                results = service.files().list(
                    spaces='drive',
                    fields='files(id, name, mimeType)',
                    pageSize=5
                ).execute()
                
                files = results.get('files', [])
                print(f"   ✓ Drive API access successful!")
                print(f"     Can list files: {len(files)} files found")
                
                # Check for IndicScribe folder
                indicscribe_files = [f for f in files if 'IndicScribe' in f.get('name', '')]
                if indicscribe_files:
                    print(f"     ✓ Found IndicScribe folder!")
                    for f in indicscribe_files:
                        print(f"        - {f.get('name')} (ID: {f.get('id')})")
                else:
                    print(f"     ℹ️  No IndicScribe folder found in recent files")
                    
                    # Try to search for it specifically
                    query = "name='IndicScribe' AND mimeType='application/vnd.google-apps.folder' AND trashed=false"
                    search_results = service.files().list(
                        q=query,
                        spaces='drive',
                        fields='files(id, name)'
                    ).execute()
                    
                    search_files = search_results.get('files', [])
                    if search_files:
                        print(f"     ✓ Search found IndicScribe folder!")
                        for f in search_files:
                            print(f"        - {f.get('name')} (ID: {f.get('id')})")
                    else:
                        print(f"     ✗ No IndicScribe folder exists - needs to be created")
                        
            except Exception as e:
                print(f"   ✗ Drive API access failed: {e}")
                logger.exception(f"Drive API error for {user.email}")
        else:
            print(f"   ✗ Cannot test Drive API - tokens missing")
    
    db.close()

def test_token_encryption():
    """Test token encryption/decryption"""
    print(f"\n{'='*60}")
    print("Testing Token Encoding")
    print(f"{'='*60}\n")
    
    test_token = "ya29.test_token_1234567890"
    
    try:
        encrypted = encrypt_token(test_token)
        print(f"✓ Token encoded successfully")
        print(f"  Original: {test_token}")
        print(f"  Encoded: {encrypted}")
        
        decrypted = decrypt_token(encrypted)
        print(f"✓ Token decoded successfully")
        print(f"  Decoded: {decrypted}")
        
        if decrypted == test_token:
            print(f"✓ Encoding/Decoding working correctly")
        else:
            print(f"✗ Decoded token doesn't match original!")
    except Exception as e:
        print(f"✗ Token encoding test failed: {e}")
        logger.exception("Encoding test failed")

if __name__ == "__main__":
    print("\n🔍 IndicScribe Token & Drive API Diagnostic")
    
    test_token_encryption()
    check_users()
    
    print(f"\n{'='*60}\n")
