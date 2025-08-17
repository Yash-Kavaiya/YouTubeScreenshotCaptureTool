#!/usr/bin/env python3
"""
YouTube Video Screenshot Capture Tool with Complete Duplicate Removal and PDF Generation
Usage: python youtube_screenshots.py <youtube_url> <interval_seconds>
Example: python youtube_screenshots.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 5

This tool:
1. Downloads the YouTube video
2. Extracts screenshots at specified intervals
3. Names images with video title prefix
4. Compares EACH image with ALL others to find duplicates
5. Removes all duplicates, keeping only the first occurrence
6. Creates a PDF with all unique images
7. Verifies that all remaining images are 100% unique
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
import hashlib
from PIL import Image
import numpy as np

def sanitize_filename(filename, max_length=100):
    """Remove invalid characters from filename"""
    # Remove invalid characters for Windows/Linux/Mac
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    # Replace spaces with underscores for cleaner filenames
    filename = filename.replace(' ', '_')
    # Limit length to avoid filesystem issues
    if len(filename) > max_length:
        filename = filename[:max_length]
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

def extract_screenshots(video_path, output_dir, interval, title_prefix):
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
        screenshot_files = []
        
        while current_time <= duration:
            # Format time for filename with title prefix
            time_str = f"{int(current_time):04d}s"
            output_file = os.path.join(output_dir, f"{title_prefix}_{time_str}.jpg")
            
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
            screenshot_files.append(output_file)
            print(f"  Screenshot at {current_time}s saved as {title_prefix}_{time_str}.jpg")
            
            current_time += interval
        
        return screenshots_taken, screenshot_files
        
    except subprocess.CalledProcessError as e:
        print(f"Error extracting screenshots: {e}")
        return 0, []
    except ValueError as e:
        print(f"Error parsing video duration: {e}")
        return 0, []

def get_image_hash(image_path):
    """Calculate SHA-256 hash of an image for exact comparison"""
    try:
        with open(image_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        print(f"Error hashing image {image_path}: {e}")
        return None

def are_images_identical(img1_path, img2_path):
    """Check if two images are 100% identical using multiple methods"""
    try:
        # Method 1: Quick file hash comparison
        hash1 = get_image_hash(img1_path)
        hash2 = get_image_hash(img2_path)
        
        if hash1 and hash2 and hash1 == hash2:
            return True
        
        # Method 2: Pixel-by-pixel comparison using PIL/numpy
        # This catches cases where files might be different but images are identical
        img1 = Image.open(img1_path)
        img2 = Image.open(img2_path)
        
        # Convert to RGB if necessary (handles different modes)
        if img1.mode != 'RGB':
            img1 = img1.convert('RGB')
        if img2.mode != 'RGB':
            img2 = img2.convert('RGB')
        
        # Check dimensions first
        if img1.size != img2.size:
            return False
        
        # Convert to numpy arrays and compare
        arr1 = np.array(img1)
        arr2 = np.array(img2)
        
        # Check if arrays are exactly equal
        return np.array_equal(arr1, arr2)
        
    except Exception as e:
        print(f"Error comparing images {img1_path} and {img2_path}: {e}")
        return False

def remove_all_duplicate_screenshots(screenshot_files):
    """Remove ALL duplicate screenshots by comparing each image with all others"""
    if len(screenshot_files) <= 1:
        return 0
    
    print("\nScanning for ALL duplicate screenshots (comparing each image with all others)...")
    print(f"Total images to process: {len(screenshot_files)}")
    
    duplicates_removed = 0
    files_to_remove = set()  # Use set to avoid duplicate entries
    processed_hashes = {}  # Store hash -> first occurrence file path
    
    # Process each image
    for i, current_file in enumerate(screenshot_files):
        # Skip if already marked for removal
        if current_file in files_to_remove:
            continue
            
        # Check if file exists
        if not os.path.exists(current_file):
            continue
        
        # Show progress for large sets
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  Processing image {i + 1}/{len(screenshot_files)}...")
        
        # Get hash of current image
        current_hash = get_image_hash(current_file)
        if not current_hash:
            continue
        
        # Check if we've seen this image before
        if current_hash in processed_hashes:
            # This is a duplicate of an earlier image
            original_file = processed_hashes[current_hash]
            files_to_remove.add(current_file)
            print(f"    Found duplicate: {os.path.basename(current_file)} is duplicate of {os.path.basename(original_file)}")
        else:
            # This is the first occurrence of this image
            processed_hashes[current_hash] = current_file
            
            # Now check all remaining images for duplicates of this one
            for j in range(i + 1, len(screenshot_files)):
                compare_file = screenshot_files[j]
                
                # Skip if already marked for removal
                if compare_file in files_to_remove:
                    continue
                
                # Check if file exists
                if not os.path.exists(compare_file):
                    continue
                
                # Compare images
                if are_images_identical(current_file, compare_file):
                    files_to_remove.add(compare_file)
                    print(f"    Found duplicate: {os.path.basename(compare_file)} matches {os.path.basename(current_file)}")
    
    # Remove all duplicate files
    if len(files_to_remove) > 0:
        print(f"\nRemoving {len(files_to_remove)} duplicate images...")
        for file_path in files_to_remove:
            try:
                os.remove(file_path)
                duplicates_removed += 1
                print(f"  Removed: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"  Error removing {file_path}: {e}")
    
    return duplicates_removed

def create_pdf_from_images(images_dir, pdf_path, video_title):
    """Create a PDF from all images in the directory"""
    try:
        print(f"\nCreating PDF from images...")
        
        # Get all jpg files in the directory, sorted by name
        image_files = sorted([f for f in Path(images_dir).glob('*.jpg')])
        
        if not image_files:
            print("  No images found to create PDF")
            return False
        
        print(f"  Found {len(image_files)} images to include in PDF")
        
        # Open all images
        images = []
        for img_path in image_files:
            try:
                img = Image.open(img_path)
                # Convert to RGB if necessary (PDF doesn't support all modes)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                images.append(img)
            except Exception as e:
                print(f"  Warning: Could not open {img_path}: {e}")
        
        if not images:
            print("  Error: No valid images to create PDF")
            return False
        
        # Save as PDF
        print(f"  Saving PDF as: {os.path.basename(pdf_path)}")
        
        # First image is saved with all others appended
        images[0].save(
            pdf_path,
            "PDF",
            resolution=100.0,
            save_all=True,
            append_images=images[1:] if len(images) > 1 else []
        )
        
        # Get file size
        file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # Convert to MB
        print(f"  ✓ PDF created successfully!")
        print(f"    - Title: {video_title}")
        print(f"    - Pages: {len(images)}")
        print(f"    - Size: {file_size:.2f} MB")
        print(f"    - Location: {pdf_path}")
        
        return True
        
    except Exception as e:
        print(f"  Error creating PDF: {e}")
        return False

def verify_all_unique(images_dir):
    """Final verification that all remaining images are unique"""
    print("\nFinal verification - confirming all remaining images are unique...")
    
    # Get all jpg files in the directory
    image_files = sorted([str(f) for f in Path(images_dir).glob('*.jpg')])
    
    if len(image_files) <= 1:
        print("  ✓ Only one or no images present - uniqueness guaranteed!")
        return True
    
    print(f"  Verifying {len(image_files)} images...")
    
    # Store hashes of all images
    image_hashes = {}
    duplicates_found = []
    
    for img_path in image_files:
        img_hash = get_image_hash(img_path)
        if img_hash:
            if img_hash in image_hashes:
                # Found a duplicate (this should not happen after our removal process)
                duplicates_found.append((image_hashes[img_hash], img_path))
                print(f"  ✗ ERROR: Found duplicate pair: {os.path.basename(image_hashes[img_hash])} == {os.path.basename(img_path)}")
            else:
                image_hashes[img_hash] = img_path
    
    if not duplicates_found:
        print(f"  ✓ SUCCESS: All {len(image_files)} images are 100% unique!")
        print("  ✓ No duplicates exist in the entire image set!")
        return True
    else:
        print(f"  ✗ ERROR: Found {len(duplicates_found)} duplicate pairs that were missed")
        print("  This is unexpected. Please report this issue.")
        return False

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
    
    # Check for Python packages
    try:
        import PIL
        import numpy
    except ImportError as e:
        print("\nError: Missing required Python packages.")
        print("Please install: pip install Pillow numpy")
        return False
    
    if missing:
        print("Error: Missing required dependencies:")
        for tool in missing:
            print(f"  - {tool}")
        print("\nInstallation instructions:")
        print("  Ubuntu/Debian: sudo apt-get install ffmpeg && pip install yt-dlp Pillow numpy")
        print("  macOS: brew install ffmpeg && pip install yt-dlp Pillow numpy")
        print("  Windows: Download ffmpeg from ffmpeg.org and install with: pip install yt-dlp Pillow numpy")
        return False
    return True

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Extract screenshots from YouTube videos with complete duplicate removal and PDF generation'
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
    parser.add_argument(
        '--no-duplicate-removal',
        action='store_true',
        help='Disable automatic duplicate removal'
    )
    parser.add_argument(
        '--no-pdf',
        action='store_true',
        help='Skip PDF generation'
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
    
    # Sanitize title for folder name and file prefix
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
        
        # Extract screenshots with title prefix
        print(f"\nExtracting screenshots to: {images_dir}")
        screenshot_count, screenshot_files = extract_screenshots(
            video_path, 
            images_dir, 
            args.interval,
            safe_title  # Pass title as prefix
        )
        
        if screenshot_count > 0:
            print(f"\nInitial extraction: {screenshot_count} screenshots saved")
            
            # Remove duplicates unless disabled
            if not args.no_duplicate_removal:
                duplicates_removed = remove_all_duplicate_screenshots(screenshot_files)
                
                if duplicates_removed > 0:
                    print(f"\n✓ Successfully removed {duplicates_removed} duplicate screenshots")
                    print(f"Final count: {screenshot_count - duplicates_removed} unique screenshots")
                else:
                    print("\n✓ No duplicate screenshots found - all images are already unique!")
                
                # Final verification that all remaining images are unique
                all_unique = verify_all_unique(images_dir)
                if not all_unique:
                    print("\n⚠ Unexpected: Some duplicates may still exist.")
                    print("  Please report this issue if it occurs.")
            else:
                print("\nDuplicate removal was skipped (--no-duplicate-removal flag used)")
            
            # Create PDF from all remaining images
            if not args.no_pdf:
                pdf_path = video_dir / f"{safe_title}.pdf"
                pdf_created = create_pdf_from_images(images_dir, pdf_path, video_info['title'])
                if not pdf_created:
                    print("\n⚠ Warning: PDF creation failed")
            else:
                print("\nPDF generation was skipped (--no-pdf flag used)")
            
            print(f"\nSuccess! Output saved to:")
            print(f"  📁 Directory: {video_dir.absolute()}")
            print(f"  🖼️ Images: {images_dir.absolute()}")
            if not args.no_pdf and pdf_created:
                print(f"  📄 PDF: {pdf_path.absolute()}")
            
            # List remaining files
            remaining_files = sorted([f for f in images_dir.glob('*.jpg')])
            if remaining_files:
                print(f"\nFinal screenshots: {len(remaining_files)} unique images")
                if len(remaining_files) <= 10:
                    for f in remaining_files:
                        print(f"  - {f.name}")
                else:
                    # Show first 5 and last 5
                    for f in remaining_files[:5]:
                        print(f"  - {f.name}")
                    print(f"  ... ({len(remaining_files) - 10} more files)")
                    for f in remaining_files[-5:]:
                        print(f"  - {f.name}")
            
            # Optionally keep the video
            if args.keep_video:
                final_video_path = video_dir / f"{safe_title}.mp4"
                shutil.copy2(video_path, final_video_path)
                print(f"\n📹 Video saved to: {final_video_path.absolute()}")
        else:
            print("\nError: No screenshots were extracted")
            sys.exit(1)
    
    print("\n✅ Done!")

if __name__ == "__main__":
    main()
