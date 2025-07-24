#!/usr/bin/env python3
"""
Example script demonstrating how to use the Subtitle Translator components
without the GUI interface.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path so we can import our modules
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

def example_basic_usage():
    """
    Example of basic subtitle translation usage
    """
    print("🎬 Subtitle Translator - Basic Usage Example")
    print("=" * 50)
    
    # This example shows how you would use the components programmatically
    # Note: You need a valid OpenAI API key and subtitle files to actually run this
    
    try:
        from translator import GPTTranslator
        from subtitle_processor import SubtitleProcessor
        from jellyfin_renamer import JellyfinRenamer
        
        print("✓ All core modules imported successfully")
        
        # Example 1: Initialize translator
        print("\n1. Initialize translator:")
        print("   translator = GPTTranslator()")
        print("   # Requires OPENAI_API_KEY environment variable")
        
        # Example 2: Process a subtitle file
        print("\n2. Process subtitle file:")
        print("   processor = SubtitleProcessor(")
        print("       file_path='movie.srt',")
        print("       translator=translator,")
        print("       target_language='Spanish',")
        print("       progress_callback=lambda p: print(f'Progress: {p}%'),")
        print("       status_callback=lambda s: print(f'Status: {s}')")
        print("   )")
        print("   processor.translate()")
        
        # Example 3: Rename for Jellyfin
        print("\n3. Rename files for Jellyfin:")
        print("   renamer = JellyfinRenamer()")
        print("   flags = {'default': True, 'forced': False}")
        print("   renamed, deleted, errors = renamer.rename_subtitles(")
        print("       folder_path='/path/to/movies',")
        print("       flags=flags,")
        print("       cleanup_originals=True")
        print("   )")
        
        # Example 4: Check for video subtitle extraction
        print("\n4. Extract subtitles from video (requires ffmpeg):")
        try:
            from subtitle_extractor import SubtitleExtractor
            print("   extractor = SubtitleExtractor()")
            print("   streams = extractor.list_subtitles('movie.mkv')")
            print("   subtitle_file = extractor.extract_subtitle('movie.mkv', stream_index=0)")
        except Exception as e:
            print(f"   ⚠️  SubtitleExtractor not available: {str(e)[:50]}...")
            print("   Install ffmpeg to enable video subtitle extraction")
        
        print("\n🎯 For GUI interface, run: python subtitle_translator.py")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure to install requirements: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error: {e}")

def check_environment():
    """
    Check if the environment is properly set up
    """
    print("\n🔍 Environment Check")
    print("=" * 30)
    
    # Check Python version
    print(f"Python version: {sys.version.split()[0]}")
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print("✓ OPENAI_API_KEY environment variable is set")
    else:
        print("⚠️  OPENAI_API_KEY environment variable not set")
        print("   Set it with: export OPENAI_API_KEY='your-api-key-here'")
    
    # Check dependencies
    dependencies = [
        ('openai', 'OpenAI API client'),
        ('pysrt', 'SRT subtitle file processing'),
    ]
    for dep, desc in dependencies:
        try:
            __import__(dep)
            print(f"✓ {dep} is installed ({desc})")
        except ImportError:
            print(f"❌ {dep} is not installed ({desc})")
    
    # Check GUI dependencies (requires display)
    try:
        import tkinter
        import customtkinter
        print("✓ GUI dependencies (tkinter, customtkinter) are available")
    except ImportError as e:
        print(f"⚠️  GUI dependencies not available: {e}")
        print("   This is normal in headless environments")
        print("   GUI will work on desktop systems with display")
    
    # Check for ffmpeg
    import subprocess
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      capture_output=True, check=True)
        print("✓ ffmpeg is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  ffmpeg is not available")
        print("   Install it to enable video subtitle extraction")

if __name__ == "__main__":
    example_basic_usage()
    check_environment()
    
    print("\n" + "=" * 50)
    print("📖 For complete documentation, see README.md")
    print("🚀 To start the GUI application: python subtitle_translator.py")