from itertools import chain

from app.decorators.time_perf import time_performance
from app.repository import ProjectRepository
from app.repository.auto_parse_job_repository import AutoParseJobRepository
from app.services.llm.job_requirements import JobParsePrompt
from app.services.llm.relevant_projects import RelevantProjectsPrompt

job_parse_promt = JobParsePrompt()

relevant_projects_llm = RelevantProjectsPrompt()

auto_parse_job_repository = AutoParseJobRepository()
project_repository = ProjectRepository()


def flatten_list(arr: list) -> list:
    return list(chain.from_iterable(arr))


def get_chunks(data, n: int = 3):
    chunks = [data[i : i + n] for i in range(0, len(data), n)]
    return chunks


@time_performance
def batch_generate(job_id):
    vacancies = auto_parse_job_repository.get_by_job_id(job_id)
    vacancies_chunks = get_chunks(vacancies[0:20])

    job_requirements = []

    for chunk in vacancies_chunks:
        messages = [
            job_parse_promt.prompt_template.invoke(
                {"job_text": f"{item[0]} {item[1]} {item[2]}"}
            )
            for item in chunk
        ]
        items = job_parse_promt.get_model.batch(messages, config={"max_concurrency": 4})
        job_requirements.extend(items)

    vacancy_data = [
        {"id": i.id, "name": i.name, "technologies": i.technologies}
        for i in job_requirements
    ]

    print("job_requirements\n", vacancy_data)

    relevant_batches = []
    # hits = 0
    # empty = 0
    # for job_requirement in job_requirements:
    #     project_list = project_repository.get_relevant(user_id=1,techs=job_requirement.technologies)
    #     vacancy = next((x for x in vacancies if x[0]== job_requirement.id), None)
    #     if len(project_list):
    #         print("data",job_requirement.id,job_requirement.name, project_list)
    #         hits+=1
    #     else:
    #         empty+=1
    #         print("empty",job_requirement.id,job_requirement.name)
    # if vacancy:
    #     body = {
    #         "projects":project_list,
    #         "job_text":vacancy[2],
    #         "technologies": job_requirement.technologies
    #     }

    #     # relevant_batches.extend(relevant_projects_llm.prompt_template.invoke(body))
    #     relevant_batches.append(
    #         relevant_projects_llm.prompt_template.invoke(body)
    #     )
    # print(f"Hits: {hits}, Empty: {empty}")
    # sorted_projects = relevant_projects_llm.get_model.batch(relevant_batches,config={
    #         "max_concurrency": 4
    # })
    # print("sorted_projects\n",sorted_projects)


batch_generate(4)
