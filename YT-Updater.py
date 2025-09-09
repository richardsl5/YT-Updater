#!/usr/bin/env python3
"""
YouTube Video Description Updater - Step 2
Write permissions and video description updating
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes - WRITE permissions for YouTube data
SCOPES = ['https://www.googleapis.com/auth/youtube']

class YouTubeVideoUpdater:
    def __init__(self, credentials_file='credentials.json'):
        self.credentials_file = credentials_file
        self.token_file = 'token_write.json'  # Different token file for write permissions
        self.youtube = None
        
    def authenticate(self):
        """Handle OAuth2 authentication flow with WRITE permissions"""
        creds = None
        
        # Load existing token if available
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        # If no valid credentials, run OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing expired credentials...")
                creds.refresh(Request())
            else:
                print("??  Starting OAuth flow for WRITE permissions...")
                print("This requires full YouTube access - you'll see additional permissions.")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                
                # Try automatic browser opening first
                try:
                    creds = flow.run_local_server(port=0, open_browser=True)
                except Exception as e:
                    print(f"Automatic browser opening failed: {e}")
                    print("\n?? Trying manual authentication...")
                    
                    try:
                        # Try without opening browser
                        creds = flow.run_local_server(port=0, open_browser=False)
                    except Exception as e2:
                        print(f"Local server method failed: {e2}")
                        print("\n?? Using console-based authentication...")
                        
                        # Fallback to console flow
                        creds = flow.run_console()
            
            # Save credentials for next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
                
        # Build YouTube service
        self.youtube = build('youtube', 'v3', credentials=creds)
        print("? Successfully authenticated with YouTube API (WRITE permissions)")
        
    def get_video_details(self, video_id):
        """Get current video details including description"""
        try:
            request = self.youtube.videos().list(
                part='snippet,status',
                id=video_id
            )
            response = request.execute()
            
            if not response['items']:
                print(f"? Video {video_id} not found or not accessible")
                return None
                
            video = response['items'][0]
            video_info = {
                'title': video['snippet']['title'],
                'description': video['snippet']['description'],
                'tags': video['snippet'].get('tags', []),
                'category_id': video['snippet']['categoryId'],
                'default_language': video['snippet'].get('defaultLanguage'),
                'published_at': video['snippet']['publishedAt']
            }
            
            print(f"?? Video: {video_info['title']}")
            print(f"?? Published: {video_info['published_at']}")
            print(f"?? Current description length: {len(video_info['description'])} characters")
            print(f"???  Tags: {len(video_info['tags'])} tags")
            
            return video_info
            
        except HttpError as e:
            print(f"? API Error getting video details: {e}")
            return None
    
    def update_video_description(self, video_id, new_description, title=None, tags=None):
        """Update video description (and optionally title/tags)"""
        try:
            # First get current video details to preserve other fields
            current_video = self.get_video_details(video_id)
            if not current_video:
                return False
            
            # Prepare update data
            video_data = {
                'id': video_id,
                'snippet': {
                    'title': title or current_video['title'],
                    'description': new_description,
                    'tags': tags or current_video['tags'],
                    'categoryId': current_video['category_id']
                }
            }
            
            # Add default language if it exists
            if current_video['default_language']:
                video_data['snippet']['defaultLanguage'] = current_video['default_language']
            
            print(f"\n?? Updating video description...")
            print(f"?? New description length: {len(new_description)} characters")
            
            # Make the update request
            request = self.youtube.videos().update(
                part='snippet',
                body=video_data
            )
            response = request.execute()
            
            print("? Video description updated successfully!")
            return True
            
        except HttpError as e:
            print(f"? API Error updating video: {e}")
            if "quotaExceeded" in str(e):
                print("?? Quota exceeded - try again tomorrow or request quota increase")
            return False
        except Exception as e:
            print(f"? Unexpected error: {e}")
            return False

def main():
    print("?? YouTube Video Description Updater - Step 2")
    print("=" * 50)
    
    # Test video ID
    test_video_id = "dp3Di1Hdgfk"
    
    # Check if credentials file exists
    if not os.path.exists('credentials.json'):
        print("? credentials.json not found!")
        print("Please download it from Google Cloud Console first.")
        return
    
    # Initialize updater
    updater = YouTubeVideoUpdater()
    
    try:
        # Authenticate with write permissions
        updater.authenticate()
        
        print(f"\n?? Getting details for video: {test_video_id}")
        print("-" * 40)
        
        # Get current video details
        video_info = updater.get_video_details(test_video_id)
        
        if video_info:
            print(f"\n?? Current Description Preview:")
            print("-" * 35)
            current_desc = video_info['description']
            preview_length = min(200, len(current_desc))
            print(f"'{current_desc[:preview_length]}{'...' if len(current_desc) > preview_length else ''}'")
            
            # Create updated description
            updated_description = current_desc + "\n\n---\nThis is UPDATED text"
            
            print(f"\n? Ready to update description?")
            print(f"Will add: '\\n\\n---\\nThis is UPDATED text'")
            
            confirm = input("Type 'yes' to proceed: ").strip().lower()
            
            if confirm == 'yes':
                success = updater.update_video_description(
                    test_video_id, 
                    updated_description
                )
                
                if success:
                    print(f"\n?? Success! Video description updated.")
                    print(f"?? Check it out: https://youtube.com/watch?v={test_video_id}")
                else:
                    print(f"\n? Failed to update video description.")
            else:
                print("??  Update cancelled.")
        
    except Exception as e:
        print(f"? Unexpected error: {e}")

if __name__ == "__main__":
    main()
