from app.services.llm.job_requirements import JobParsePrompt
from app.services.llm.relevant_projects import RelevantProjectsPrompt
from app.services.projects import get_projects_service
from app.decorators.time_perf import time_performance
from app.schemas.llm_outputs.job_requirements import JobRequirement
from app.repository import ProjectRepository
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from app.services.llm.qwen import QwenClient
    
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
test_file_path = os.path.join(BASE_DIR, "test.txt")

project_service = get_projects_service()
project_repository = ProjectRepository()


# Initialize the Gemini model (e.g., Gemini 2.0 Flash)
gemini_llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash",
    temperature=0.1,
    max_tokens=4096,
)

qwen_llm = QwenClient().model

def get_projects(user_id:int,tags:list[str])->list[dict]:
    result = project_repository.get_relevant(user_id=user_id,techs=tags)
    items = [ {
        "id":item[0].id,
        "name":item[0].name,
        "technologies":item[0].technologies,
        "count":item[1]
        } for item in result]
    return items


def vector_search(user_id:int,vacancy):
    items = project_service.rank_projects_overlap(user_id,vacancy)
    print(json.dumps(items, indent=2, ensure_ascii=False))


def sql_search(text, tech_tags, user_id):
    result = get_projects(user_id,tech_tags)
    print("SQL RESULT",json.dumps(result,indent=2, ensure_ascii=False))
    if len(result) > 2:    
        relevant_promt = RelevantProjectsPrompt()
        relevant_projects = relevant_promt.get_sync_response({"job_text":text,"technologies":tech_tags,"projects":result})
        print("LLM RESULT",json.dumps(relevant_projects.model_dump(),indent=2, ensure_ascii=False))
    else:
        print("LLM RESULT",json.dumps(result,indent=2, ensure_ascii=False))

@time_performance
def qwen_test():
    prompt = JobParsePrompt()
    text = None
    with open(test_file_path, "r", encoding="utf-8") as file:
        text = file.read()
    if text is not None:
        
        result = prompt.get_sync_response({"job_text": text})
        print("result",result)
        tech_tags = result.model_dump()["technologies"]
        user_id = 1
        
        # print(tech_tags)
        print("==========SQL============")
        
        # sql_search(text, tech_tags, user_id)

qwen_test()