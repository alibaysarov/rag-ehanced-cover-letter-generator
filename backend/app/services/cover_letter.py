from app.services.projects import ProjectStorageService, get_projects_service
from app.helper.user import get_user_repository
from ..services.llm.job_requirements import JobParsePrompt
from ..schemas.llm_outputs.job_requirements import JobRequirement
from app.services.llm.job_items import CoverLetterPrompt
from app.services.llm.agents.tools.fetch_url import parse_hh

import json

def get_projects_storage_service() -> ProjectStorageService:
    return get_projects_service()

class CoverLetterService:
    
    def __init__(self):
        self.llm = CoverLetterPrompt()
        self.projects_service = get_projects_service()
        self.user_repo = get_user_repository()
    
    async def sync_by_url(self,url:str,user_id:int):
        chain = self.llm.prompt_template | self.llm.get_model
        body = await self.__get_data_from_url(url,user_id)
        result = await chain.ainvoke(body)
        return result.content
    
    
    async def stream_by_text(self,vacancy_name:str,vacancy_text:str,user_id:int):
        
        text = f"""
        {vacancy_name}\n
        {vacancy_text}
        """
        
        body = await self.__get_data_from_text(text=text,user_id=user_id)
        
        async for delta in self.llm.get_stream_response(body):
            yield delta
    
    async def stream_by_url(self,url:str,user_id:int ):
        
        body = await self.__get_data_from_url(url,user_id)

        async for delta in self.llm.get_stream_response(body):
            yield delta
    
    async def __get_data_from_text(self,text:str,user_id:int):
        job_parse = JobParsePrompt()
        chain = job_parse.prompt_template | job_parse.get_model
        vacancy: JobRequirement = chain.invoke({"job_text": text})
        
        ranked = self.projects_service.rank_projects(
            user_id=user_id,
            vacancy=vacancy,
            top_k=5,
        )
        
        user_projects = self.__projects_normalize(ranked=ranked)
        body = {
            "name":vacancy.name,
            "lang":vacancy.lang,
            "project_name":vacancy.project_name,
            "user_projects":user_projects,
            "requirements":vacancy.requirements
        }
        return body
    
    async def __get_data_from_url(self,url:str,user_id:int):
        text = await parse_hh(url)
        
        job_parse = JobParsePrompt()
        chain = job_parse.prompt_template | job_parse.get_model
        vacancy: JobRequirement = chain.invoke({"job_text": text})
        
        ranked = self.projects_service.rank_projects(
            user_id=user_id,
            vacancy=vacancy,
            top_k=5,
        )
        
        user_projects = self.__projects_normalize(ranked=ranked)
        body = {
            "name":vacancy.name,
            "lang":vacancy.lang,
            "project_name":vacancy.project_name,
            "user_projects":user_projects,
            "requirements":vacancy.requirements
        }
        return body
    
    def __projects_normalize(self, ranked: list[dict]) -> str:
        result = [
            {
                "project_name": item["payload"]["project_name"],
                "skills": item["payload"]["skills"],
                "achievements": item["payload"]["achievements"],
                "technologies": item["payload"]["technologies"],
            }
            for item in ranked
        ]
        return json.dumps(result, ensure_ascii=False, indent=2)