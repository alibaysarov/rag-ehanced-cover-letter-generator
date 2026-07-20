from .ollama import OllamaModel


class JsonParseModel(OllamaModel):
    def __init__(self, *args, **kwargs):
        
        super().__init__(model="json-parser:latest",format="json",num_ctx=4096, temperature=0.1,num_predict=400,reasoning=False, *args, **kwargs)