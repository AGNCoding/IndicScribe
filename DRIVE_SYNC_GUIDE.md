# IndicScribe Google Drive Sync - Troubleshooting & Setup Guide

## ✅ What Was Fixed

1. **Token Encoding Issue**: Replaced URLSafeSerializer with simple base64 encoding to prevent signature mismatch errors
2. **OAuth Configuration**: Moved `access_type` and `prompt` to `authorize_params` in authlib for proper offline token handling
3. **Database**: Fresh database created (old one deleted) to ensure clean token storage

## 🚀 Fresh Setup & Testing

### Step 1: Start the Server

```bash
cd /home/amit/Desktop/IndicScribe
. .venv/bin/activate
uvicorn app.main:app --reload
```

### Step 2: Complete Fresh Login

1. Open browser to http://localhost:8000
2. Click "Login with Google"
3. **IMPORTANT**: The consent screen should appear (this is new!) - ensure you approve or go through full consent
4. Complete OAuth flow

### Step 3: Watch Server Logs for These Messages

During login, look for:

```
✓ Token response keys: [...]
✓ OAuth tokens received - access_token: True, refresh_token: True
✓ Access token successfully decoded
✓ Refresh token successfully decoded  
✓ IndicScribe folder ready for user: [folder_id]
✓ User [email] session created
```

### Step 4: If Tokens Show as False/Decoded Fail

**Problem**: `Has refresh token: False`
- **Cause**: Google OAuth didn't request offline access or consent wasn't shown
- **Solution**: 
  1. Logout
  2. Clear browser cookies for localhost:8000 and accounts.google.com
  3. Re-login and ensure you approve the consent screen
  4. If consent screen doesn't appear, try incognito window

**Problem**: `Token decoding failed: ...`
- **Cause**: Token format issue (shouldn't happen now with base64)
- **Solution**: Delete database and re-login

### Step 5: Test Folder Creation

After successful login, open browser DevTools (F12) Console and run:

```javascript
fetch('/api/debug/test-folder-creation', {method: 'POST'})
  .then(r => r.json())
  .then(d => console.log(d))
```

**Expected Success Response:**
```json
{
  "status": "success",
  "folder_id": "1a2b3c4d5e6f...",
  "message": "Successfully created/retrieved IndicScribe folder"
}
```

**Error Response Example:**
```json
{
  "status": "error",
  "message": "User ... does not have stored OAuth tokens",
  "error_type": "ValueError"
}
```

### Step 6: Test Project Save

1. Upload a file (dashboard → +)
2. Editor should open
3. Click "Save Project" button (amber/gold button with disk icon)
4. Enter project name and save
5. Should see success message

**Expected in Console:**
- `saveProjectToDrive called`
- `Calling api.saveProject with name: ...`
- `API response: {status: "saved", saved_to_drive: true, ...}`
- Success notification: "✓ Project saved to Google Drive: [name]"

### Step 7: Verify in Google Drive

1. Open https://drive.google.com
2. Look for "IndicScribe" folder at root level
3. Inside should be your saved project files named `IndicScribe_[projectname].json`

## 🔍 Diagnostic Commands

### Check Token Status
```bash
cd /home/amit/Desktop/IndicScribe
. .venv/bin/activate
python debug_tokens.py
```

### Check Server Logs for Errors
Look for lines starting with:
- `✗` = Error/failure
- `⚠️` = Warning
- `✓` = Success

### Test Token Encoding
```bash
python -c "
from app.database import encrypt_token, decrypt_token
token = 'ya29.test123'
enc = encrypt_token(token)
dec = decrypt_token(enc)
print(f'Original: {token}')
print(f'Decoded: {dec}')
print(f'Match: {token == dec}')
"
```

## 🐛 Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Refresh token is False | OAuth not requesting offline access | Clear cookies, re-login with consent screen |
| Folder creation fails | No valid tokens or Drive API error | Check token status with debug_tokens.py |
| Projects save locally only | Tokens missing or invalid | Re-login and verify tokens work |
| IndicScribe folder not in Drive | Tokens expired or API failed silently | Check server logs for errors |
| Folder in Drive but projects don't save | File write permissions issue | Check Drive API scope includes drive.file |

## 📝 Expected Flow (Successful)

```
1. User clicks "Login with Google"
   ↓
2. Redirected to Google OAuth consent screen
   ↓
3. User approves and returns to app with tokens
   ↓
4. Server: auth_callback receives access_token + refresh_token
   ↓
5. Server: Encodes tokens with base64 and stores in database
   ↓
6. Server: Verifies tokens decode correctly
   ↓
7. Server: Creates/retrieves IndicScribe folder in Drive
   ↓
8. Server: Sets user session and redirects to dashboard
   ↓
9. User brings files or creates project
   ↓
10. User clicks "Save Project"
    ↓
11. Frontend calls api.saveProject(name, content)
    ↓
12. Backend: get_drive_service() rebuilds Credentials from stored tokens
    ↓
13. Backend: get_or_create_indicscribe_folder() finds/creates IndicScribe folder
    ↓
14. Backend: save_project() creates/updates JSON file in IndicScribe folder
    ↓
15. Frontend: Shows "✓ Project saved to Google Drive" success message
```

## 🔧 Debug API Endpoints Available

- `GET /api/me` - Check current user profile and first_project_created flag
- `GET /api/debug/auth` - Check token status (has/valid/decryptable)
- `POST /api/debug/test-folder-creation` - Manually test IndicScribe folder creation
- `GET /api/projects` - List saved projects from Drive
- `POST /api/projects` - Save a project
- `GET /api/projects/{file_id}` - Load a specific project

## ⚠️ Important Notes

1. **First Login is Critical**: Ensure the Google consent screen appears on first login - this is when refresh tokens are issued
2. **Tokens are Base64 Encoded**: Not encrypted with a key. Database file shouldn't be publicly exposed.
3. **Token Refresh**: Google Credentials object handles token refresh automatically
4. **Session Timeout**: Users stay logged in via session cookie. Refresh tokens are used for API calls.

---

**After following this guide, the "IndicScribe" folder should appear in your Google Drive and projects should save automatically!**
