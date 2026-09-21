"""Versioned default phrases and graph layouts for newly provisioned users."""

DEFAULT_TEMPLATE_SEED_VERSION = 1

DEFAULT_TEMPLATE_SEEDS = {
    "no_portfolio": {
        "name": "Портфолио пусто",
        "blocks": [
            ("opening", "Добрый день! Меня заинтересовала вакансия [[job_title]]."),
            ("closing", "Буду рад подробнее обсудить задачи команды и свой опыт."),
        ],
    },
    "relevant_domain": {
        "name": "Есть релевантная сфера",
        "blocks": [
            ("opening", "Добрый день! Меня заинтересовала вакансия [[job_title]]."),
            (
                "experience_bridge",
                "Я использовал технологии, которые применяются у вас: [[matched_technologies]].",
            ),
            ("portfolio_intro", "Хочу привести релевантные примеры из портфолио:"),
            ("projects", None),
            ("closing", "Буду рад подробнее обсудить задачи команды и свой опыт."),
        ],
    },
    "partial_match": {
        "name": "Частичное совпадение",
        "blocks": [
            ("opening", "Здравствуйте! Хочу откликнуться на вакансию [[job_title]]."),
            (
                "experience_bridge",
                "В моих проектах использовалась технология [[matched_technologies]].",
            ),
            ("portfolio_intro", "Ниже несколько примеров из портфолио:"),
            ("projects", None),
            ("closing", "Буду рад обсудить, чем мой опыт полезен вашей команде."),
        ],
    },
    "no_relevant_projects": {
        "name": "Проекты есть, но релевантных нет",
        "blocks": [
            ("opening", "Здравствуйте! Меня заинтересовала позиция [[job_title]]."),
            (
                "experience_bridge",
                "Ниже приведу проекты, которые показывают мой практический опыт.",
            ),
            ("portfolio_intro", "В портфолио представлены следующие проекты:"),
            ("projects", None),
            ("closing", "Буду рад подробнее обсудить задачи команды и свой опыт."),
        ],
    },
}
