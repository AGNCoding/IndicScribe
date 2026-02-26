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

FOLDER_NAME = "IndicScribe"


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
        logger.error(f"User {user.email} missing tokens - access: {bool(user.access_token)}, refresh: {bool(user.refresh_token)}")
        raise ValueError(f"User {user.email} does not have stored OAuth tokens")
    
    try:
        # Decrypt the stored tokens
        logger.info(f"Attempting to decrypt tokens for user {user.email}")
        access_token = decrypt_token(user.access_token)
        refresh_token = decrypt_token(user.refresh_token)
        logger.info(f"Successfully decrypted tokens for user {user.email}")
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
        logger.info(f"Refreshing expired access token for user {user.email}")
        creds.refresh(Request())
    
    # Build and return Drive service
    drive_service = build('drive', 'v3', credentials=creds)
    logger.info(f"Drive service initialized for user {user.email}")
    
    return drive_service


def list_projects(user: User) -> List[Dict[str, Any]]:
    """
    List all IndicScribe projects from the user's Google Drive.
    
    Searches for files in the IndicScribe folder matching:
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
        # Get the IndicScribe folder ID
        folder_id = get_or_create_indicscribe_folder(user)
        
        # Build the query to search within the folder
        query = (
            f"'{folder_id}' in parents AND "
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


def save_project(user: User, filename: str, content_json: dict, file_name: Optional[str] = None, file_data: Optional[str] = None) -> Dict[str, Any]:
    """
    Save or update a project file on Google Drive in the IndicScribe folder.
    Also saves the associated document/image file if provided.
    
    Creates a new file named 'IndicScribe_{filename}.json' or updates existing.
    If file_data is provided, saves it as 'IndicScribe_{filename}_source' in a subfolder.
    
    Args:
        user: User object with Drive credentials
        filename: Project filename (without IndicScribe_ prefix or .json extension)
        content_json: Full editor state (Quill Delta/HTML as dict or JSON string)
        file_name: (Optional) Name of the original uploaded file
        file_data: (Optional) File data as base64 string or binary data
        
    Returns:
        Dict with keys: id, name, webViewLink, uploaded_file_id (if file saved), uploaded_file_name
        
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
    
    file_name_project = f"IndicScribe_{filename}.json"
    uploaded_file_id = None
    uploaded_file_name = None
    
    try:
        # Get or create the IndicScribe folder
        logger.info(f"Getting/creating IndicScribe folder for user {user.email}")
        folder_id = get_or_create_indicscribe_folder(user)
        logger.info(f"Using folder ID: {folder_id}")
        
        # Check if file already exists in the folder
        query = f"'{folder_id}' in parents AND name='{file_name_project}' AND mimeType='application/json' AND trashed=false"
        logger.info(f"Searching for existing file with query: {query}")
        
        existing = drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id)',
            pageSize=1
        ).execute()
        
        file_id = None
        if existing.get('files'):
            file_id = existing['files'][0]['id']
            logger.info(f"Found existing file {file_id}, will update")
        else:
            logger.info(f"File does not exist, will create new")
        
        # Prepare media upload for JSON content
        media = MediaIoBaseUpload(
            BytesIO(json_content.encode('utf-8')),
            mimetype='application/json',
            resumable=True
        )
        
        if file_id:
            # Update existing file
            logger.info(f"Updating existing file {file_id}")
            result = drive_service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
            logger.info(f"Successfully updated project {file_name_project} in IndicScribe folder for user {user.email}")
        else:
            # Create new file in the folder
            logger.info(f"Creating new file in folder {folder_id}")
            file_metadata = {
                'name': file_name_project,
                'mimeType': 'application/json',
                'parents': [folder_id]
            }
            result = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()
            logger.info(f"Successfully created new project {file_name_project} in IndicScribe folder for user {user.email}")
        
        # If file data is provided, save the original file
        if file_data and file_name:
            try:
                logger.info(f"Saving uploaded file: {file_name} for project {filename}")
                
                # Create or get a "files" subfolder within IndicScribe folder
                files_folder_id = _get_or_create_subfolder(drive_service, folder_id, "uploaded_files")
                
                # Determine MIME type based on file extension
                import mimetypes
                mime_type, _ = mimetypes.guess_type(file_name)
                if mime_type is None:
                    mime_type = 'application/octet-stream'
                
                # Create file metadata
                source_file_name = f"IndicScribe_{filename}_source_{file_name}"
                file_metadata = {
                    'name': source_file_name,
                    'mimeType': mime_type,
                    'parents': [files_folder_id]
                }
                
                # Handle file_data - could be base64 string or binary
                if isinstance(file_data, str):
                    # Assume it's base64 encoded
                    try:
                        import base64
                        file_bytes = base64.b64decode(file_data)
                    except Exception as e:
                        logger.warning(f"Could not decode base64 file data: {e}, using as is")
                        file_bytes = file_data.encode('utf-8')
                else:
                    file_bytes = file_data
                
                # Prepare media upload for the file
                file_media = MediaIoBaseUpload(
                    BytesIO(file_bytes),
                    mimetype=mime_type,
                    resumable=True
                )
                
                # Check if file already exists
                query = f"'{files_folder_id}' in parents AND name='{source_file_name}' AND trashed=false"
                existing_file = drive_service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id)',
                    pageSize=1
                ).execute()
                
                if existing_file.get('files'):
                    # Update existing
                    uploaded_file_id = existing_file['files'][0]['id']
                    drive_service.files().update(
                        fileId=uploaded_file_id,
                        media_body=file_media
                    ).execute()
                    logger.info(f"Updated uploaded file {uploaded_file_id}")
                else:
                    # Create new
                    file_result = drive_service.files().create(
                        body=file_metadata,
                        media_body=file_media,
                        fields='id, name'
                    ).execute()
                    uploaded_file_id = file_result.get('id')
                    logger.info(f"Successfully uploaded source file: {file_name} (ID: {uploaded_file_id})")
                
                uploaded_file_name = file_name
            
            except Exception as e:
                logger.error(f"Error uploading source file for project {filename}: {e}", exc_info=True)
                # Don't fail the entire project save if file upload fails
        
        return {
            'id': result.get('id'),
            'name': result.get('name'),
            'webViewLink': result.get('webViewLink', ''),
            'uploaded_file_id': uploaded_file_id,
            'uploaded_file_name': uploaded_file_name
        }
        
    except Exception as e:
        logger.error(f"Error saving project {file_name_project} for user {user.email}: {e}", exc_info=True)
        raise


