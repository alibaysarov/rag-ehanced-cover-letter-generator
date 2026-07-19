from app.services.scraper.parsers.general import GeneralVacancyParser
from urllib.parse import urlencode


class HHVacancyParser(GeneralVacancyParser):
    def __init__(self):
        super().__init__("hh.ru","https://hh.ru/search/vacancy", True)
    
    def get_single_url(self,vacancy_id)->str:
        return f"https://hh.ru/vacancy/{vacancy_id}"
    
    def evaluate_vacancy_list(self)->str:
        return """
        
            () => [...document.querySelectorAll('[data-qa^=vacancy-serp__vacancy]')]
                    .map(v => {
                        const title = v.querySelector('[data-qa=serp-item__title-text]')?.textContent || null;
                        
                        const link = v.querySelector('a')?.href || null;
                        const vacancy_id = link?.match(/\/vacancy\/(\d+)/)?.[1] || null;

                        return { title, link, vacancy_id };
                    })
                    .filter(({ title, vacancy_id, link }) => title && vacancy_id && link)
        """
    
    def evaluate_vacancy_page(self):
        return """
        ()=>{
            const job_title = document.querySelector('[data-qa="vacancy-title"]')?.textContent?.trim() || null;
            const job_text = document.querySelector('[data-qa="vacancy-description"]')?.textContent?.trim() || null;
            return {
                job_title,
                job_text,
            }
        }
        """
    
    def evaluate_pagination(self)->str:
        return """
        () => [...document.querySelectorAll('[data-qa="pager-page"]')]
                .map(item => item.textContent?.trim() || null)
                .filter(v => v != null)
        """
    
    
    def format_url(self, url: str, **kwargs) -> str:
        q_params = {
            "text": kwargs["text"],
        }
        if "page" in kwargs:
            q_params["page"] = kwargs["page"]
        return f"{url}?{urlencode(q_params)}"
    
    
        