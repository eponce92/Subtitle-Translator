# Subtitle Translator

A powerful desktop application for translating video subtitles using OpenAI's GPT models. Extract embedded subtitles from video files, translate them to any language, and organize them for media servers like Jellyfin.

## ✨ Features

- **🌐 Multi-language Translation**: Translate subtitles to any language using OpenAI's GPT models
- **🎬 Video File Support**: Extract embedded subtitles from MP4, MKV, and AVI files
- **📁 Batch Processing**: Process single files or entire folders automatically
- **🎯 Auto-detection**: Automatically detect and select English subtitle streams
- **📺 Jellyfin Integration**: Rename files according to Jellyfin media server standards
- **⏱️ Time Synchronization**: Adjust subtitle timing with millisecond precision
- **🎨 Modern UI**: Dark theme interface with real-time progress tracking
- **💾 Settings Persistence**: Saves your preferences between sessions
- **🔄 Format Support**: Works with SRT subtitle files

## 🖥️ Screenshots

### Main Interface
The application features a clean, step-by-step interface that guides you through the translation process:

- **Step 1**: Choose between single file or batch processing
- **Step 2**: Select your video files or folder
- **Step 3**: Configure translation options and API key
- **Step 4**: Monitor translation progress in real-time
- **Step 5**: Organize files for Jellyfin (optional)

## 📋 Requirements

### System Requirements
- **Operating System**: Windows, macOS, or Linux with desktop environment
- **Python**: 3.8 or higher
- **Display**: GUI application requires a desktop environment or X11 forwarding
- **FFmpeg**: Required for extracting embedded subtitles from video files

### Python Dependencies
- `openai` - OpenAI API integration
- `pysrt` - SRT subtitle file processing
- `customtkinter` - Modern UI components
- `tkinter` - GUI framework (usually included with Python desktop installations)

### Note for Server/Headless Environments
This application includes a GUI interface that requires a desktop environment. For headless servers or environments without display capabilities, you can still use the core translation components programmatically (see `example.py`).

## 🚀 Installation

### Quick Setup (Recommended)

Run the automated setup script:

```bash
chmod +x setup.sh
./setup.sh
```

This script will:
- Check Python version
- Install Python dependencies
- Check for ffmpeg
- Run basic tests
- Provide next steps

### Manual Installation

### 1. Install Python Dependencies

```bash
pip install openai pysrt customtkinter
```

### 2. Install FFmpeg

