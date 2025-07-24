#!/bin/bash

# Subtitle Translator Setup Script
# This script helps set up the Subtitle Translator application

echo "🎬 Subtitle Translator Setup"
echo "=============================="

# Check Python version
echo "Checking Python version..."
python3 --version || {
    echo "❌ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
}

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt || {
    echo "❌ Failed to install Python dependencies."
    echo "Try: pip3 install -r requirements.txt"
    exit 1
}

echo "✓ Python dependencies installed"

# Check for ffmpeg
echo "Checking for ffmpeg..."
if command -v ffmpeg >/dev/null 2>&1; then
    echo "✓ ffmpeg is available"
    ffmpeg -version | head -1
else
    echo "⚠️  ffmpeg not found"
    echo "To extract subtitles from video files, install ffmpeg:"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  macOS: brew install ffmpeg"
    echo "  Windows: Download from https://ffmpeg.org/"
fi

# Run basic tests
echo ""
echo "Running basic tests..."
python3 test_basic.py || {
    echo "❌ Basic tests failed. Please check the error messages above."
    exit 1
}

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Get an OpenAI API key from https://platform.openai.com/api-keys"
echo "2. Set your API key: export OPENAI_API_KEY='your-key-here'"
echo "3. Run the application: python3 subtitle_translator.py"
echo ""
echo "For headless usage, see example.py"
echo "For documentation, see README.md"