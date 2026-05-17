from app.services.projects import ProjectStorageService, get_projects_service
from app.repository.user_repository import UserRepository
from ..services.llm.job_requirements import JobParsePrompt
from ..schemas.llm_outputs.job_requirements import JobRequirement
from app.services.llm.job_items import CoverLetterPrompt
from app.services.llm.agents.tools.fetch_url import parse_hh
from app.cache import redis as redis_db
import json

def get_projects_storage_service() -> ProjectStorageService:
    return get_projects_service()

class CoverLetterService:

    def __init__(self, user_repo: UserRepository):
        self.llm = CoverLetterPrompt()
        self.projects_service = get_projects_service()
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

        async for delta in self.llm.get_stream_response(body):
            yield delta
    
    async def stream_by_url(self,url:str,user_id:int ):
        try:
            body = await self.__get_data_from_url(url,user_id)
        except Exception as e:
            print(f"URL parse error: {e}")
            yield "__URL_PARSE_ERROR__"
            return

        async for delta in self.llm.get_stream_response(body):
            yield delta
    
    async def __get_data_from_text(self,text:str,user_id:int):
        job_parse = JobParsePrompt()
        chain = job_parse.prompt_template | job_parse.get_model
        vacancy: JobRequirement = chain.invoke({"job_text": text})

        ranked = self.projects_service.rank_projects_overlap(
            user_id=user_id,
            vacancy=vacancy,
            top_k=5,
        )

        user = self.user_repo.get_user_by_id(user_id)
        user_projects = self.__projects_normalize(ranked=ranked)
        body = {
            "name":vacancy.name,
            "lang":vacancy.lang,
            "project_name":vacancy.project_name,
            "user_projects":user_projects,
            "requirements":vacancy.requirements,
            "user_first_name": (user.first_name or "") if user else "",
            "user_last_name": (user.last_name or "") if user else "",
        }
        return body
    
    async def __get_data_from_url(self,url:str,user_id:int):
        text = None
        if await redis_db.redis_client.get(url) is None:
            text = await parse_hh(url)
            await redis_db.redis_client.set(url,text,ex=3600)
        else:
            text = await redis_db.redis_client.get(url)
            print("cache hit")
        job_parse = JobParsePrompt()
        chain = job_parse.prompt_template | job_parse.get_model
        vacancy: JobRequirement = chain.invoke({"job_text": text})
        
        ranked = self.projects_service.rank_projects_overlap(
            user_id=user_id,
            vacancy=vacancy,
            top_k=5,
        )
        printed_ranked = [{
            "project_name": item["payload"]["project_name"],
            "technologies": item["payload"]["technologies"],
            }for item in ranked]
        print("ranked ",printed_ranked)
        user = self.user_repo.get_user_by_id(user_id)
        user_projects = self.__projects_normalize(ranked=ranked)
        body = {
            "name":vacancy.name,
            "lang":vacancy.lang,
            "project_name":vacancy.project_name,
            "user_projects":user_projects,
            "requirements":vacancy.requirements,
            "user_first_name": (user.first_name or "") if user else "",
            "user_last_name": (user.last_name or "") if user else "",
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