#!/usr/bin/env python3
"""
YouTube Channel Reader - Get most recent video title
Step 1: Read-only authentication and basic channel access
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes - read-only access to YouTube data
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']

class YouTubeChannelReader:
    def __init__(self, credentials_file='credentials.json'):
        self.credentials_file = credentials_file
        self.token_file = 'token.json'
        self.youtube = None
        
    def authenticate(self):
        """Handle OAuth2 authentication flow"""
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
                print("Starting OAuth flow...")
                print("This will open your browser for authentication.")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
                
        # Build YouTube service
        self.youtube = build('youtube', 'v3', credentials=creds)
        print("? Successfully authenticated with YouTube API")
        
    def get_channel_info(self):
        """Get basic info about the authenticated channel"""
        try:
            request = self.youtube.channels().list(
                part='snippet,statistics',
                mine=True
            )
            response = request.execute()
            
            if not response['items']:
                print("? No channel found for this account")
                return None
                
            channel = response['items'][0]
            channel_info = {
                'title': channel['snippet']['title'],
                'id': channel['id'],
                'subscriber_count': channel['statistics'].get('subscriberCount', 'Hidden'),
                'video_count': channel['statistics']['videoCount']
            }
            
            print(f"?? Channel: {channel_info['title']}")
            print(f"?? Videos: {channel_info['video_count']}")
            print(f"?? Subscribers: {channel_info['subscriber_count']}")
            
            return channel_info
            
        except HttpError as e:
            print(f"? API Error: {e}")
            return None
    
    def get_latest_video(self):
        """Get the most recent video from the channel"""
        try:
            # Get channel's uploads playlist
            channels_response = self.youtube.channels().list(
                mine=True,
                part='contentDetails'
            ).execute()
            
            if not channels_response['items']:
                print("? No channel found")
                return None
                
            uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Get the most recent video from uploads playlist
            playlist_response = self.youtube.playlistItems().list(
                playlistId=uploads_playlist_id,
                part='snippet',
                maxResults=1
            ).execute()
            
            if not playlist_response['items']:
                print("? No videos found in channel")
                return None
                
            latest_video = playlist_response['items'][0]['snippet']
            video_info = {
                'title': latest_video['title'],
                'video_id': latest_video['resourceId']['videoId'],
                'published_at': latest_video['publishedAt'],
                'description': latest_video.get('description', '')
            }
            
            print(f"?? Latest Video: {video_info['title']}")
            print(f"?? Published: {video_info['published_at']}")
            print(f"?? Video ID: {video_info['video_id']}")
            print(f"?? Description length: {len(video_info['description'])} characters")
            
            return video_info
            
        except HttpError as e:
            print(f"? API Error: {e}")
            return None

def main():
    print("?? YouTube Channel Reader - Step 1")
    print("=" * 40)
    
    # Check if credentials file exists
    if not os.path.exists('credentials.json'):
        print("? credentials.json not found!")
        print("Please download it from Google Cloud Console first.")
        return
    
    # Initialize reader
    reader = YouTubeChannelReader()
    
    try:
        # Authenticate
        reader.authenticate()
        
        # Get channel info
        print("\n?? Channel Information:")
        print("-" * 25)
        channel_info = reader.get_channel_info()
        
        if channel_info:
            # Get latest video
            print(f"\n?? Latest Video Information:")
            print("-" * 30)
            latest_video = reader.get_latest_video()
            
            if latest_video:
                print(f"\n? Success! Found your most recent video:")
                print(f"'{latest_video['title']}'")
        
    except Exception as e:
        print(f"? Unexpected error: {e}")
        print("Make sure you've set up the Google Cloud project correctly.")

if __name__ == "__main__":
    main()
