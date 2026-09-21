"""Deterministic, dependency-free Russian cover-letter templates."""

import re
from dataclasses import dataclass
from typing import Sequence

OPENINGS = (
    "Добрый день! Заинтересовала вакансия {title}.",
    "Здравствуйте! Хочу откликнуться на вакансию {title}.",
    "Здравствуйте! Меня заинтересовала позиция {title}.",
)
CLOSINGS = (
    "Буду рад подробнее обсудить задачи команды и свой релевантный опыт.",
    "Буду рад обсудить, чем мои проекты могут быть полезны вашей команде.",
    "Заранее спасибо.",
)
PROJECT_LEADS = (
    "В портфолио представлены следующие проекты:",
    "Ниже несколько проектов из портфолио:",
    "Хочу привести примеры проектов:",
    "Вот проекты, близкие по используемым технологиям:",
    "В качестве примеров могу выделить следующие проекты:",
    "Мой опыт представлен в следующих проектах:",
    "Ниже перечислены проекты из портфолио:",
    "Проекты, которые могут быть полезны в контексте позиции:",
)
NEUTRAL_PROJECT_LEADS = (
    "В портфолио представлены следующие проекты:",
    "Ниже приведены проекты, которые могут быть полезны в контексте этой роли:",
)
BRIDGES = (
    "Ниже приведу проекты, которые могут быть полезны в контексте этой роли.",
    "Я использовал технологии которые применяются у вас.",
    "Хочу показать несколько релевантных примеров из портфолио.",
    "Ниже — проекты, которые помогут предметно обсудить мой опыт.",
    "Поделюсь проектами, связанными с указанным технологическим стеком.",
    "Вот несколько примеров практической работы с нужными технологиями.",
    "Приведу проекты, которые могут быть интересны вашей команде.",
)
NEUTRAL_BRIDGES = (
    "Ниже приведу проекты, которые могут быть полезны в контексте этой роли.",
    "Хочу показать несколько проектов из своего портфолио.",
)
NEUTRAL_STACK = "Проекты помогают предметно обсудить, какие задачи и технологии могут быть релевантны позиции."


@dataclass(frozen=True)
class TemplateProject:
    id: int
    name: str
    technologies: tuple[str, ...]


def _unique_technologies(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def _technology_pattern(technology: str) -> re.Pattern[str]:
    # A non-word boundary is important for C++, C#, .NET and Node.js.
    escaped = re.escape(" ".join(technology.split()))
    return re.compile(r"(?<![\w+#.])" + escaped + r"(?![\w+#.])", re.IGNORECASE)


def matching_technologies(vacancy_text: str, technologies: Sequence[str]) -> list[str]:
    """Return at most four declared technologies found as complete technical names."""
    result: list[str] = []
    for technology in _unique_technologies(technologies):
        if _technology_pattern(technology).search(vacancy_text):
            result.append(technology)
            if len(result) == 4:
                break
    return result


def generate_template_cover_letter(
    *,
    vacancy_id: int,
    job_title: str,
    job_text: str,
    projects: Sequence[TemplateProject],
) -> str:
    variant = vacancy_id
    clean_projects: list[TemplateProject] = []
    seen_ids: set[int] = set()
    for project in projects:
        if project.id in seen_ids or not project.name.strip():
            continue
        seen_ids.add(project.id)
        clean_projects.append(
            TemplateProject(
                project.id,
                project.name.strip(),
                tuple(_unique_technologies(project.technologies)),
            )
        )
        if len(clean_projects) == 3:
            break

    title = job_title.strip()
    opening = (
        OPENINGS[variant % len(OPENINGS)].format(title=title)
        if title
        else "Здравствуйте! Хочу откликнуться на вашу вакансию."
    )
    blocks = [opening]
    if clean_projects:
        all_tech = [tech for project in clean_projects for tech in project.technologies]
        matches = matching_technologies(f"{job_title}\n{job_text}", all_tech)
        bridge_source = BRIDGES if matches else NEUTRAL_BRIDGES
        lead_source = PROJECT_LEADS if matches else NEUTRAL_PROJECT_LEADS
        blocks.append(bridge_source[variant % len(bridge_source)])
        blocks.append(lead_source[variant % len(lead_source)])
        lines = []
        for project in clean_projects:
            suffix = (
                f" — {', '.join(project.technologies)}" if project.technologies else ""
            )
            lines.append(f"«{project.name}»{suffix}.")
        blocks.append("\n".join(lines))
        blocks.append(f"Стек: {', '.join(matches)}." if matches else NEUTRAL_STACK)
    blocks.append(CLOSINGS[variant % len(CLOSINGS)])
    return "\n\n".join(block for block in blocks if block)
