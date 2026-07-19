from app.celery_app import celery_app
from app.repository.auto_parse_job_repository import AutoParseJobRepository
from app.models.project import Project
from typing import Any,Generator
from app.repository.project_repository import ProjectRepository
from app.services.llm.job_requirements import JobParsePrompt
from app.services.llm.relevant_projects import RelevantProjectsPrompt
from app.services.llm.job_items import CoverLetterPrompt
from app.schemas.llm_outputs.relevant_projects import RelevantProject,RelevantProjects
from app.services.task_progress import set_cover_letter_task_status
from app.decorators.time_perf import time_performance
import logging

logger = logging.getLogger(__name__)


cover_letter_prompt = CoverLetterPrompt()
            

job_parse_promt = JobParsePrompt()
relevant_projects_prompt = RelevantProjectsPrompt()


project_repository = ProjectRepository()
auto_parsed_jobs_repo = AutoParseJobRepository()


def generate_cover_letter(
    name:str,
    last_name:str,
    vacancy_name:str,
    vacancy_technologies:list,
    vacancy_requirements:list,
    projects:list
    )->dict:
    cover_letter_body = {
        "user_first_name":name,
        "user_last_name":last_name,
        "lang":"ru",
        "name":vacancy_name,
        "vacancy_technologies":vacancy_technologies,
        "vacancy_requirements":vacancy_requirements,
        "user_projects":projects
    }
    cover_letter = cover_letter_prompt.get_sync_response(cover_letter_body)
    return cover_letter.model_dump()


def _sort_by_ids(projects: list[tuple[Project, Any]]|list[Project], llm_projects: list[RelevantProject]):
    if len(projects) ==0:
        return []
    if isinstance(projects[0], tuple):
        map_ = {item[0].id: item[0] for item in projects}
    else:
        map_ = {item.id: item for item in projects}
    sorted_projects = []
    for llm_project in llm_projects:
        project = map_.get(llm_project.id)
        if project is None:
            logger.warning(f"LLM returned unknown project id {llm_project.id}, skipping")
            continue
        sorted_projects.append(project)

    # optional: make sure any project the LLM forgot still gets included
    missing_ids = set(map_.keys()) - {p.id for p in sorted_projects}
    for missing_id in missing_ids:
        logger.warning(f"LLM omitted project id {missing_id}, appending at end")
        sorted_projects.append(map_[missing_id])

    return sorted_projects


def _sort_projects_llm(vacancy, technologies, relevant_projects):
    body = {
        "job_text":vacancy.job_text,
        "technologies":technologies,
        "projects":relevant_projects,
    }
    llm_sorted:RelevantProjects = relevant_projects_prompt.get_sync_response(body)
    
    return _sort_by_ids(relevant_projects,llm_sorted.projects)


@celery_app.task(
    bind=True,
    name="app.tasks.single_generation",
    queue="default",
)
def single_generation(self, vacancy_id:int,first_name:str,last_name:str,batch_id:str):
    logger.info(f"Starting generation id {vacancy_id}")
    set_cover_letter_task_status(batch_id, vacancy_id, "started")
    
    vacancy = auto_parsed_jobs_repo.get_by_id(vacancy_id)
    if vacancy is not None:
        user_id = vacancy.user_id
        prep_str = f"{vacancy.id} {vacancy.job_title} {vacancy.job_text}"
        try:
            parsed_json = job_parse_promt.get_sync_response({"job_text":prep_str})
            technologies:list = parsed_json.model_dump()["technologies"]
            technologies = [tech.lower() for tech in technologies]
            relevant_projects = project_repository.get_relevant(user_id ,technologies)
            
            if len(relevant_projects) == 0:
                logger.warning(f"Missed getting relevant projects vacancy_id {vacancy_id}\n Technologies:{technologies} \n fetching all projects by user")
                user_projects = project_repository.get_by_user(user_id)
                sorted_projects = _sort_projects_llm(vacancy, technologies, user_projects)
                
            if len(relevant_projects) > 2:
                sorted_projects = _sort_projects_llm(vacancy, technologies, relevant_projects)
                cover_letter = generate_cover_letter(
                    name=first_name,
                    last_name=last_name,
                    vacancy_name=vacancy.job_title,
                    vacancy_technologies=technologies,
                    vacancy_requirements=technologies,
                    projects=sorted_projects
                )
                print("Response",cover_letter)
                auto_parsed_jobs_repo.update_vacancy(vacancy_id,cover_letter['content'],is_generated=True)
                set_cover_letter_task_status(batch_id, vacancy_id, "generated")
                return
            else:   
                cover_letter = generate_cover_letter(
                    name=first_name,
                    last_name=last_name,
                    vacancy_name=vacancy.job_title,
                    vacancy_technologies=technologies,
                    vacancy_requirements=technologies,
                    projects=relevant_projects
                )
                print("Response",cover_letter)
                auto_parsed_jobs_repo.update_vacancy(vacancy_id,cover_letter['content'],is_generated=True)
                set_cover_letter_task_status(batch_id, vacancy_id, "generated")
                return
        except Exception as e:
            set_cover_letter_task_status(batch_id, vacancy_id, "failed")
            raise e
    else:
        logger.info(f"Generation job with id {vacancy_id} not found!")
