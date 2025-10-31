#!/usr/bin/env python3
"""
YouTube Description Backup Tool
Backs up all video descriptions to SQLite database
"""

import os
import sys
import sqlite3
import json
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# YouTube API scope (read-only is sufficient for backup)
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']

# Database configuration
DB_FILE = 'youtube_backups.db'

class YouTubeBackupManager:
    def __init__(self, credentials_file='credentials.json'):
        self.credentials_file = credentials_file
        self.token_file = 'token_readonly.json'
        self.youtube = None
        self.db_conn = None
        
    def authenticate(self):
        """Handle OAuth2 authentication flow"""
        creds = None
        
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing expired credentials...")
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Token refresh failed: {e}")
                    creds = None
            
            if not creds or not creds.valid:
                print("Starting OAuth flow...")
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
    
    def init_database(self):
        """Initialize SQLite database with schema"""
        self.db_conn = sqlite3.connect(DB_FILE)
        cursor = self.db_conn.cursor()
        
        # Create videos table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                published_at TEXT,
                category_id TEXT,
                tags TEXT,
                backed_up_at TEXT
            )
        ''')
        
        # Create backup_runs table for tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backup_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                videos_count INTEGER,
                new_count INTEGER,
                updated_count INTEGER,
                notes TEXT
            )
        ''')
        
        self.db_conn.commit()
        print(f"? Database initialized: {DB_FILE}")
    
    def get_all_channel_videos(self):
        """Get all videos from the authenticated user's channel"""
        print("\nFetching video list from channel...")
        
        # First, get the uploads playlist ID
        try:
            channels_request = self.youtube.channels().list(
                part='contentDetails',
                mine=True
            )
            channels_response = channels_request.execute()
            
            if not channels_response['items']:
                print("? No channel found")
                return []
            
            uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            print(f"? Found uploads playlist: {uploads_playlist_id}")
            
        except HttpError as e:
            print(f"? API Error getting channel: {e}")
            return []
        
        # Now fetch all videos from the uploads playlist
        all_videos = []
        next_page_token = None
        page_count = 0
        
        while True:
            try:
                playlist_request = self.youtube.playlistItems().list(
                    part='snippet',
                    playlistId=uploads_playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                )
                playlist_response = playlist_request.execute()
                
                page_count += 1
                videos_in_page = len(playlist_response['items'])
                all_videos.extend(playlist_response['items'])
                
                print(f"  Page {page_count}: {videos_in_page} videos (total so far: {len(all_videos)})")
                
                next_page_token = playlist_response.get('nextPageToken')
                if not next_page_token:
                    break
                    
            except HttpError as e:
                print(f"? API Error fetching videos: {e}")
                break
        
        print(f"\n? Found {len(all_videos)} total videos")
        return all_videos
    
    def get_video_details(self, video_ids):
        """Get detailed information for a batch of video IDs"""
        try:
            request = self.youtube.videos().list(
                part='snippet',
                id=','.join(video_ids)
            )
            response = request.execute()
            return response['items']
            
        except HttpError as e:
            print(f"? API Error getting video details: {e}")
            return []
    
    def backup_videos(self):
        """Main backup process"""
        # Get all videos from channel
        playlist_items = self.get_all_channel_videos()
        
        if not playlist_items:
            print("No videos to backup")
            return
        
        # Extract video IDs
        video_ids = [item['snippet']['resourceId']['videoId'] for item in playlist_items]
        
        print(f"\nBacking up {len(video_ids)} videos...")
        print("=" * 50)
        
        new_count = 0
        updated_count = 0
        error_count = 0
        
        # Process in batches of 50 (API limit)
        batch_size = 50
        for i in range(0, len(video_ids), batch_size):
            batch = video_ids[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(video_ids) + batch_size - 1) // batch_size
            
            print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} videos)...")
            
            # Get detailed info for this batch
            video_details = self.get_video_details(batch)
            
            # Save each video to database
            for video in video_details:
                try:
                    video_id = video['id']
                    snippet = video['snippet']
                    
                    # Check if video already exists
                    cursor = self.db_conn.cursor()
                    cursor.execute('SELECT video_id FROM videos WHERE video_id = ?', (video_id,))
                    exists = cursor.fetchone()
                    
                    # Prepare data
                    title = snippet.get('title', '')
                    description = snippet.get('description', '')
                    published_at = snippet.get('publishedAt', '')
                    category_id = snippet.get('categoryId', '')
                    tags = json.dumps(snippet.get('tags', []))
                    backed_up_at = datetime.now().isoformat()
                    
                    if exists:
                        # Update existing record
                        cursor.execute('''
                            UPDATE videos 
                            SET title=?, description=?, published_at=?, category_id=?, tags=?, backed_up_at=?
                            WHERE video_id=?
                        ''', (title, description, published_at, category_id, tags, backed_up_at, video_id))
                        updated_count += 1
                        status = "updated"
                    else:
                        # Insert new record
                        cursor.execute('''
                            INSERT INTO videos (video_id, title, description, published_at, category_id, tags, backed_up_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (video_id, title, description, published_at, category_id, tags, backed_up_at))
                        new_count += 1
                        status = "new"
                    
                    self.db_conn.commit()
                    
                    # Show progress every 10 videos
                    if (new_count + updated_count) % 10 == 0:
                        print(f"  Progress: {new_count + updated_count}/{len(video_ids)} videos processed...")
                    
                except Exception as e:
                    print(f"  ? Error saving video {video_id}: {e}")
                    error_count += 1
        
        # Record this backup run
        cursor = self.db_conn.cursor()
        cursor.execute('''
            INSERT INTO backup_runs (timestamp, videos_count, new_count, updated_count, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), len(video_ids), new_count, updated_count, "Full backup"))
        self.db_conn.commit()
        
        # Print summary
        print("\n" + "=" * 50)
        print("BACKUP COMPLETE")
        print("=" * 50)
        print(f"? Total videos: {len(video_ids)}")
        print(f"? New videos backed up: {new_count}")
        print(f"? Existing videos updated: {updated_count}")
        if error_count > 0:
            print(f"? Errors: {error_count}")
        print(f"\n? Database saved: {DB_FILE}")
    
    def show_stats(self):
        """Show database statistics"""
        cursor = self.db_conn.cursor()
        
        # Total videos
        cursor.execute('SELECT COUNT(*) FROM videos')
        total = cursor.fetchone()[0]
        
        # Latest backup
        cursor.execute('SELECT timestamp, videos_count, new_count, updated_count FROM backup_runs ORDER BY id DESC LIMIT 1')
        latest = cursor.fetchone()
        
        print("\n" + "=" * 50)
        print("DATABASE STATISTICS")
        print("=" * 50)
        print(f"Total videos in database: {total}")
        
        if latest:
            print(f"\nLast backup:")
            print(f"  Timestamp: {latest[0]}")
            print(f"  Videos processed: {latest[1]}")
            print(f"  New: {latest[2]}")
            print(f"  Updated: {latest[3]}")
    
    def close(self):
        """Close database connection"""
        if self.db_conn:
            self.db_conn.close()

def main():
    print("=" * 50)
    print("YouTube Description Backup Tool")
    print("=" * 50)
    
    # Check for credentials file
    if not os.path.exists('credentials.json'):
        print("\n? credentials.json not found!")
        print("Please download it from Google Cloud Console first.")
        return
    
    # Initialize manager
    manager = YouTubeBackupManager()
    
    try:
        # Authenticate
        manager.authenticate()
        
        # Initialize database
        manager.init_database()
        
        # Check if database already has data
        cursor = manager.db_conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM videos')
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            print(f"\n? Database already contains {existing_count} videos")
            print("Running backup will update existing records and add new ones.")
        
        # Confirm before proceeding
        print("\n" + "=" * 50)
        response = input("Start backup? (yes/no): ").strip().lower()
        
        if response == 'yes':
            manager.backup_videos()
            manager.show_stats()
        else:
            print("Backup cancelled.")
    
    except KeyboardInterrupt:
        print("\n\n? Backup interrupted by user")
    except Exception as e:
        print(f"\n? Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        manager.close()

if __name__ == "__main__":
    main()