def _get_or_create_subfolder(drive_service, parent_folder_id: str, subfolder_name: str) -> str:
    """
    Helper function to get or create a subfolder within a parent folder.
    
    Args:
        drive_service: Google Drive service
        parent_folder_id: ID of the parent folder
        subfolder_name: Name of the subfolder to get or create
        
    Returns:
        str: The folder ID of the subfolder
    """
    try:
        # Check if subfolder already exists
        query = f"'{parent_folder_id}' in parents AND name='{subfolder_name}' AND mimeType='application/vnd.google-apps.folder' AND trashed=false"
        results = drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=1
        ).execute()
        
        files = results.get('files', [])
        if files:
            folder_id = files[0]['id']
            logger.info(f"Found existing subfolder {subfolder_name}: {folder_id}")
            return folder_id
        
        # Create new subfolder
        file_metadata = {
            'name': subfolder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        
        folder = drive_service.files().create(
            body=file_metadata,
            fields='id, name'
        ).execute()
        
        folder_id = folder.get('id')
        logger.info(f"Created new subfolder {subfolder_name}: {folder_id}")
        return folder_id
        
    except Exception as e:
        logger.error(f"Error getting/creating subfolder {subfolder_name}: {e}")
        raise


def load_project(user: User, file_id: str) -> dict:
    """
    Load and retrieve a project file from Google Drive.
    
    Gets the file content by ID and returns the JSON content.
    Also searches for any associated uploaded file and returns its metadata.
    
    Args:
        user: User object with Drive credentials
        file_id: Google Drive file ID
        
    Returns:
        Dict containing the loaded project content and optional uploaded file metadata
        
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
        
        # Try to find associated uploaded file
        try:
            project_name = file_metadata.get('name', '')
            # Extract filename without extension and prefix
            # e.g., "IndicScribe_myproject.json" -> "myproject"
            if project_name.startswith('IndicScribe_') and project_name.endswith('.json'):
                base_filename = project_name[len('IndicScribe_'):-5]  # Remove prefix and .json
                
                # Search for uploaded file with pattern
                folder_id = get_or_create_indicscribe_folder(user)
                files_folder_id = _get_or_create_subfolder(drive_service, folder_id, "uploaded_files")
                
                # Search for source file
                query = f"'{files_folder_id}' in parents AND name contains 'IndicScribe_{base_filename}_source' AND trashed=false"
                results = drive_service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name, mimeType, size)',
                    pageSize=1
                ).execute()
                
                uploaded_files = results.get('files', [])
                if uploaded_files:
                    uploaded_file = uploaded_files[0]
                    content_dict['_uploaded_file'] = {
                        'id': uploaded_file['id'],
                        'name': uploaded_file['name'],
                        'mimeType': uploaded_file.get('mimeType', 'application/octet-stream'),
                        'size': uploaded_file.get('size', 0)
                    }
                    logger.info(f"Found associated uploaded file: {uploaded_file['name']}")
        except Exception as e:
            logger.warning(f"Could not find associated uploaded file for project {file_id}: {e}")
            # Don't fail the load if we can't find the uploaded file
        
        return content_dict
        
    except Exception as e:
        logger.error(f"Error loading project {file_id} for user {user.email}: {e}")
        raise


def get_or_create_indicscribe_folder(user: User) -> str:
    """
    Get or create the IndicScribe folder in the user's Google Drive.
    
    Args:
        user: User object with Drive credentials
        
    Returns:
        str: The folder ID of the IndicScribe folder
        
    Raises:
        ValueError: If user has no Drive credentials
        Exception: If Drive API call fails
    """
    drive_service = get_drive_service(user)
    
    try:
        # Check if IndicScribe folder already exists
        query = f"name='{FOLDER_NAME}' AND mimeType='application/vnd.google-apps.folder' AND trashed=false"
        results = drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=1
        ).execute()
        
        files = results.get('files', [])
        if files:
            folder_id = files[0]['id']
            logger.info(f"Found existing IndicScribe folder {folder_id} for user {user.email}")
            return folder_id
        
        # Create new folder if it doesn't exist
        file_metadata = {
            'name': FOLDER_NAME,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        folder = drive_service.files().create(
            body=file_metadata,
            fields='id, name'
        ).execute()
        
        folder_id = folder.get('id')
        logger.info(f"Created new IndicScribe folder {folder_id} for user {user.email}")
        return folder_id
        
    except Exception as e:
        logger.error(f"Error getting/creating IndicScribe folder for user {user.email}: {e}")
        raise


def get_uploaded_file(user: User, file_id: str) -> bytes:
    """
    Download and retrieve an uploaded file from Google Drive by file ID.
    
    Args:
        user: User object with Drive credentials
        file_id: Google Drive file ID
        
    Returns:
        bytes: The file content as bytes
        
    Raises:
        ValueError: If user has no Drive credentials
        Exception: If file not found or cannot be retrieved
    """
    drive_service = get_drive_service(user)
    
    try:
        # Get file metadata to verify it exists
        file_metadata = drive_service.files().get(
            fileId=file_id,
            fields='id, name, mimeType'
        ).execute()
        
        logger.info(f"Retrieving file {file_metadata.get('name')} (ID: {file_id}) for user {user.email}")
        
        # Get the file content
        file_content = drive_service.files().get_media(fileId=file_id).execute()
        
        logger.info(f"Successfully downloaded file {file_metadata.get('name')} for user {user.email}")
        return file_content
        
    except Exception as e:
        logger.error(f"Error downloading file {file_id} for user {user.email}: {e}")
        raise
