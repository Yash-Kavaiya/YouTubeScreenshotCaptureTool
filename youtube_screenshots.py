#!/usr/bin/env python3
"""
YouTube Video Screenshot Capture Tool
Usage: python youtube_screenshots.py <youtube_url> <interval_seconds>
Example: python youtube_screenshots.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 5
"""

import os
import sys
import re
import subprocess
import argparse
import tempfile
import shutil
from pathlib import Path
import json

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    # Remove invalid characters for Windows/Linux/Mac
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    # Limit length to avoid filesystem issues
    if len(filename) > 200:
        filename = filename[:200]
    return filename

def get_video_info(url):
    """Get video title and duration using yt-dlp"""
    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-playlist',
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)
        return {
            'title': info.get('title', 'untitled'),
            'duration': info.get('duration', 0)
        }
    except subprocess.CalledProcessError as e:
        print(f"Error getting video info: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing video info: {e}")
        return None

def download_video(url, output_path):
    """Download YouTube video using yt-dlp"""
    try:
        cmd = [
            'yt-dlp',
            '-f', 'best[ext=mp4]/best',
            '--no-playlist',
            '-o', output_path,
            url
        ]
        print("Downloading video...")
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error downloading video: {e}")
        return False

def extract_screenshots(video_path, output_dir, interval):
    """Extract screenshots from video at specified intervals using ffmpeg"""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Get video duration using ffprobe
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        
        print(f"Video duration: {duration:.1f} seconds")
        print(f"Taking screenshots every {interval} seconds...")
        
        # Extract screenshots at intervals
        screenshots_taken = 0
        current_time = 0
        
        while current_time <= duration:
            # Format time for filename (e.g., "005s", "010s", "015s")
            time_str = f"{int(current_time):03d}s"
            output_file = os.path.join(output_dir, f"{time_str}.jpg")
            
            # Use ffmpeg to extract frame at specific timestamp
            cmd = [
                'ffmpeg',
                '-ss', str(current_time),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',  # JPEG quality (2 is high quality)
                '-y',  # Overwrite output files
                output_file
            ]
            
            # Run quietly
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            
            screenshots_taken += 1
            print(f"  Screenshot at {current_time}s saved as {time_str}.jpg")
            
            current_time += interval
        
        return screenshots_taken
        
    except subprocess.CalledProcessError as e:
        print(f"Error extracting screenshots: {e}")
        return 0
    except ValueError as e:
        print(f"Error parsing video duration: {e}")
        return 0

def check_dependencies():
    """Check if required tools are installed"""
    dependencies = {
        'yt-dlp': 'yt-dlp --version',
        'ffmpeg': 'ffmpeg -version',
        'ffprobe': 'ffprobe -version'
    }
    
    missing = []
    for tool, cmd in dependencies.items():
        try:
            subprocess.run(cmd.split(), capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append(tool)
    
    if missing:
        print("Error: Missing required dependencies:")
        for tool in missing:
            print(f"  - {tool}")
        print("\nInstallation instructions:")
        print("  Ubuntu/Debian: sudo apt-get install ffmpeg && pip install yt-dlp")
        print("  macOS: brew install ffmpeg && pip install yt-dlp")
        print("  Windows: Download ffmpeg from ffmpeg.org and install yt-dlp with pip")
        return False
    return True

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Extract screenshots from YouTube videos at specified intervals'
    )
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument(
        'interval', 
        type=int, 
        help='Interval in seconds between screenshots'
    )
    parser.add_argument(
        '--keep-video', 
        action='store_true',
        help='Keep the downloaded video file after extraction'
    )
    parser.add_argument(
        '--output-dir',
        default='.',
        help='Base directory for output (default: current directory)'
    )
    
    args = parser.parse_args()
    
    # Validate input
    if args.interval <= 0:
        print("Error: Interval must be greater than 0")
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Get video information
    print(f"Fetching video information...")
    video_info = get_video_info(args.url)
    if not video_info:
        print("Error: Could not fetch video information")
        sys.exit(1)
    
    # Sanitize title for folder name
    safe_title = sanitize_filename(video_info['title'])
    duration = video_info['duration']
    
    print(f"Video title: {video_info['title']}")
    print(f"Video duration: {duration} seconds")
    
    # Create output directory structure
    base_dir = Path(args.output_dir)
    video_dir = base_dir / safe_title
    images_dir = video_dir / 'images'
    
    # Create directories
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # Create temporary directory for video download
    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = os.path.join(temp_dir, 'video.mp4')
        
        # Download video
        if not download_video(args.url, video_path):
            print("Error: Failed to download video")
            sys.exit(1)
        
        print(f"\nVideo downloaded successfully!")
        
        # Extract screenshots
        print(f"\nExtracting screenshots to: {images_dir}")
        screenshot_count = extract_screenshots(video_path, images_dir, args.interval)
        
        if screenshot_count > 0:
            print(f"\nSuccess! {screenshot_count} screenshots saved to:")
            print(f"  {images_dir.absolute()}")
            
            # Optionally keep the video
            if args.keep_video:
                final_video_path = video_dir / f"{safe_title}.mp4"
                shutil.copy2(video_path, final_video_path)
                print(f"\nVideo saved to: {final_video_path.absolute()}")
        else:
            print("\nError: No screenshots were extracted")
            sys.exit(1)
    
    print("\nDone!")

if __name__ == "__main__":
    main()