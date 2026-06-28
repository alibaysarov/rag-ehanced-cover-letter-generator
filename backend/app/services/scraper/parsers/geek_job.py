from app.services.scraper.parsers.general import GeneralVacancyParser
from urllib.parse import urlencode


class GeekJobVacancyParser(GeneralVacancyParser):
    def __init__(self):
        super().__init__("geek_job","https://geekjob.ru/vacancies", False)
    
    def get_single_url(self)->str:
        return "https://geekjob.ru/vacancy/{vacancy_id}"
    
    def evaluate_pagination(self)->str:
        return """
        () => [...document.querySelectorAll('[data-qa="pager-page"]')]
                .map(item => item.textContent?.trim() || null)
                .filter(v => v != null)
        """
    
    
    def format_url(self, url: str, **kwargs) -> str:
        q_params = {
            "qs": kwargs["text"],
        }
        if "page" in kwargs:
            q_params["page"] = kwargs["page"]
        return f"{url}?{urlencode(q_params)}"
    
    def evaluate_vacancy_list(self)->str:
        return """
        
            () => [...document.querySelectorAll('ul.collection.serp-list li')]
                    .map(v => {
                        const elem = v.querySelector('p.truncate.vacancy-name a')
                        const title = elem?.textContent || null;
                        
                        const link = elem?.href || null;
                        const vacancy_id = link?.match(/\/vacancy\/(\d+)/)?.[1] || null;

                        return { title, link, vacancy_id };
                    })
                    .filter(({ title, vacancy_id, link }) => title && vacancy_id && link)
        """