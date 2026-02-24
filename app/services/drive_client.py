"""
Google Drive Client for IndicScribe project management.
Handles listing, saving, and loading projects from Google Drive.
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
from io import BytesIO

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from app.database import User, decrypt_token

logger = logging.getLogger("indic-scribe.drive")


def get_drive_service(user: User):
    """
    Create and return a Google Drive service for the authenticated user.
    
    Reconstructs Credentials using the user's stored access_token and refresh_token.
    
    Args:
        user: User object with encrypted access_token and refresh_token
        
    Returns:
        google.googleapiclient.discovery.Resource: Drive service resource
        
    Raises:
        ValueError: If tokens are missing or cannot be decrypted
    """
    if not user.access_token or not user.refresh_token:
        raise ValueError(f"User {user.email} does not have stored OAuth tokens")
    
    try:
        # Decrypt the stored tokens
        access_token = decrypt_token(user.access_token)
        refresh_token = decrypt_token(user.refresh_token)
    except ValueError as e:
        logger.error(f"Failed to decrypt tokens for user {user.email}: {e}")
        raise
    
    # Reconstruct credentials object
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=['https://www.googleapis.com/auth/drive.file']
    )
    
    # Refresh the access token if needed
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    
    # Build and return Drive service
    drive_service = build('drive', 'v3', credentials=creds)
    logger.info(f"Drive service initialized for user {user.email}")
    
    return drive_service


def list_projects(user: User) -> List[Dict[str, Any]]:
    """
    List all IndicScribe projects from the user's Google Drive.
    
    Searches for files matching:
    - mimeType = 'application/json'
    - name contains 'IndicScribe_'
    - trashed = false
    
    Args:
        user: User object with Drive credentials
        
    Returns:
        List of dicts with keys: id, name, createdTime
    """
    try:
        drive_service = get_drive_service(user)
    except ValueError as e:
        logger.warning(f"Cannot list projects for user {user.email}: {e}")
        return []
    
    try:
        # Build the query
        query = (
            "mimeType='application/json' AND "
            "name contains 'IndicScribe_' AND "
            "trashed=false"
        )
        
        # Execute the query
        results = drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, createdTime)',
            pageSize=100
        ).execute()
        
        files = results.get('files', [])
        logger.info(f"Retrieved {len(files)} projects for user {user.email}")
        
        # Return list of dicts with required fields
        return [
            {
                'id': file['id'],
                'name': file['name'],
                'createdTime': file.get('createdTime', '')
            }
            for file in files
        ]
        
    except Exception as e:
        logger.error(f"Error listing projects for user {user.email}: {e}")
        raise


def save_project(user: User, filename: str, content_json: dict) -> Dict[str, Any]:
    """
    Save or update a project file on Google Drive.
    
    Creates a new file named 'IndicScribe_{filename}.json' or updates existing.
    
    Args:
        user: User object with Drive credentials
        filename: Project filename (without IndicScribe_ prefix or .json extension)
        content_json: Full editor state (Quill Delta/HTML as dict or JSON string)
        
    Returns:
        Dict with keys: id, name, webViewLink
        
    Raises:
        ValueError: If user has no Drive credentials
        Exception: If Drive API call fails
    """
    drive_service = get_drive_service(user)
    
    # Handle content - convert to JSON string if dict
    if isinstance(content_json, dict):
        json_content = json.dumps(content_json)
    else:
        json_content = str(content_json)
    
    file_name = f"IndicScribe_{filename}.json"
    
    try:
        # Check if file already exists
        query = f"name='{file_name}' AND mimeType='application/json' AND trashed=false"
        existing = drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id)',
            pageSize=1
        ).execute()
        
        file_id = None
        if existing.get('files'):
            file_id = existing['files'][0]['id']
        
        # Prepare media upload
        media = MediaIoBaseUpload(
            BytesIO(json_content.encode('utf-8')),
            mimetype='application/json',
            resumable=True
        )
        
        if file_id:
            # Update existing file
            result = drive_service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
            logger.info(f"Updated project {file_name} for user {user.email}")
        else:
            # Create new file
            file_metadata = {
                'name': file_name,
                'mimeType': 'application/json'
            }
            result = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()
            logger.info(f"Created new project {file_name} for user {user.email}")
        
        return {
            'id': result.get('id'),
            'name': result.get('name'),
            'webViewLink': result.get('webViewLink', '')
        }
        
    except Exception as e:
        logger.error(f"Error saving project {file_name} for user {user.email}: {e}")
        raise


def load_project(user: User, file_id: str) -> dict:
    """
    Load and retrieve a project file from Google Drive.
    
    Gets the file content by ID and returns the JSON content.
    
    Args:
        user: User object with Drive credentials
        file_id: Google Drive file ID
        
    Returns:
        Dict containing the loaded project content
        
    Raises:
        ValueError: If user has no Drive credentials
        Exception: If file not found or cannot be retrieved
    """
    drive_service = get_drive_service(user)
    
    try:
        # Get the file metadata first to verify it exists
        file_metadata = drive_service.files().get(
            fileId=file_id,
            fields='id, name, mimeType'
        ).execute()
        
        # Get the file content
        file_content = drive_service.files().get_media(fileId=file_id).execute()
        
        # Parse JSON content
        if isinstance(file_content, bytes):
            content_dict = json.loads(file_content.decode('utf-8'))
        else:
            content_dict = json.loads(file_content)
        
        logger.info(f"Loaded project {file_metadata.get('name')} for user {user.email}")
        return content_dict
        
    except Exception as e:
        logger.error(f"Error loading project {file_id} for user {user.email}: {e}")
        raise
