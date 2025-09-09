#!/usr/bin/env python3
"""
YouTube Affiliate Links Manager - Step 3
Manages affiliate link sections in video descriptions using delimiters
"""

import os
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes - WRITE permissions for YouTube data
SCOPES = ['https://www.googleapis.com/auth/youtube']

# Affiliate section delimiters
START_DELIMITER = "########## AFFILIATE LINKS ##########"
END_DELIMITER = "######## END AFFILIATE LINKS ########"

class YouTubeAffiliateManager:
    def __init__(self, credentials_file='credentials.json'):
        self.credentials_file = credentials_file
        self.token_file = 'token_write.json'
        self.youtube = None
        
    def authenticate(self):
        """Handle OAuth2 authentication flow with WRITE permissions"""
        creds = None
        
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing expired credentials...")
                creds.refresh(Request())
            else:
                print("??  Starting OAuth flow for WRITE permissions...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                
                try:
                    creds = flow.run_local_server(port=0, open_browser=True)
                except Exception:
                    try:
                        creds = flow.run_local_server(port=0, open_browser=False)
                    except Exception:
                        creds = flow.run_console()
            
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
                
        self.youtube = build('youtube', 'v3', credentials=creds)
        print("? Successfully authenticated with YouTube API")
        
    def get_video_details(self, video_id):
        """Get current video details"""
        try:
            request = self.youtube.videos().list(
                part='snippet,status',
                id=video_id
            )
            response = request.execute()
            
            if not response['items']:
                print(f"? Video {video_id} not found")
                return None
                
            return response['items'][0]
            
        except HttpError as e:
            print(f"? API Error: {e}")
            return None
    
    def extract_affiliate_section(self, description):
        """Extract existing affiliate section from description"""
        pattern = f"{re.escape(START_DELIMITER)}(.*?){re.escape(END_DELIMITER)}"
        match = re.search(pattern, description, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        return None
    
    def remove_affiliate_section(self, description):
        """Remove existing affiliate section from description"""
        pattern = f"{re.escape(START_DELIMITER)}.*?{re.escape(END_DELIMITER)}"
        cleaned = re.sub(pattern, '', description, flags=re.DOTALL)
        
        # Clean up extra newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned.strip())
        return cleaned
    
    def add_affiliate_section(self, description, affiliate_content):
        """Add affiliate section to description"""
        # Remove existing section first
        clean_description = self.remove_affiliate_section(description)
        
        # Add new section at the end
        affiliate_section = f"\n\n{START_DELIMITER}\n{affiliate_content}\n{END_DELIMITER}"
        
        return clean_description + affiliate_section
    
    def update_video_affiliate_links(self, video_id, new_affiliate_content):
        """Update only the affiliate links section of a video"""
        try:
            # Get current video details
            video_data = self.get_video_details(video_id)
            if not video_data:
                return False
            
            current_snippet = video_data['snippet']
            current_description = current_snippet['description']
            
            print(f"?? Video: {current_snippet['title']}")
            print(f"?? Current description length: {len(current_description)} characters")
            
            # Extract existing affiliate section
            existing_affiliate = self.extract_affiliate_section(current_description)
            if existing_affiliate:
                print(f"?? Found existing affiliate section ({len(existing_affiliate)} chars)")
            else:
                print("?? No existing affiliate section found - will add new one")
            
            # Create new description with updated affiliate section
            new_description = self.add_affiliate_section(current_description, new_affiliate_content)
            
            print(f"?? New description length: {len(new_description)} characters")
            
            # Update video
            update_data = {
                'id': video_id,
                'snippet': {
                    'title': current_snippet['title'],
                    'description': new_description,
                    'tags': current_snippet.get('tags', []),
                    'categoryId': current_snippet['categoryId']
                }
            }
            
            if current_snippet.get('defaultLanguage'):
                update_data['snippet']['defaultLanguage'] = current_snippet['defaultLanguage']
            
            request = self.youtube.videos().update(
                part='snippet',
                body=update_data
            )
            response = request.execute()
            
            print("? Affiliate links updated successfully!")
            return True
            
        except HttpError as e:
            print(f"? API Error: {e}")
            return False
    
    def preview_changes(self, video_id, new_affiliate_content):
        """Preview what changes will be made without updating"""
        video_data = self.get_video_details(video_id)
        if not video_data:
            return
        
        current_description = video_data['snippet']['description']
        new_description = self.add_affiliate_section(current_description, new_affiliate_content)
        
        print(f"?? Video: {video_data['snippet']['title']}")
        print(f"?? Description length: {len(current_description)} ? {len(new_description)} characters")
        
        # Show before/after affiliate sections
        existing_affiliate = self.extract_affiliate_section(current_description)
        
        print(f"\n?? CURRENT AFFILIATE SECTION:")
        print("-" * 40)
        if existing_affiliate:
            preview = existing_affiliate[:200]
            print(f"'{preview}{'...' if len(existing_affiliate) > 200 else ''}'")
        else:
            print("(No affiliate section found)")
        
        print(f"\n?? NEW AFFILIATE SECTION:")
        print("-" * 40)
        preview = new_affiliate_content[:200]
        print(f"'{preview}{'...' if len(new_affiliate_content) > 200 else ''}'")

def main():
    print("?? YouTube Affiliate Links Manager - Step 3")
    print("=" * 50)
    
    # Test video ID
    test_video_id = "dp3Di1Hdgfk"
    
    # Sample affiliate content
    sample_affiliate_content = """??? RECOMMENDED PRODUCTS & TOOLS:

**Testing & Assessment:**
ApoE Genetic Test - Know your Alzheimer's risk factors
23andMe Health - Code: BRAIN10 - https://example.com/23andme

**Brain Health Devices:**
Red Light Therapy Helmet - As mentioned at 15:30
Vielight Neuro - Code: HEALTH20 - https://example.com/vielight

**Supplements:**
Omega-3 High DHA - What I take daily
Nordic Naturals - Code: LONGEVITY15 - https://example.com/omega3

**Books & Resources:**
"The End of Alzheimer's" by Dr. Dale Bredesen
Amazon - https://example.com/alzheimers-book

?? These are affiliate links - using them supports the channel at no extra cost to you."""
    
    # Initialize manager
    manager = YouTubeAffiliateManager()
    
    try:
        manager.authenticate()
        
        print(f"\n?? Working with video: {test_video_id}")
        print("=" * 40)
        
        # Preview changes first
        print("?? PREVIEW MODE:")
        manager.preview_changes(test_video_id, sample_affiliate_content)
        
        print(f"\n? Update affiliate links section?")
        confirm = input("Type 'yes' to proceed: ").strip().lower()
        
        if confirm == 'yes':
            success = manager.update_video_affiliate_links(
                test_video_id, 
                sample_affiliate_content
            )
            
            if success:
                print(f"\n?? Success! Affiliate section updated.")
                print(f"?? View video: https://youtube.com/watch?v={test_video_id}")
                print(f"\n?? Delimiters used:")
                print(f"Start: {START_DELIMITER}")
                print(f"End: {END_DELIMITER}")
            else:
                print(f"\n? Failed to update affiliate section.")
        else:
            print("??  Update cancelled.")
        
    except Exception as e:
        print(f"? Unexpected error: {e}")

if __name__ == "__main__":
    main()
