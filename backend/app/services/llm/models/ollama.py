from langchain_ollama import ChatOllama

from app.core.config import settings


class OllamaModel():
    def __init__(self,*args, **kwargs):
        
        kwargs.setdefault("base_url", settings.OLLAMA_HOST)
        self.__model = ChatOllama( *args, **kwargs)
    
    @property
    def model(self):
        return self.__model