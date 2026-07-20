# gemini_wrapper.py
from langchain.llms.base import LLM
from typing import Optional, List
import google.generativeai as genai
import os


class GeminiLLM(LLM):
    """
    🔄 Replaced Groq backend with Gemini backend internally.
    Name kept as GroqLLM so no other file breaks.
    """

    model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
    temperature: float = 0.2

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"

    def __init__(self, model=None, temperature=0.2, **kwargs):
        super().__init__(**kwargs)

        # Load Gemini key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ GEMINI_API_KEY missing in .env")

        genai.configure(api_key=api_key)

        # Use user model or default
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        self.temperature = temperature

        # Gemini client
        self.client = genai.GenerativeModel(self.model)

    # -------------------------------
    # REQUIRED by LangChain interface
    # -------------------------------
    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        response = self.client.generate_content(
            prompt,
            generation_config={"temperature": self.temperature},
        )

        text = response.text

        # Apply stop tokens manually if needed
        if stop:
            for token in stop:
                if token in text:
                    text = text.split(token)[0]

        return text

    @property
    def _llm_type(self) -> str:
        return "gemini-llm"

    @property
    def _identifying_params(self) -> dict:
        return {"model": self.model, "temperature": self.temperature}
