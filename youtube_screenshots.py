#!/usr/bin/env python3
"""
Enhanced YouTube Video Screenshot Capture Tool with HD PDF (Images Only)
Usage: python youtube_screenshots.py <youtube_url> <interval_seconds>
Example: python youtube_screenshots.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 5

Features:
1. High-quality screenshot extraction (PNG format option)
2. HD PDF generation with configurable DPI (images only)
3. Automatic transcript/subtitle download (saved as separate text file)
4. Complete duplicate removal
5. PDF contains only high-quality screenshots
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
from datetime import timedelta
import textwrap

def sanitize_filename(filename, max_length=100):
    """Remove invalid characters from filename"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    filename = filename.strip('. ')
    filename = filename.replace(' ', '_')
    if len(filename) > max_length:
        filename = filename[:max_length]
    return filename

def format_time(seconds):
    """Convert seconds to readable format"""
    return str(timedelta(seconds=int(seconds)))

def get_video_info(url):
    """Get video title, duration, and available subtitles using yt-dlp"""
    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-playlist',
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)
        
        # Check for available subtitles/captions
        subtitles_available = bool(info.get('subtitles', {})) or bool(info.get('automatic_captions', {}))
        
        return {
            'title': info.get('title', 'untitled'),
            'duration': info.get('duration', 0),
            'description': info.get('description', ''),
            'uploader': info.get('uploader', 'Unknown'),
            'upload_date': info.get('upload_date', ''),
            'view_count': info.get('view_count', 0),
            'subtitles_available': subtitles_available
        }
    except subprocess.CalledProcessError as e:
        print(f"Error getting video info: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing video info: {e}")
        return None

def download_video_and_transcript(url, video_path, transcript_path):
    """Download YouTube video and transcript/subtitles using yt-dlp"""
    try:
        # First, try to download with subtitles
        cmd = [
            'yt-dlp',
            '-f', 'best[ext=mp4]/best',
            '--no-playlist',
            '-o', video_path,
            '--write-auto-subs',  # Download automatic captions if available
            '--write-subs',       # Download manual subtitles if available
            '--sub-lang', 'en',   # Prefer English subtitles
            '--convert-subs', 'srt',  # Convert to SRT format
            url
        ]
        
        print("Downloading video and attempting to fetch transcript...")
        subprocess.run(cmd, check=True)
        
        # Check if subtitle file was created
        video_dir = os.path.dirname(video_path)
        video_base = os.path.splitext(os.path.basename(video_path))[0]
        
        # Look for subtitle files
        subtitle_patterns = [
            f"{video_base}.en.srt",
            f"{video_base}.en.vtt",
            f"{video_base}.srt",
            f"{video_base}.vtt"
        ]
        
        subtitle_file = None
        for pattern in subtitle_patterns:
            potential_file = os.path.join(video_dir, pattern)
            if os.path.exists(potential_file):
                subtitle_file = potential_file
                break
        
        # If subtitle file exists, convert to plain text
        if subtitle_file:
            print(f"  ✓ Transcript found: {os.path.basename(subtitle_file)}")
            convert_srt_to_text(subtitle_file, transcript_path)
            return True, True  # Video downloaded, transcript found
        else:
            print("  ⚠ No transcript/captions available for this video")
            return True, False  # Video downloaded, no transcript
            
    except subprocess.CalledProcessError as e:
        print(f"Error downloading video: {e}")
        return False, False

