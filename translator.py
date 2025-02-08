import concurrent.futures
from openai import OpenAI
import os
import json
import backoff
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

logger = logging.getLogger(__name__)

class GPTTranslator:
    def __init__(self):
        # Get API key from environment variable
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = OpenAI(api_key=api_key)
        self.rate_limit_lock = Lock()
        self.last_request_time = 0
        self.min_request_interval = 0.05  # 50ms between requests for rate limiting
        
    def _rate_limit(self):
        """Simple rate limiting mechanism"""
        with self.rate_limit_lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_request_interval:
                time.sleep(self.min_request_interval - time_since_last)
            self.last_request_time = time.time()

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        max_time=300,
        on_backoff=lambda details: logger.warning(f"Backing off {details['wait']:0.1f} seconds after {details['tries']} tries")
    )
    def _translate_batch(self, batch, target_language):
        """Translate a single batch of texts"""
        try:
            self._rate_limit()  # Apply rate limiting
            
            # Create a list of texts with indices
            text_array = [{"id": i, "text": text} for i, text in enumerate(batch)]
            
            system_prompt = f"""You are a professional subtitle translator. 
            Translate the following subtitle texts from English to {target_language}.
            Return ONLY a JSON object with a 'translations' array containing the translated texts.
            Each translation must keep the same ID as its source text.
            Keep the same number of lines as the source text and match the layout with new lines.
            Translate naturally and colloquially, maintaining the original tone and style.
            """

            user_prompt = f"""Please translate these subtitles:
            {json.dumps(text_array, ensure_ascii=False, indent=2)}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using gpt-4o-mini for higher rate limits
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=4000
            )
            
            # Parse the JSON response
            try:
                translated_json = json.loads(response.choices[0].message.content)
                if 'translations' not in translated_json:
                    raise ValueError("Response missing 'translations' key")
                
                # Sort by id and return only the translated texts in order
                sorted_translations = sorted(translated_json['translations'], key=lambda x: x['id'])
                return [(item['id'], item['text']) for item in sorted_translations]
                
            except json.JSONDecodeError as e:
                raise Exception(f"Failed to parse JSON response: {str(e)}")
            except KeyError as e:
                raise Exception(f"Invalid response format: {str(e)}")
            
        except Exception as e:
            raise Exception(f"Translation error: {str(e)}")

    def translate(self, texts, target_language):
        """Translate texts in parallel using a thread pool"""
        if not texts:
            return []

        # Optimal batch size for GPT-4 API
        batch_size = 20  # Adjusted for better performance
        batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
        
        # Use ThreadPoolExecutor for parallel processing
        all_translations = []
        with ThreadPoolExecutor(max_workers=3) as executor:  # Limit concurrent API calls
            future_to_batch = {
                executor.submit(self._translate_batch, batch, target_language): i 
                for i, batch in enumerate(batches)
            }
            
            # Collect results as they complete
            batch_results = []
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    result = future.result()
                    batch_results.extend(result)
                except Exception as e:
                    logger.error(f"Batch {batch_idx} failed: {str(e)}")
                    raise
        
        # Sort all translations by their original indices and return just the texts
        batch_results.sort(key=lambda x: x[0])
        return [item[1] for item in batch_results] 