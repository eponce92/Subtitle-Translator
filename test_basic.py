#!/usr/bin/env python3
"""
Simple test script to verify basic functionality
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

def test_imports():
    """Test that all core modules can be imported"""
    print("Testing module imports...")
    
    try:
        from translator import GPTTranslator
        print("✓ GPTTranslator imports successfully")
    except Exception as e:
        print(f"✗ GPTTranslator import failed: {e}")
        return False
    
    try:
        from subtitle_processor import SubtitleProcessor
        print("✓ SubtitleProcessor imports successfully")
    except Exception as e:
        print(f"✗ SubtitleProcessor import failed: {e}")
        return False
    
    try:
        from jellyfin_renamer import JellyfinRenamer
        print("✓ JellyfinRenamer imports successfully")
    except Exception as e:
        print(f"✗ JellyfinRenamer import failed: {e}")
        return False
    
    return True

def test_jellyfin_renamer():
    """Test JellyfinRenamer functionality"""
    print("\nTesting JellyfinRenamer...")
    
    try:
        from jellyfin_renamer import JellyfinRenamer
        renamer = JellyfinRenamer()
        
        # Test filename generation
        test_cases = [
            ("movie_stream_2_Spanish.srt", {"default": True}, "movie.es.default.srt"),
            ("show.S01E01.eng.srt", {"forced": False}, "show.S01E01.en.srt"),
            ("test.spa.srt", {}, "test.es.srt")
        ]
        
        for filename, flags, expected in test_cases:
            result = renamer._generate_jellyfin_name(filename, flags)
            if result == expected:
                print(f"✓ {filename} -> {result}")
            else:
                print(f"✗ {filename} -> {result} (expected {expected})")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ JellyfinRenamer test failed: {e}")
        return False

def test_subtitle_processor():
    """Test SubtitleProcessor initialization"""
    print("\nTesting SubtitleProcessor...")
    
    try:
        from subtitle_processor import SubtitleProcessor
        from translator import GPTTranslator
        
        # Test language code mapping
        processor = SubtitleProcessor(
            file_path="test.srt",
            translator=None,  # Don't need real translator for this test
            target_language="Spanish",
            progress_callback=None,
            status_callback=None
        )
        
        lang_code = processor._get_language_code("Spanish")
        if lang_code == "spa":
            print("✓ Language code mapping works")
        else:
            print(f"✗ Language code mapping failed: got {lang_code}, expected spa")
            return False
        
        # Test output path generation
        output_path = processor._create_subtitle_path("/path/to/movie.mkv")
        expected = "/path/to/movie.spa.srt"
        if output_path == expected:
            print("✓ Output path generation works")
        else:
            print(f"✗ Output path generation failed: got {output_path}, expected {expected}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ SubtitleProcessor test failed: {e}")
        return False

def main():
    print("🧪 Subtitle Translator - Basic Tests")
    print("=" * 40)
    
    all_passed = True
    
    # Run tests
    all_passed &= test_imports()
    all_passed &= test_jellyfin_renamer()
    all_passed &= test_subtitle_processor()
    
    print("\n" + "=" * 40)
    if all_passed:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    exit(main())