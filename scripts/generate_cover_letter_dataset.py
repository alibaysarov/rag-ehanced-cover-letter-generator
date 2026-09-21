"""Build a varied plain-text cover-letter SFT dataset from parsed jobs.

Every output is a regular Russian cover letter. No JSON, Markdown schema, or
invented achievements are included. The 500 source vacancies are each paired
with four different truthful subsets/orderings of the candidate's projects.
"""

from __future__ import annotations

import csv
import json
import re
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JOBS_PATH = ROOT / "datasets" / "auto_parsed_jobs_202609182333.csv"
PROJECTS_PATH = ROOT / "datasets" / "projects_202609150940.csv"
OUTPUT_PATH = ROOT / "datasets" / "cover_letter_dataset_2000.json"

INSTRUCTION = (
    "На основе текста вакансии и информации о проектах кандидата напиши "
    "персонализированное сопроводительное письмо на русском языке. "
    "Ответом должен быть только готовый текст письма без JSON, списков полей, "
    "разметки и служебных комментариев. Используй только факты из вакансии и "
    "проектов; не придумывай опыт, достижения, цифры или технологии."
)

STOP_WORDS = {
    "and", "api", "css", "html", "http", "javascript", "js", "sql",
    "the", "web", "в", "для", "и", "на", "опыт", "разработка", "с",
}

OPENINGS = [
    "Добрый день! Заинтересовала вакансия {title}.",
    "Здравствуйте! Хочу откликнуться на позицию {title}.",
    "Добрый день! Рассматриваю позицию {title} и вижу пересечение с моим опытом.",
    "Здравствуйте! Меня заинтересовала роль {title}.",
    "Добрый день! Откликаюсь на вакансию {title}.",
    "Здравствуйте! Хотел бы предложить свою кандидатуру на позицию {title}.",
    "Добрый день! Вакансия {title} соответствует направлению моего опыта.",
    "Здравствуйте! Обращаюсь по поводу позиции {title}.",
]

CLOSINGS = [
    "Буду рад подробнее обсудить задачи команды и свой релевантный опыт.",
    "Готов рассказать о проектах подробнее и обсудить, чем могу быть полезен команде.",
    "Буду рад продолжить разговор и ответить на вопросы по релевантным проектам.",
    "С удовольствием обсудю задачи позиции на собеседовании.",
    "Буду рад обсудить, как мой опыт может помочь в задачах этой вакансии.",
    "Готов подробнее рассказать о применённых в проектах технологиях и задачах.",
    "Буду рад знакомству и предметному разговору о задачах команды.",
    "Буду рад обсудить, какие из моих проектов могут быть полезны вашей команде.",
]

BRIDGES = [
    "В описании вашей вакансии я увидел задачи и технологии, которые пересекаются с проектами из моего портфолио.",
    "Для этой позиции могу привести несколько релевантных примеров из портфолио.",
    "Меня привлекает практический характер задач, поэтому особенно внимательно сопоставил вакансию со своими проектами.",
    "Сфера и технологический контекст вакансии близки к направлениям, с которыми я уже работал в проектах.",
    "Ниже приведу проекты, которые могут быть наиболее полезны в контексте этой роли.",
    "Считаю, что у меня есть опыт, релевантный для задач, описанных в вашей вакансии.",
    "Хочу применить накопленный проектный опыт в вашей компании и быть полезным в задачах этой позиции.",
    
]

PROJECT_LEADS = [
    "В портфолио представлены следующие проекты:",
    "",
    "Среди проектов хотел бы выделить:",
    "Мой проектный опыт включает:",
    "В качестве примеров могу указать:",
    "Наиболее близкими по контексту выглядят проекты:",
    "Среди работ в портфолио есть:",
    "Для этой роли могут быть интересны следующие проекты:",
]


def tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[a-zа-яё][a-zа-яё0-9.+/#-]{1,}", text, flags=re.I)
        if token.lower() not in STOP_WORDS
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def project_text(project: dict[str, str]) -> str:
    technologies = project["technologies"].strip("{}").replace('"', "")
    return f"{project['name']}: {technologies}"


def technologies(project: dict[str, str]) -> list[str]:
    return [item.strip().replace('"', "") for item in project["technologies"].strip("{}").split(",") if item.strip()]


def matching_technologies(job: dict[str, str], projects: list[dict[str, str]]) -> list[str]:
    job_words = tokens(f"{job['job_title']} {job['job_text']}")
    matches: list[str] = []
    for project in projects:
        for technology in technologies(project):
            tech_words = tokens(technology)
            if tech_words and tech_words <= job_words and technology not in matches:
                matches.append(technology)
    return matches[:4]


def select_projects(job: dict[str, str], projects: list[dict[str, str]], variant: int) -> list[dict[str, str]]:
    job_tokens = tokens(f"{job['job_title']} {job['job_text']}")
    ranked = sorted(
        projects,
        key=lambda project: len(job_tokens & tokens(f"{project['name']} {project['technologies']}")),
        reverse=True,
    )
    # Rotate equally relevant choices; outputs remain limited to real projects.
    offset = variant % len(ranked)
    rotated = ranked[offset:] + ranked[:offset]
    return rotated[:3]


def make_letter(job: dict[str, str], projects: list[dict[str, str]], variant: int) -> str:
    descriptions = [f"«{project['name']}» — {', '.join(technologies(project))}" for project in projects]
    intro = OPENINGS[variant % len(OPENINGS)].format(title=job["job_title"])
    style = variant % 8
    bridge = BRIDGES[style]
    project_lead = PROJECT_LEADS[style]
    overlap = matching_technologies(job, projects)
    overlap_sentence = (
        f"Стек: {', '.join(overlap)}."
        if overlap
        else "Проекты помогают предметно обсудить, какие задачи и технологии могут быть релевантны позиции."
    )

    if style == 0:
        project_block = "Среди них: " + "; ".join(descriptions) + "."
    elif style == 1:
        project_block = "; ".join(descriptions) + "."
    elif style == 2:
        project_block = f"{descriptions[0]}. Также в портфолио есть {', '.join(descriptions[1:])}."
    elif style == 3:
        project_block = f"Один из примеров — {descriptions[0]}. Другие проекты в портфолио: {', '.join(descriptions[1:])}."
    elif style == 4:
        project_block = f"{descriptions[0]}. В портфолио представлены и другие проекты: {', '.join(descriptions[1:])}."
    elif style == 5:
        project_block = "; ".join(f"проект {description}" for description in descriptions) + "."
    elif style == 6:
        project_block = f"В первую очередь — {descriptions[0]}. Кроме него, в портфолио есть {', '.join(descriptions[1:])}."
    else:
        project_block = "\n".join(f"{description}." for description in descriptions)

    paragraphs = [intro, bridge, project_lead, project_block, overlap_sentence, CLOSINGS[style]]
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", type=Path, default=JOBS_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--variants", type=int, default=4)
    parser.add_argument("--total", type=int)
    args = parser.parse_args()
    if args.variants < 1:
        raise ValueError("--variants must be at least 1")

    jobs = read_csv(args.jobs)
    projects = read_csv(PROJECTS_PATH)

    total = args.total or len(jobs) * args.variants
    if total < len(jobs):
        raise ValueError("--total cannot be smaller than the number of jobs")
    base_variants, extra_variants = divmod(total, len(jobs))

    dataset: list[dict[str, str]] = []
    for job_index, job in enumerate(jobs):
        variants_for_job = base_variants + (1 if job_index < extra_variants else 0)
        for variant in range(variants_for_job):
            selected = select_projects(job, projects, variant)
            input_text = "\n\n".join(
                [
                    f"job_title: {job['job_title']}",
                    f"job_text: {job['job_text'].strip()}",
                    "projects:\n" + "\n".join(f"- {project_text(project)}" for project in selected),
                ]
            )
            dataset.append(
                {
                    "instruction": INSTRUCTION,
                    "input": input_text,
                    "output": make_letter(job, selected, variant),
                }
            )

    if len(dataset) != total:
        raise AssertionError(f"Expected {total} records, got {len(dataset)}")
    if any(item["output"].lstrip().startswith(("{", "[")) for item in dataset):
        raise AssertionError("Output must be plain text, not JSON")

    args.output.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(dataset)} examples to {args.output}")


if __name__ == "__main__":
    main()