def convert_srt_to_text(srt_file, text_file):
    """Convert SRT subtitle file to plain text transcript"""
    try:
        with open(srt_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        transcript_lines = []
        current_text = []
        
        for line in lines:
            line = line.strip()
            # Skip subtitle numbers and timestamps
            if line and not line.isdigit() and '-->' not in line:
                # Remove HTML tags if present
                line = re.sub('<[^<]+?>', '', line)
                current_text.append(line)
            elif not line and current_text:
                # Empty line indicates end of subtitle block
                transcript_lines.append(' '.join(current_text))
                current_text = []
        
        # Add any remaining text
        if current_text:
            transcript_lines.append(' '.join(current_text))
        
        # Write to text file
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write("VIDEO TRANSCRIPT\n")
            f.write("=" * 50 + "\n\n")
            
            # Join lines and format paragraphs
            full_text = ' '.join(transcript_lines)
            # Remove duplicate spaces
            full_text = re.sub(r'\s+', ' ', full_text)
            
            # Wrap text for better readability
            wrapped_text = textwrap.fill(full_text, width=80)
            f.write(wrapped_text)
        
        print(f"  ✓ Transcript saved to: {os.path.basename(text_file)}")
        return True
        
    except Exception as e:
        print(f"Error converting transcript: {e}")
        return False

def extract_high_quality_screenshots(video_path, output_dir, interval, title_prefix, quality='high'):
    """Extract high-quality screenshots from video at specified intervals"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        # Get video duration
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
        print(f"Taking high-quality screenshots every {interval} seconds...")
        
        screenshots_taken = 0
        current_time = 0
        screenshot_files = []
        
        while current_time <= duration:
            time_str = f"{int(current_time):04d}s"
            
            # Use PNG for lossless quality or high-quality JPEG
            if quality == 'highest':
                output_file = os.path.join(output_dir, f"{title_prefix}_{time_str}.png")
                # Extract as PNG for maximum quality
                cmd = [
                    'ffmpeg',
                    '-ss', str(current_time),
                    '-i', video_path,
                    '-vframes', '1',
                    '-vf', 'scale=iw:ih',  # Keep original resolution
                    '-y',
                    output_file
                ]
            else:
                output_file = os.path.join(output_dir, f"{title_prefix}_{time_str}.jpg")
                # Extract as high-quality JPEG
                cmd = [
                    'ffmpeg',
                    '-ss', str(current_time),
                    '-i', video_path,
                    '-vframes', '1',
                    '-q:v', '1',  # Highest JPEG quality (1 is best, 31 is worst)
                    '-vf', 'scale=iw:ih',  # Keep original resolution
                    '-y',
                    output_file
                ]
            
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            
            screenshots_taken += 1
            screenshot_files.append(output_file)
            
            # Show progress
            progress = (current_time / duration) * 100
            print(f"  [{progress:5.1f}%] Screenshot at {format_time(current_time)} saved")
            
            current_time += interval
        
        return screenshots_taken, screenshot_files
        
    except subprocess.CalledProcessError as e:
        print(f"Error extracting screenshots: {e}")
        return 0, []
    except ValueError as e:
        print(f"Error parsing video duration: {e}")
        return 0, []

def get_image_hash(image_path):
    """Calculate hash of an image for comparison"""
    try:
        with open(image_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        print(f"Error hashing image {image_path}: {e}")
        return None

def are_images_identical(img1_path, img2_path):
    """Check if two images are identical"""
    try:
        hash1 = get_image_hash(img1_path)
        hash2 = get_image_hash(img2_path)
        
        if hash1 and hash2 and hash1 == hash2:
            return True
        
        img1 = Image.open(img1_path)
        img2 = Image.open(img2_path)
        
        if img1.mode != 'RGB':
            img1 = img1.convert('RGB')
        if img2.mode != 'RGB':
            img2 = img2.convert('RGB')
        
        if img1.size != img2.size:
            return False
        
        arr1 = np.array(img1)
        arr2 = np.array(img2)
        
        return np.array_equal(arr1, arr2)
        
    except Exception as e:
        print(f"Error comparing images: {e}")
        return False

def remove_duplicate_screenshots(screenshot_files):
    """Remove duplicate screenshots"""
    if len(screenshot_files) <= 1:
        return 0
    
    print("\nRemoving duplicate screenshots...")
    
    duplicates_removed = 0
    files_to_remove = set()
    processed_hashes = {}
    
    for i, current_file in enumerate(screenshot_files):
        if current_file in files_to_remove:
            continue
        
        if not os.path.exists(current_file):
            continue
        
        current_hash = get_image_hash(current_file)
        if not current_hash:
            continue
        
        if current_hash in processed_hashes:
            files_to_remove.add(current_file)
        else:
            processed_hashes[current_hash] = current_file
            
            for j in range(i + 1, len(screenshot_files)):
                compare_file = screenshot_files[j]
                
                if compare_file in files_to_remove or not os.path.exists(compare_file):
                    continue
                
                if are_images_identical(current_file, compare_file):
                    files_to_remove.add(compare_file)
    
    if len(files_to_remove) > 0:
        print(f"  Removing {len(files_to_remove)} duplicate images...")
        for file_path in files_to_remove:
            try:
                os.remove(file_path)
                duplicates_removed += 1
            except Exception as e:
                print(f"  Error removing {file_path}: {e}")
    
    return duplicates_removed

def create_hd_pdf_images_only(images_dir, pdf_path, video_info, dpi=300):
    """Create high-quality PDF from images only (no transcript in PDF)"""
    try:
        print(f"\nCreating HD PDF with images only (DPI: {dpi})...")
        
        # Get all image files
        image_files = sorted(list(Path(images_dir).glob('*.jpg')) + list(Path(images_dir).glob('*.png')))
        
        if not image_files:
            print("  No images found to create PDF")
            return False
        
        print(f"  Found {len(image_files)} images to include in PDF")
        
        # Prepare images for PDF (no title page, just screenshots)
        pdf_images = []
        
        # Add all screenshots
        print("  Processing screenshots for HD quality...")
        for i, img_path in enumerate(image_files):
            try:
                img = Image.open(img_path)
                
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Optional: Resize very large images to reasonable PDF size while maintaining quality
                max_dimension = 3000  # Maximum width or height
                if img.width > max_dimension or img.height > max_dimension:
                    img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                
                pdf_images.append(img)
                
                if (i + 1) % 10 == 0:
                    print(f"    Processed {i + 1}/{len(image_files)} images...")
                    
            except Exception as e:
                print(f"  Warning: Could not process {img_path}: {e}")
        
        # Save as high-quality PDF with screenshots only
        print(f"  Saving HD PDF (screenshots only)...")
        
        if pdf_images:
            # Save with high DPI for better quality
            pdf_images[0].save(
                pdf_path,
                "PDF",
                resolution=dpi,  # Higher DPI for better quality
                quality=95,  # High quality setting
                optimize=True,  # Optimize file size
                save_all=True,
                append_images=pdf_images[1:] if len(pdf_images) > 1 else []
            )
            
            # Get file size
            file_size = os.path.getsize(pdf_path) / (1024 * 1024)
            
            print(f"  ✓ HD PDF created successfully!")
            print(f"    - Screenshots: {len(image_files)}")
            print(f"    - DPI: {dpi}")
            print(f"    - Size: {file_size:.2f} MB")
            print(f"    - Location: {pdf_path}")
            
            return True
        
    except Exception as e:
        print(f"  Error creating PDF: {e}")
        return False



def verify_all_unique(images_dir):
    """Final verification that all remaining images are unique"""
    print("\nVerifying all images are unique...")
    
    # Get all image files in the directory
    image_files = sorted([str(f) for f in Path(images_dir).glob('*.jpg')] + 
                         [str(f) for f in Path(images_dir).glob('*.png')])
    
    if len(image_files) <= 1:
        print("  ✓ Only one or no images present - uniqueness guaranteed!")
        return True
    
    print(f"  Checking {len(image_files)} images...")
    
    # Store hashes of all images
    image_hashes = {}
    duplicates_found = []
    
    for img_path in image_files:
        img_hash = get_image_hash(img_path)
        if img_hash:
            if img_hash in image_hashes:
                # Found a duplicate
                duplicates_found.append((image_hashes[img_hash], img_path))
                print(f"  ✗ Found duplicate: {os.path.basename(image_hashes[img_hash])} == {os.path.basename(img_path)}")
            else:
                image_hashes[img_hash] = img_path
    
    if not duplicates_found:
        print(f"  ✓ All {len(image_files)} images are unique!")
        return True
    else:
        print(f"  ✗ Found {len(duplicates_found)} duplicate pairs")
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
    
    try:
        import PIL
        import numpy
    except ImportError:
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
    parser = argparse.ArgumentParser(
        description='Extract HD screenshots from YouTube videos with image-only PDF and separate transcript'
    )
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('interval', type=int, help='Interval in seconds between screenshots')
    parser.add_argument('--keep-video', action='store_true', help='Keep the downloaded video file')
    parser.add_argument('--output-dir', default='.', help='Base directory for output')
    parser.add_argument('--no-duplicate-removal', action='store_true', help='Disable duplicate removal')
    parser.add_argument('--no-pdf', action='store_true', help='Skip PDF generation')
    parser.add_argument('--no-transcript', action='store_true', help='Skip transcript download')
    parser.add_argument('--quality', choices=['high', 'highest'], default='high', 
                       help='Screenshot quality (high=JPEG, highest=PNG)')
    parser.add_argument('--pdf-dpi', type=int, default=300, 
                       help='PDF DPI resolution (default: 300, higher=better quality)')
    
    args = parser.parse_args()
    
    if args.interval <= 0:
        print("Error: Interval must be greater than 0")
        sys.exit(1)
    
    if not check_dependencies():
        sys.exit(1)
    
    # Get video information
    print(f"Fetching video information...")
    video_info = get_video_info(args.url)
    if not video_info:
        print("Error: Could not fetch video information")
        sys.exit(1)
    
    safe_title = sanitize_filename(video_info['title'])
    
    print(f"\n{'='*60}")
    print(f"Video: {video_info['title']}")
    print(f"Duration: {format_time(video_info['duration'])}")
    print(f"Uploader: {video_info['uploader']}")
    if video_info.get('view_count'):
        print(f"Views: {video_info['view_count']:,}")
    print(f"Subtitles available: {'Yes' if video_info['subtitles_available'] else 'No'}")
    print(f"{'='*60}\n")
    
    # Create output directories
    base_dir = Path(args.output_dir)
    video_dir = base_dir / safe_title
    images_dir = video_dir / 'images'
    images_dir.mkdir(parents=True, exist_ok=True)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = os.path.join(temp_dir, 'video.mp4')
        transcript_path = video_dir / f"{safe_title}_transcript.txt"
        
        # Download video and transcript
        video_success, transcript_success = download_video_and_transcript(
            args.url, 
            video_path, 
            transcript_path if not args.no_transcript else None
        )
        
        if not video_success:
            print("Error: Failed to download video")
            sys.exit(1)
        
        print(f"\n✓ Video downloaded successfully!")
        
        if not args.no_transcript and transcript_success:
            print(f"✓ Transcript saved as separate text file!")
        elif not args.no_transcript:
            print("⚠ Transcript not available for this video")
        
        # Extract high-quality screenshots
        print(f"\nExtracting {args.quality} quality screenshots...")
        screenshot_count, screenshot_files = extract_high_quality_screenshots(
            video_path, 
            images_dir, 
            args.interval,
            safe_title,
            args.quality
        )
        
        if screenshot_count > 0:
            print(f"\n✓ Extracted {screenshot_count} screenshots")
            
            # Remove duplicates
            if not args.no_duplicate_removal:
                duplicates_removed = remove_duplicate_screenshots(screenshot_files)
                if duplicates_removed > 0:
                    print(f"✓ Removed {duplicates_removed} duplicate screenshots")
                    print(f"  Final count: {screenshot_count - duplicates_removed} unique screenshots")
                
                # Verify all remaining images are unique
                verify_all_unique(images_dir)
            
            # Create HD PDF with images only
            if not args.no_pdf:
                pdf_path = video_dir / f"{safe_title}_HD.pdf"
                pdf_created = create_hd_pdf_images_only(
                    images_dir, 
                    pdf_path, 
                    video_info,
                    args.pdf_dpi
                )
                
                if not pdf_created:
                    print("\n⚠ Warning: PDF creation failed")
            
            # Keep video if requested
            if args.keep_video:
                final_video_path = video_dir / f"{safe_title}.mp4"
                shutil.copy2(video_path, final_video_path)
                print(f"\n📹 Video saved to: {final_video_path.absolute()}")
            
            # Final summary
            print(f"\n{'='*60}")
            print(f"✅ COMPLETED SUCCESSFULLY!")
            print(f"{'='*60}")
            print(f"📁 Output directory: {video_dir.absolute()}")
            print(f"🖼️ Screenshots: {images_dir.absolute()}")
            if not args.no_pdf and pdf_created:
                print(f"📄 HD PDF (images only): {pdf_path.absolute()}")
            if transcript_success and not args.no_transcript:
                print(f"📝 Transcript (text file): {transcript_path.absolute()}")
            
            # List some of the final files
            remaining_files = sorted(list(Path(images_dir).glob('*.jpg')) + 
                                    list(Path(images_dir).glob('*.png')))
            if remaining_files:
                print(f"\nTotal unique screenshots: {len(remaining_files)}")
                if len(remaining_files) <= 5:
                    print("Files:")
                    for f in remaining_files:
                        print(f"  - {f.name}")
                else:
                    print("Sample files:")
                    for f in remaining_files[:3]:
                        print(f"  - {f.name}")
                    print(f"  ... and {len(remaining_files) - 3} more")
            
            print(f"{'='*60}\n")
            
        else:
            print("\nError: No screenshots were extracted")
            sys.exit(1)

if __name__ == "__main__":
    main()
