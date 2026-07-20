from langchain_core.tools import tool
from dotenv import load_dotenv
import google.generativeai as genai
import os

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")


@tool("summarize_text")
def summarize_text(text: str) -> str:
    """
    Summarize text using Gemini LLM.
    """

    if not API_KEY:
        return "Missing GEMINI_API_KEY in .env"

    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(MODEL_NAME)

        prompt = f"Summarize this ERP report:\n\n{text}"

        #  FIXED: Correct Gemini API call (NO .chat, NO completions)
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.2},
        )

        return response.text.strip()

    except Exception as e:
        return f"Summary failed: {str(e)}"
