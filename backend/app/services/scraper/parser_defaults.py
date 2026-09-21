HH_LIST_JS = r"""
        
            () => [...document.querySelectorAll('[data-qa^=vacancy-serp__vacancy]')]
                    .map(v => {
                        const title = v.querySelector('[data-qa=serp-item__title-text]')?.textContent || null;
                        
                        const link = v.querySelector('a')?.href || null;
                        const vacancy_id = link?.match(/\/vacancy\/(\d+)/)?.[1] || null;

                        return { title, link, vacancy_id };
                    })
                    .filter(({ title, vacancy_id, link }) => title && vacancy_id && link)
        """

HH_PAGE_JS = """
        ()=>{
            const job_title = document.querySelector('[data-qa="vacancy-title"]')?.textContent?.trim() || '';
            const job_text = document.querySelector('[data-qa="vacancy-description"]')?.textContent?.trim() || '';
            const company_name = document.querySelector('[data-qa="vacancy-company-name"]')?.textContent?.trim() || null;
            return {
                job_title,
                job_text,
                company_name,
            }
        }
        """

PAGINATION_JS = """
        () => [...document.querySelectorAll('[data-qa="pager-page"]')]
                .map(item => item.textContent?.trim() || null)
                .filter(v => v != null)
        """

GEEKJOB_LIST_JS = r"""
            () => [...document.querySelectorAll('ul.collection.serp-list li')]
                    .map(v => {
                        const elem = v.querySelector('p.truncate.vacancy-name a')
                        const title = elem?.textContent || null;
                        const link = elem?.href || null;
                        const vacancy_id = link?.match(/\/vacancy\/([^/?#]+)/)?.[1] || null;

                        return { title, link, vacancy_id };
                    })
                    .filter(({ title, vacancy_id, link }) => title && vacancy_id && link)
        """

GEEKJOB_PAGE_JS = """
        ()=>{
            const job_title = (
                document.querySelector('h1')?.textContent?.trim() ||
                document.querySelector('main h1')?.textContent?.trim() ||
                ''
            );

            const job_text = (
                document.querySelector('article')?.textContent?.trim() ||
                document.querySelector('[class*="description"]')?.textContent?.trim() ||
                document.body?.textContent?.trim() ||
                ''
            );

            const company_name = (
                document.querySelector('[class*="company"] a')?.textContent?.trim() ||
                document.querySelector('[class*="company"]')?.textContent?.trim() ||
                null
            );

            return {
                job_title,
                job_text,
                company_name,
            }
        }
        """


def default_parser_values(user_id: int) -> list[dict]:
    common = {"user_id": user_id, "pagination_start": 0, "max_pages": 5}
    return [
        {
            **common,
            "name": "hh.ru",
            "site_key": "hh.ru",
            "base_url": "https://hh.ru/search/vacancy",
            "single_url": "https://hh.ru/vacancy/{vacancy_id}",
            "has_pagination": True,
            "evaluate_vacancy_list": HH_LIST_JS,
            "evaluate_vacancy_page": HH_PAGE_JS,
            "evaluate_pagination": PAGINATION_JS,
            "format_url": {
                "url_template": "{base_url}",
                "query_params": {"text": "{text}", "page": "{page}"},
            },
        },
        {
            **common,
            "name": "geekjob.ru",
            "site_key": "geekjob.ru",
            "base_url": "https://geekjob.ru/vacancies",
            "single_url": "https://geekjob.ru/vacancy/{vacancy_id}",
            "has_pagination": False,
            "evaluate_vacancy_list": GEEKJOB_LIST_JS,
            "evaluate_vacancy_page": GEEKJOB_PAGE_JS,
            "evaluate_pagination": PAGINATION_JS,
            "format_url": {
                "url_template": "{base_url}",
                "query_params": {"qs": "{text}", "page": "{page}"},
            },
        },
    ]
