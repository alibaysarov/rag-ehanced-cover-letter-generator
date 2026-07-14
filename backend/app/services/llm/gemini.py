from app.services.llm.general import GeneralLLMClient
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI

import os

_MODEL="qwen2.5:7b"
_GEMINI_MODEL = "gemini-3.5-flash"
class GeminiClient(GeneralLLMClient):
    def __init__(self):
        
        gemini_model = ChatGoogleGenerativeAI(
            model=_GEMINI_MODEL,
            temperature=0,
            max_tokens=4096,
        )
        
        base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        fallback_model = ChatOllama(model=_MODEL,format="json", temperature=0, base_url=base_url)
        model = gemini_model.with_fallbacks([
            # fallback_model
            ])
        super().__init__(model=model)