#!/bin/bash

# YouTube Screenshot Capture Tool - Bash Wrapper
# Usage: ./ytscreenshot.sh <youtube_url> <interval_seconds>

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    echo -e "${1}${2}${NC}"
}

# Check if correct number of arguments provided
if [ $# -ne 2 ]; then
    print_color "$RED" "Error: Invalid number of arguments"
    echo "Usage: $0 <youtube_url> <interval_seconds>"
    echo "Example: $0 \"https://www.youtube.com/watch?v=dQw4w9WgXcQ\" 5"
    exit 1
fi

YOUTUBE_URL="$1"
INTERVAL="$2"

# Validate interval is a number
if ! [[ "$INTERVAL" =~ ^[0-9]+$ ]]; then
    print_color "$RED" "Error: Interval must be a positive integer"
    exit 1
fi

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    print_color "$RED" "Error: Python 3 is not installed"
    echo "Please install Python 3 to continue"
    exit 1
fi

# Check and install dependencies
print_color "$YELLOW" "Checking dependencies..."

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check for yt-dlp
if ! command_exists yt-dlp; then
    print_color "$YELLOW" "Installing yt-dlp..."
    pip3 install --user yt-dlp
    if [ $? -ne 0 ]; then
        print_color "$RED" "Failed to install yt-dlp"
        echo "Please install manually: pip3 install yt-dlp"
        exit 1
    fi
fi

# Check for ffmpeg
if ! command_exists ffmpeg; then
    print_color "$RED" "Error: ffmpeg is not installed"
    echo ""
    echo "Please install ffmpeg:"
    echo "  Ubuntu/Debian: sudo apt-get install ffmpeg"
    echo "  macOS: brew install ffmpeg"
    echo "  Fedora: sudo dnf install ffmpeg"
    echo "  Arch: sudo pacman -S ffmpeg"
    exit 1
fi

# Create Python script if it doesn't exist
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/youtube_screenshots.py"

if [ ! -f "$PYTHON_SCRIPT" ]; then
    print_color "$YELLOW" "Python script not found. Please ensure youtube_screenshots.py is in the same directory."
    exit 1
fi

# Run the Python script
print_color "$GREEN" "Starting screenshot capture..."
echo ""

python3 "$PYTHON_SCRIPT" "$YOUTUBE_URL" "$INTERVAL"

# Check if the script ran successfully
if [ $? -eq 0 ]; then
    print_color "$GREEN" "✓ Screenshot capture completed successfully!"
else
    print_color "$RED" "✗ Screenshot capture failed"
    exit 1
fi