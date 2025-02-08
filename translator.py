from openai import OpenAI
import os
import json

class GPTTranslator:
    def __init__(self):
        # Get API key from environment variable
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = OpenAI(api_key=api_key)
        
    def translate(self, texts, target_language):
        try:
            # Create a list of texts with indices
            text_array = [{"id": i, "text": text} for i, text in enumerate(texts)]
            
            system_prompt = f"""You are a professional subtitle translator. 
            Translate the following subtitle texts from English to {target_language}.
            Return ONLY a JSON object with a 'translations' array containing the translated texts.
            Each translation must keep the same ID as its source text.
            Keep the same number of lines as the source text and match the layout with new lines.
            """

            user_prompt = f"""Please translate these subtitles:
            {json.dumps(text_array, ensure_ascii=False, indent=2)}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Keep original model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            try:
                translated_json = json.loads(response.choices[0].message.content)
                if 'translations' not in translated_json:
                    raise ValueError("Response missing 'translations' key")
                
                # Sort by id and return only the translated texts in order
                sorted_translations = sorted(translated_json['translations'], key=lambda x: x['id'])
                return [item['text'] for item in sorted_translations]
                
            except json.JSONDecodeError as e:
                raise Exception(f"Failed to parse JSON response: {str(e)}")
            except KeyError as e:
                raise Exception(f"Invalid response format: {str(e)}")
            
        except Exception as e:
            raise Exception(f"Translation error: {str(e)}") 