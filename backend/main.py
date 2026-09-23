import uvicorn


def cover_template_test(): ...


def main():
    """Main entry point for the application"""
    print("Starting Cover Letter RAG Backend...")

    # Run the FastAPI application
    uvicorn.run(
        "app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )


# TODO: сделать UI обертку над ф-иями bs4 find_all,find и тд
def test_req():
    import httpx
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    url = "https://hh.ru/search/vacancy?text=PHP+%D1%80%D0%B0%D0%B7%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D1%87%D0%B8%D0%BA&area=1&suggestId=fc5d7a2a-8945-4bd7-8d3d-94372ab9a25d&hhtmFrom=main&hhtmFromLabel=vacancy_search_line"
    with httpx.Client(follow_redirects=True, timeout=15) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        elements = soup.find_all(attrs={"data-qa": "serp-item__title-text"})
        names = [el.text for el in elements]
        print(names)

    print("123")


if __name__ == "__main__":
    # test_req()
    main()
