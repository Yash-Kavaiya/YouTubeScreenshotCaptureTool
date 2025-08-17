# YouTube Screenshot Capture Tool - Setup Guide

## Features
- Downloads YouTube videos using yt-dlp
- Extracts screenshots at specified intervals
- Creates organized folder structure with video title
- Saves screenshots with timestamp names (e.g., 005s.jpg, 010s.jpg)
- Optionally keeps the downloaded video

## Prerequisites

### 1. Install Python 3
- **Ubuntu/Debian**: `sudo apt-get install python3 python3-pip`
- **macOS**: `brew install python3`
- **Windows**: Download from [python.org](https://python.org)

### 2. Install FFmpeg
- **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
- **Fedora**: `sudo dnf install ffmpeg`
- **Arch**: `sudo pacman -S ffmpeg`

### 3. Install yt-dlp
```bash
pip3 install yt-dlp
```

## Installation

### Option 1: Quick Setup (Linux/macOS)
```bash
# Create a directory for the tool
mkdir ~/youtube-screenshots
cd ~/youtube-screenshots

# Save the Python script as youtube_screenshots.py
# Save the bash script as ytscreenshot.sh

# Make scripts executable
chmod +x youtube_screenshots.py
chmod +x ytscreenshot.sh

# Add to PATH (optional)
echo 'export PATH="$HOME/youtube-screenshots:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Option 2: Python-only Setup (All platforms)
```bash
# Install yt-dlp
pip3 install yt-dlp

# Save the Python script as youtube_screenshots.py
# Make it executable (Linux/macOS)
chmod +x youtube_screenshots.py
```

## Usage

### Basic Usage
```bash
# Using Python directly
python3 youtube_screenshots.py "https://www.youtube.com/watch?v=VIDEO_ID" 5

# Using bash wrapper (Linux/macOS)
./ytscreenshot.sh "https://www.youtube.com/watch?v=VIDEO_ID" 5
```

### Advanced Options
```bash
# Keep the downloaded video file
python3 youtube_screenshots.py "URL" 5 --keep-video

# Specify output directory
python3 youtube_screenshots.py "URL" 5 --output-dir /path/to/output

# Help
python3 youtube_screenshots.py --help
```

## Examples

### Example 1: Screenshot every 10 seconds
```bash
python3 youtube_screenshots.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 10
```
This will:
- Create folder: `./Rick Astley - Never Gonna Give You Up/`
- Create subfolder: `./Rick Astley - Never Gonna Give You Up/images/`
- Save screenshots: `000s.jpg`, `010s.jpg`, `020s.jpg`, etc.

### Example 2: Screenshot every 30 seconds and keep video
```bash
python3 youtube_screenshots.py "https://www.youtube.com/watch?v=VIDEO_ID" 30 --keep-video
```

## Output Structure
```
video_title/
├── images/
│   ├── 000s.jpg    # Screenshot at 0 seconds
│   ├── 005s.jpg    # Screenshot at 5 seconds
│   ├── 010s.jpg    # Screenshot at 10 seconds
│   └── ...
└── video_title.mp4  # (if --keep-video is used)
```

## Troubleshooting

### Common Issues

1. **"yt-dlp not found"**
   ```bash
   pip3 install --upgrade yt-dlp
   ```

2. **"ffmpeg not found"**
   - Install ffmpeg using your system's package manager

3. **"Permission denied"**
   ```bash
   chmod +x youtube_screenshots.py
   ```

4. **Age-restricted videos**
   - You may need to use cookies:
   ```bash
   yt-dlp --cookies-from-browser chrome "URL"
   ```

5. **Network issues**
   - Try using a VPN if videos are region-locked
   - Check your internet connection

## Requirements File (requirements.txt)
```
yt-dlp>=2023.1.6
```

Install with:
```bash
pip3 install -r requirements.txt
```

## Features Breakdown

- ✅ Downloads YouTube videos
- ✅ Extracts screenshots at custom intervals
- ✅ Creates organized folder structure
- ✅ Sanitizes filenames for all operating systems
- ✅ Handles long videos efficiently
- ✅ Progress indication
- ✅ Error handling and validation
- ✅ Cross-platform compatibility

## License
Free to use and modify for personal and commercial purposes.