**Windows:**
- Download from [FFmpeg website](https://ffmpeg.org/download.html)
- Add FFmpeg to your system PATH

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**CentOS/RHEL:**
```bash
sudo yum install ffmpeg
```

### 3. Get OpenAI API Key

1. Visit [OpenAI's website](https://platform.openai.com/api-keys)
2. Create an account and generate an API key
3. Keep your API key secure - you'll need it to run translations

### 4. Download the Application

```bash
git clone https://github.com/eponce92/Subtitle-Translator.git
cd Subtitle-Translator
```

## 🎯 Quick Start

### GUI Application

### 1. Launch the Application

```bash
python subtitle_translator.py
```

**Note**: Requires desktop environment. For headless environments, see Programmatic Usage below.

### 2. Basic Translation Workflow

1. **Enter your OpenAI API Key** in the configuration section
2. **Select Processing Mode**:
   - **Single File**: Choose specific video files
   - **Batch Process**: Select a folder to process all videos
3. **Browse and Select Files**: Use the browse button to select your content
4. **Configure Options**:
   - Set target language (e.g., "Spanish", "French", "German")
   - Choose to auto-select English subtitles
   - Optionally limit the number of subtitle blocks for testing
5. **Start Translation**: Click the "Start Translation" button
6. **Monitor Progress**: Watch real-time progress for each file

### 3. Example Usage

**Translating a Single Movie:**
```
1. Select "Single File" mode
2. Browse and select "movie.mkv"
3. Set target language to "Spanish"
4. The app will extract English subtitles and create "movie.spa.srt"
```

**Batch Processing a TV Show:**
```
1. Select "Batch Process Folder" mode
2. Browse to your TV show folder
3. Set target language to "French"
4. The app will process all video files and create French subtitles
```

### Programmatic Usage (For Headless Environments)

If you're running on a server or headless environment, you can use the core components directly:

```python
import os
from translator import GPTTranslator
from subtitle_processor import SubtitleProcessor

# Set your API key
os.environ['OPENAI_API_KEY'] = 'your-api-key-here'

# Initialize translator
translator = GPTTranslator()

# Process a subtitle file
def progress_callback(progress):
    print(f"Progress: {progress}%")

def status_callback(status):
    print(f"Status: {status}")

processor = SubtitleProcessor(
    file_path='path/to/subtitle.srt',
    translator=translator,
    target_language='Spanish',
    progress_callback=progress_callback,
    status_callback=status_callback
)

# Start translation
processor.translate()
```

See `example.py` for more detailed programmatic usage examples.

## 📚 Detailed Usage Guide

### Processing Modes

#### Single File Mode
- Select one or more specific video files
- Ideal for individual movies or episodes
- Shows detailed progress for each file

#### Batch Processing Mode
- Select a folder containing video files
- Automatically discovers all supported video files
- Processes them sequentially with overall progress tracking

### Translation Options

#### Target Language
- Enter any language name (e.g., "Spanish", "Portuguese", "Japanese")
- The application automatically maps to appropriate language codes
- Supports all languages that GPT models can translate

#### Auto-select English Subtitles
- Automatically finds and selects English subtitle streams
- Useful for batch processing where you want consistent source language
- Can be disabled to manually select subtitle streams

#### Block Limiting
- **All Subtitles**: Translate the entire subtitle file
- **Limited**: Translate only a specified number of subtitle blocks
- Useful for testing translations before processing large files

### Subtitle Stream Selection

For video files with multiple subtitle streams:
- The application lists all available subtitle streams
- Shows language, codec, and title information
- Auto-selects English streams when the option is enabled
- Manual selection available for fine control

### Jellyfin Integration

#### Naming Convention
The application can rename subtitle files to follow Jellyfin standards:
- `movie.en.srt` - English subtitles
- `movie.es.srt` - Spanish subtitles
- `movie.es.forced.srt` - Spanish forced subtitles
- `movie.es.default.srt` - Spanish default subtitles

#### Available Flags
- **Default**: Mark as the default subtitle track
- **Forced**: Mark as forced subtitles (for foreign language parts)
- **SDH**: Mark as hearing impaired subtitles
- **Delete originals**: Remove original files after successful renaming

#### Preview and Apply
- **Preview Rename**: See what changes will be made before applying
- **Rename for Jellyfin**: Apply the renaming with selected flags

### Time Synchronization

#### Adjustment Options
- Adjust subtitle timing by milliseconds
- Quick adjustment buttons: -1s, -500ms, +500ms, +1s
- Manual entry for precise timing
- Supports adjustments from -1 hour to +1 hour

#### Use Cases
- Fix subtitles that are out of sync with video
- Adjust for different video frame rates
- Compensate for video encoding timing differences

## 🔧 Configuration

### Settings Persistence
The application automatically saves:
- Target language preference
- Auto-select English option
- Last used directory
- OpenAI API key (stored locally)

### API Key Security
- API keys are stored locally in `translator_settings.json`
- The key field is hidden by default with a show/hide toggle
- Keys are also stored in environment variables during runtime

## 🛠️ Troubleshooting

### Common Issues

#### "ffmpeg is not installed" Error
**Problem**: FFmpeg is not found in system PATH
**Solution**: 
- Install FFmpeg for your operating system
- Ensure it's added to your system PATH
- Restart the terminal/application after installation

#### "No subtitle streams found" Error
**Problem**: Video file doesn't contain embedded subtitles
**Solution**:
- Use video files with embedded subtitles
- Or use external SRT files directly
- Check video properties to confirm subtitle tracks exist

#### Translation API Errors
**Problem**: OpenAI API errors during translation
**Solutions**:
- Verify your API key is correct and active
- Check your OpenAI account has sufficient credits
- Ensure internet connection is stable
- Try reducing batch size for large files

#### Encoding Issues
**Problem**: Subtitle files have garbled characters
**Solution**:
- The application tries multiple encodings automatically
- For persistent issues, convert subtitle files to UTF-8 encoding
- Use subtitle editing tools to fix encoding before translation

#### Memory Issues with Large Files
**Problem**: Application becomes slow with very large subtitle files
**Solutions**:
- Use the block limit feature for testing
- Process files in smaller batches
- Close other applications to free memory

### Performance Optimization

#### For Large Batch Jobs
- Process during off-peak hours to avoid API rate limits
- Monitor your OpenAI usage to manage costs
- Use batch processing for efficiency

#### For Better Accuracy
- Ensure source subtitles are clean and well-formatted
- Use descriptive target language names (e.g., "Mexican Spanish" vs "Spanish")
- Review translated samples before processing large batches

## 🧪 Testing

### Basic Functionality Test

Run the included test script to verify that core components are working:

```bash
python test_basic.py
```

This will test:
- Module imports
- Jellyfin filename generation
- Language code mapping
- Output path generation

### Example Usage

Run the example script to see how to use the components programmatically:

```bash
python example.py
```

This will show example usage and check your environment setup.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

### Development Setup
1. Fork the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Feature Requests
- Support for additional subtitle formats (ASS, VTT)
- Integration with other translation services
- Subtitle quality assessment tools
- Custom translation prompts

## 📄 License

This project is open source. Please check the repository for license details.

## 🙏 Acknowledgments

- OpenAI for providing powerful translation capabilities
- FFmpeg project for video processing tools
- CustomTkinter for modern UI components
- pysrt library for subtitle file handling

## 📁 Project Structure

```
Subtitle-Translator/
├── README.md                 # This documentation
├── requirements.txt          # Python dependencies
├── setup.sh                 # Automated setup script
├── example.py               # Programmatic usage examples
├── test_basic.py            # Basic functionality tests
├── subtitle_translator.py   # Main GUI application
├── translator.py            # OpenAI GPT translation logic
├── subtitle_processor.py    # SRT file processing
├── subtitle_extractor.py    # Video subtitle extraction
└── jellyfin_renamer.py      # Jellyfin filename utilities
```

## 📞 Support

If you encounter issues or have questions:
1. Check this README for common solutions
2. Search existing GitHub issues
3. Create a new issue with detailed information
4. Include error messages and system information

---

**Happy Translating! 🎬✨**