import pysrt
import threading
from queue import Queue
import logging
import time
import os
import re
import backoff
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

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
        self.batch_size = 50  # Process 50 subtitles at a time
        self.overlap = 0  # No overlap needed with new context handling
        self.progress_lock = Lock()
        self.total_progress = 0
        self.completed_batches = 0
        self.total_batches = 0
        self.processed_subtitles = 0
        self.total_subtitles = 0
        logger.debug(f"Initialized SubtitleProcessor with file: {file_path}")
        
    def translate(self):
        """Start translation in a separate thread"""
        self.cancel_flag = False
        thread = threading.Thread(target=self._translate_process)
        thread.start()
        logger.debug("Started translation thread")
        
    def _update_progress_safe(self, processed_count):
        """Thread-safe progress update based on processed subtitles"""
        with self.progress_lock:
            self.processed_subtitles += processed_count
            progress = (self.processed_subtitles / self.total_subtitles) * 100
            self.progress_callback(min(100, progress))
            
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
        
    def _process_subtitle_batch(self, batch, batch_index):
        """Process a batch of subtitles"""
        try:
            # Clean texts before translation
            batch_texts = [self._clean_subtitle_text(sub.text) for sub in batch]
            
            # Translate the batch
            translated_texts = self._translate_batch(batch_texts)
            
            # Update progress based on number of subtitles in this batch
            self._update_progress_safe(len(batch))
            
            # Update status with more detailed information
            with self.progress_lock:
                self.completed_batches += 1
                self.status_callback(
                    f"Completed batch {self.completed_batches}/{self.total_batches} "
                    f"({self.processed_subtitles}/{self.total_subtitles} subtitles)"
                )
            
            return list(zip(batch, translated_texts))
            
        except Exception as e:
            logger.error(f"Batch processing error: {str(e)}")
            raise
            
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

            # Apply block limit if specified
            if self.block_limit:
                total_subs = min(len(subs), self.block_limit)
                subs = subs[:total_subs]
                logger.debug(f"Applied block limit: {total_subs} subtitles")
            else:
                total_subs = len(subs)
                logger.debug(f"Processing all {total_subs} subtitles")
            
            # Initialize progress tracking
            self.total_subtitles = total_subs
            self.processed_subtitles = 0
            
            # Create output path
            srt_output_path = self._create_subtitle_path(self.file_path)
            logger.debug(f"Will save translated subtitles to: {srt_output_path}")

            # Process subtitles sequentially in batches
            translated_subs = []
            batch_size = self.batch_size
            
            for start_idx in range(0, total_subs, batch_size):
                if self.cancel_flag:
                    logger.info("Translation cancelled by user")
                    self.status_callback("Translation cancelled")
                    return

                end_idx = min(start_idx + batch_size, total_subs)
                batch = subs[start_idx:end_idx]
                
                # Clean and prepare batch texts
                batch_texts = []
                for sub in batch:
                    cleaned_text = self._clean_subtitle_text(sub.text)
                    # Add context about timing to help maintain order
                    batch_texts.append(f"[{sub.index}] {cleaned_text}")
                
                try:
                    # Translate the batch
                    translated_texts = self._translate_batch(batch_texts)
                    
                    # Process translated texts and maintain original properties
                    for i, (sub, trans_text) in enumerate(zip(batch, translated_texts)):
                        # Remove the index prefix we added
                        trans_text = re.sub(r'^\[\d+\]\s*', '', trans_text)
                        # Create a new subtitle object with original timing
                        new_sub = pysrt.SubRipItem(
                            index=sub.index,
                            start=sub.start,
                            end=sub.end,
                            text=trans_text
                        )
                        translated_subs.append(new_sub)
                    
                    # Update progress
                    self._update_progress_safe(len(batch))
                    self.completed_batches += 1
                    self.status_callback(
                        f"Completed batch {self.completed_batches}/{(total_subs + batch_size - 1) // batch_size} "
                        f"({self.processed_subtitles}/{self.total_subtitles} subtitles)"
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing batch {start_idx//batch_size}: {str(e)}")
                    raise
            
            # Sort subtitles by index to ensure correct order
            translated_subs.sort(key=lambda x: x.index)
            
            # Write to file
            with open(srt_output_path, 'w', encoding='utf-8') as f:
                for sub in translated_subs:
                    f.write(f"{sub.index}\n")
                    f.write(f"{sub.start} --> {sub.end}\n")
                    f.write(f"{sub.text}\n\n")
            
            # Final status update
            logger.info(f"Translation completed. Saved to: {srt_output_path}")
            self.status_callback(f"Translation completed successfully! Saved to: {srt_output_path}")
            self.progress_callback(100)  # Ensure we reach 100%
            
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