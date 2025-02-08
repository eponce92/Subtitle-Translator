import subprocess
import os
import json

class SubtitleExtractor:
    def __init__(self):
        # Check if ffmpeg is installed
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True)
        except FileNotFoundError:
            raise Exception("ffmpeg is not installed. Please install ffmpeg to extract embedded subtitles.")

    def list_subtitles(self, video_path):
        """List all available subtitle streams in the video file"""
        try:
            # Get subtitle stream information using ffprobe
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                '-select_streams', 's',  # Only select subtitle streams
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            streams = json.loads(result.stdout).get('streams', [])
            
            subtitle_streams = []
            for stream in streams:
                language = stream.get('tags', {}).get('language', 'unknown')
                codec = stream.get('codec_name', 'unknown')
                index = stream.get('index')
                title = stream.get('tags', {}).get('title', f'Subtitle {index}')
                
                subtitle_streams.append({
                    'index': index,
                    'language': language,
                    'codec': codec,
                    'title': title
                })
                
            return subtitle_streams
            
        except Exception as e:
            raise Exception(f"Failed to list subtitles: {str(e)}")

    def extract_subtitle(self, video_path, stream_index, output_path=None):
        """Extract a specific subtitle stream to an SRT file"""
        try:
            if output_path is None:
                # Generate output path if not provided
                base_path = os.path.splitext(video_path)[0]
                output_path = f"{base_path}_stream_{stream_index}.srt"

            # Extract subtitle using ffmpeg with formatting removal
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-map', f'0:{stream_index}',
                '-c:s', 'text',  # Force text output
                '-f', 'srt',     # Force SRT format
                '-scodec', 'srt',  # Use SRT codec
                '-y',            # Overwrite output file
                output_path
            ]
            
            # For ASS/SSA subtitles, add extra parameters to strip formatting
            if any(ext in video_path.lower() for ext in ['.ass', '.ssa']):
                cmd.extend([
                    '-ass_style_override', '1',  # Override ASS styles
                    '-ass_style_override_all', '1'  # Override all styles
                ])
            
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Additional cleanup pass to ensure clean SRT
            self._clean_srt_file(output_path)
            
            return output_path
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to extract subtitle: {e.stderr.decode()}")
        except Exception as e:
            raise Exception(f"Failed to extract subtitle: {str(e)}")

    def _clean_srt_file(self, srt_path):
        """Clean up the SRT file to ensure proper formatting"""
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Clean lines and remove any remaining formatting
            cleaned_lines = []
            for line in lines:
                # Remove any HTML/font tags
                line = self._remove_formatting(line)
                cleaned_lines.append(line)

            # Write back clean content
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)

        except Exception as e:
            raise Exception(f"Failed to clean SRT file: {str(e)}")

    def _remove_formatting(self, line):
        """Remove formatting tags from a line"""
        import re
        # Remove font tags
        line = re.sub(r'<font[^>]*>', '', line)
        line = re.sub(r'</font>', '', line)
        # Remove other HTML-like tags
        line = re.sub(r'<[^>]+>', '', line)
        # Remove any ASS/SSA formatting
        line = re.sub(r'\{\\[^}]+\}', '', line)
        return line 