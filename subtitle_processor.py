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
        logger.debug(f"Initialized SubtitleProcessor with file: {file_path}")
        
    def translate(self):
        """Start translation in a separate thread"""
        self.cancel_flag = False
        thread = threading.Thread(target=self._translate_process)
        thread.start()
        logger.debug("Started translation thread")
        
    def _update_progress_safe(self, value):
        """Thread-safe progress update"""
        with self.progress_lock:
            self.total_progress = min(100, max(self.total_progress, value))
            self.progress_callback(self.total_progress)
            
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
        
    def _process_subtitle_batch(self, batch, total_subs):
        """Process a batch of subtitles"""
        try:
            # Clean texts before translation
            batch_texts = [self._clean_subtitle_text(sub.text) for sub in batch]
            
            # Translate the batch
            translated_texts = self._translate_batch(batch_texts)
            
            # Update progress based on batch size
            progress = (len(batch) / total_subs) * 100
            self._update_progress_safe(progress)
            
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
            
            # Create empty output file
            with open(srt_output_path, 'w', encoding='utf-8') as f:
                f.write("")
            
            # Process in parallel batches
            batches = [subs[i:i + self.batch_size] for i in range(0, total_subs, self.batch_size)]
            all_results = []
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_batch = {
                    executor.submit(self._process_subtitle_batch, batch, total_subs): i 
                    for i, batch in enumerate(batches)
                }
                
                # Process results as they complete
                for future in as_completed(future_to_batch):
                    if self.cancel_flag:
                        executor.shutdown(wait=False)
                        logger.info("Translation cancelled by user")
                        self.status_callback("Translation cancelled")
                        return
                        
                    batch_idx = future_to_batch[future]
                    try:
                        batch_results = future.result()
                        all_results.extend(batch_results)
                        
                        # Update status
                        progress = ((batch_idx + 1) / len(batches)) * 100
                        self.status_callback(
                            f"Processed batch {batch_idx + 1}/{len(batches)} "
                            f"({len(all_results)}/{total_subs} subtitles)"
                        )
                        
                    except Exception as e:
                        logger.error(f"Batch {batch_idx} failed: {str(e)}")
                        raise
            
            # Sort results by original subtitle index
            all_results.sort(key=lambda x: x[0].index)
            
            # Write all results to file
            with open(srt_output_path, 'w', encoding='utf-8') as f:
                for sub, translated_text in all_results:
                    sub.text = translated_text
                    f.write(f"{sub.index}\n")
                    f.write(f"{sub.start} --> {sub.end}\n")
                    f.write(f"{sub.text}\n\n")
            
            # Final status update
            logger.info(f"Translation completed. Saved to: {srt_output_path}")
            self.status_callback(f"Translation completed successfully! Saved to: {srt_output_path}")
            self._update_progress_safe(100)
            
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