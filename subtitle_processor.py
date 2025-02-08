import pysrt
import threading
from queue import Queue
import logging
import time
import os
import re
import backoff

logger = logging.getLogger(__name__)

class SubtitleProcessor:
    # ISO 639-1 language codes mapping
    LANGUAGE_CODES = {
        'english': 'eng',
        'spanish': 'spa',
        'french': 'fre',
        'german': 'ger',
        'italian': 'ita',
        'portuguese': 'por',
        'russian': 'rus',
        'japanese': 'jpn',
        'korean': 'kor',
        'chinese': 'chi'
        # Add more as needed
    }
    
    def __init__(self, file_path, translator, target_language, progress_callback, status_callback, block_limit=None):
        self.file_path = file_path
        self.translator = translator
        self.target_language = target_language
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self.cancel_flag = False
        self.block_limit = block_limit
        self.batch_size = 50  # Increased batch size for better performance
        self.overlap = 0  # Removed overlap since we're handling context differently
        logger.debug(f"Initialized SubtitleProcessor with file: {file_path}")
        
    def translate(self):
        self.cancel_flag = False
        thread = threading.Thread(target=self._translate_process)
        thread.start()
        logger.debug("Started translation thread")
        
    def _get_language_code(self, language):
        """Get the ISO 639-1/2 language code"""
        return self.LANGUAGE_CODES.get(language.lower(), language.lower()[:3])
        
    def _create_subtitle_path(self, file_path):
        """Create standardized subtitle filename"""
        base_path = os.path.splitext(file_path)[0]
        lang_code = self._get_language_code(self.target_language)
        
        # Create filename in format: moviename.spa.srt
        return f"{base_path}.{lang_code}.srt"
        
    def _clean_subtitle_text(self, text):
        """Remove HTML/font tags and clean up subtitle text"""
        # Remove font tags and other HTML
        text = re.sub(r'<font[^>]*>', '', text)
        text = re.sub(r'</font>', '', text)
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove any double spaces
        text = ' '.join(text.split())
        
        return text.strip()
        
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        max_time=300,
        on_backoff=lambda details: logger.warning(f"Backing off {details['wait']:0.1f} seconds after {details['tries']} tries")
    )
    def _translate_batch(self, batch_texts):
        """Translate a batch of texts with retry logic"""
        return self.translator.translate(batch_texts, self.target_language)
        
    def _translate_process(self):
        try:
            # Check if file is a subtitle file
            if not self.file_path.lower().endswith('.srt'):
                raise Exception("Input file must be a .srt subtitle file")

            # Load subtitles with different encodings
            logger.debug(f"Loading subtitles from {self.file_path}")
            subs = None
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    subs = pysrt.open(self.file_path, encoding=encoding)
                    logger.debug(f"Successfully loaded subtitles with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    logger.debug(f"Error loading with {encoding}: {str(e)}")
                    continue
            
            if subs is None:
                raise Exception("Failed to load subtitle file with any supported encoding")
                
            # Clean subtitle texts before translation
            for sub in subs:
                sub.text = self._clean_subtitle_text(sub.text)
            
            # Store original file path to delete later
            original_english_file = self.file_path
            is_extracted_file = "_stream_" in original_english_file
            
            # Apply block limit if specified
            if self.block_limit:
                total_subs = min(len(subs), self.block_limit)
                subs = subs[:total_subs]
                logger.debug(f"Applied block limit: {total_subs} subtitles")
            else:
                total_subs = len(subs)
                logger.debug(f"Processing all {total_subs} subtitles")
            
            # Create output path with standard naming convention
            srt_output_path = self._create_subtitle_path(self.file_path)
            logger.debug(f"Will save translated subtitles to: {srt_output_path}")
            
            # Create output file
            with open(srt_output_path, 'w', encoding='utf-8') as f:
                f.write("")  # Initialize empty file
            
            # Process in larger batches
            for i in range(0, total_subs, self.batch_size):
                if self.cancel_flag:
                    logger.info("Translation cancelled by user")
                    self.status_callback("Translation cancelled")
                    return
                    
                batch_end = min(i + self.batch_size, total_subs)
                current_batch = subs[i:batch_end]
                
                # More detailed status updates
                batch_num = (i // self.batch_size) + 1
                total_batches = (total_subs + self.batch_size - 1) // self.batch_size
                self.status_callback(
                    f"Translating batch {batch_num}/{total_batches} "
                    f"(subtitles {i+1}-{batch_end} of {total_subs})"
                )
                
                try:
                    # Clean texts before translation
                    batch_texts = [self._clean_subtitle_text(sub.text) 
                                 for sub in current_batch]
                    
                    # Translate with retry logic
                    translated_texts = self._translate_batch(batch_texts)
                    
                    # Save translations immediately
                    with open(srt_output_path, 'a', encoding='utf-8') as f:
                        for j, (sub, translated_text) in enumerate(
                            zip(current_batch, translated_texts)
                        ):
                            sub_num = i + j + 1
                            sub.text = translated_text
                            f.write(f"{sub_num}\n")
                            f.write(f"{sub.start} --> {sub.end}\n")
                            f.write(f"{sub.text}\n\n")
                    
                except Exception as e:
                    logger.error(
                        f"Error translating batch {i+1}-{batch_end}: {str(e)}"
                    )
                    raise
                
                # Update progress
                progress = min((batch_end / total_subs) * 100, 100)
                self.progress_callback(progress)
                logger.debug(f"Progress: {progress:.1f}%")
                
                # Add a small delay between batches to avoid hitting rate limits
                time.sleep(0.1)
            
            # Final status update
            logger.info(f"Translation completed. Saved to: {srt_output_path}")
            self.status_callback(
                f"Translation completed successfully! Saved to: {srt_output_path}"
            )
            self.progress_callback(100)
            
        except Exception as e:
            logger.exception("Translation process failed:")
            self.status_callback(f"Error: {str(e)}")
            raise 

    def adjust_timing(self, srt_file_path, time_delta_ms):
        """Adjust subtitle timings by a given number of milliseconds"""
        try:
            # Load subtitles
            subs = pysrt.open(srt_file_path)
            
            # Shift all subtitles by time_delta_ms
            subs.shift(milliseconds=time_delta_ms)
            
            # Save the adjusted subtitles
            subs.save(srt_file_path, encoding='utf-8')
            
            return True
            
        except Exception as e:
            logger.error(f"Error adjusting subtitle timing: {e}")
            return False 