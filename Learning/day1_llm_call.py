from pathlib import Path
import os

from dotenv import load_dotenv
import google.genai as genai
from google.genai import errors
from google.genai import types

load_dotenv(dotenv_path=Path(__file__).with_name('.env'))

api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    api_key = os.getenv('GEMINI_API_KEY')

if not api_key:
    raise ValueError('Set GOOGLE_API_KEY or GEMINI_API_KEY in Learning/.env')

client = genai.Client(api_key=api_key)
try:
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents='What is a multi-agent system?',
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=1024,
        ),
    )
    print(response.text)
except errors.ClientError as exc:
    if getattr(exc, 'status_code', None) == 401:
        raise RuntimeError(
            'Gemini rejected the API key. As of June 19, 2026, unrestricted '
            'standard Gemini keys are rejected. Create a new auth key in '
            'Google AI Studio or add restrictions to the existing key.'
        ) from exc
    raise
