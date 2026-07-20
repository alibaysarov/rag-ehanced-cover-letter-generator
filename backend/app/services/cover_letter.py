from app.services.projects import ProjectStorageService, get_projects_service
from app.repository.user_repository import UserRepository
from ..services.llm.job_requirements import JobParsePrompt
from ..schemas.llm_outputs.job_requirements import JobRequirement
from app.services.llm.relevant_projects import RelevantProjectsPrompt

from app.services.llm.job_items import CoverLetterPrompt
from app.services.llm.agents.tools.fetch_url import parse_hh
from app.cache import redis as redis_db
from app.repository.project_repository import ProjectRepository
from app.models import Project
from langsmith import traceable
import json
import re
import asyncio

def get_projects_storage_service() -> ProjectStorageService:
    return get_projects_service()

class CoverLetterService:

    def __init__(self, user_repo: UserRepository):
        self.llm = CoverLetterPrompt()
        self.projects_service = get_projects_service()
        self.project_repository = ProjectRepository()
        self.user_repo = user_repo
    
    async def sync_by_url(self,url:str,user_id:int):
        chain = self.llm.prompt_template | self.llm.get_model
        body = await self.__get_data_from_url(url,user_id)
        result = await chain.ainvoke(body)
        return result.content
    
    
    async def stream_by_text(self,vacancy_name:str,vacancy_text:str,user_id:int, lang:str|None=None):

        text = f"""
        {vacancy_name}\n
        {vacancy_text}
        """

        body = await self.__get_data_from_text(text=text,user_id=user_id)
        if lang:
            body["lang"] = lang

        async for delta in self._clean_stream(body):
            yield delta

    async def stream_by_url(self,url:str,user_id:int ):
        try:
            body = await self.__get_data_from_url(url,user_id)
        except Exception as e:
            print(f"URL parse error: {e}")
            yield "__URL_PARSE_ERROR__"
            return

        async for delta in self._clean_stream(body):
            yield delta

    # Patterns stripped from the very start of LLM output
    _STRIP_LABEL = re.compile(
        r'^\s*(сообщение|письмо|текст\s+письма|ответ|вот\s+письмо)[:\-]?\s*\n*',
        re.IGNORECASE,
    )

    
    
    
    async def _clean_stream(self, body: dict):
        result = await (self.llm.prompt_template | self.llm.get_model).ainvoke(body)
        text = result.content
        text = self._STRIP_LABEL.sub("", text).lstrip("\n ")

        chunk_size = 20
        for i in range(0, len(text), chunk_size):
            yield text[i:i+chunk_size]
            await asyncio.sleep(0.02)


    @staticmethod
    def _chunk_to_text(chunk) -> str:
        """Normalize a stream chunk (str | list | dict | None) to plain text."""
        if chunk is None:
            return ""
        if isinstance(chunk, str):
            return chunk
        if isinstance(chunk, list):
            parts = []
            for part in chunk:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict):
                    parts.append(part.get("text", "") or "")
                else:
                    text_attr = getattr(part, "text", None)
                    if text_attr:
                        parts.append(text_attr)
            return "".join(parts)
        if isinstance(chunk, dict):
            return chunk.get("text", "") or ""
        # fallback for objects with a `.content` or `.text` attribute
        text_attr = getattr(chunk, "text", None) or getattr(chunk, "content", None)
        return text_attr if isinstance(text_attr, str) else ""
    
    
    async def __get_data_from_text(self,text:str,user_id:int):
        job_parse = JobParsePrompt()
        chain = job_parse.prompt_template | job_parse.get_model
        vacancy: JobRequirement =await chain.ainvoke({"job_text": text})

        ranked = self._get_ranked_projects(user_id,text, vacancy)
        
        user = self.user_repo.get_user_by_id(user_id)
        user_projects = self.__projects_normalize(ranked=ranked)
        body = {
            "name":vacancy.name,
            "lang":"ru",
            "project_name":vacancy.name,
            "user_projects":user_projects,
            "vacancy_requirements":vacancy.technologies,
            "vacancy_technologies":vacancy.technologies,
            "user_first_name": (user.first_name or "") if user else "",
            "user_last_name": (user.last_name or "") if user else "",
        }
        return body

    def _get_ranked_projects(self, user_id,vacancy_text:str, job_requirement:JobRequirement):
        
        relevant_projects = self.project_repository.get_relevant(user_id,job_requirement.technologies)
            
        if len(relevant_projects) > 2:
            relevant_project_promt = RelevantProjectsPrompt()
            model_response = relevant_project_promt.get_sync_response({
                "job_text":vacancy_text,
                "technologies":job_requirement.technologies,
                "projects":relevant_projects
            })
            projects = model_response.projects
            result = []
            
            
            
            for project in projects:
                relevant_projects
                item = next((item for item,_ in relevant_projects if str(item.id) == str(project.id)), None)
                if item is not None:
                    result.append(item)
            return result
        
        return [project for project,_ in relevant_projects] 
    

    async def __get_data_from_url(self,url:str,user_id:int):
        
        text = await self.__fetch_from_browser(url)
        job_parse = JobParsePrompt()
        chain = job_parse.prompt_template | job_parse.get_model
        vacancy: JobRequirement = chain.invoke({"job_text": text})
        
        ranked = self._get_ranked_projects(user_id=user_id,vacancy_text=text,job_requirement=vacancy)
        
        
        user = self.user_repo.get_user_by_id(user_id)
        user_projects = self.__projects_normalize(ranked=ranked)
        body = {
            "name":vacancy.name,
            "lang":vacancy.lang,
            "project_name":vacancy.project_name,
            "user_projects":user_projects,
            "vacancy_requirements":vacancy.requirements,
            "vacancy_technologies":vacancy.technologies,
            "user_first_name": (user.first_name or "") if user else "",
            "user_last_name": (user.last_name or "") if user else "",
        }
        return body

    async def __fetch_from_browser(self, url:str):
        if await redis_db.redis_client.get(url) is None:
            text = await parse_hh(url)
            await redis_db.redis_client.set(url,text,ex=3600)
        else:
            text = await redis_db.redis_client.get(url)
        return text
    
    
    def __projects_normalize(self, ranked: list[Project]) -> str:
        result = [
            {
                "project_name":item.name,
                "skills":item.skills,
                "achievements":item.achievements,
                "technologies":item.technologies
            } for item in ranked
        ]
        return json.dumps(result, ensure_ascii=False, indent=2)