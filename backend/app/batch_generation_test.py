from app.services.llm.job_items import CoverLetterPrompt

from app.decorators.time_perf import time_performance
import os
import json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
test_file_path = os.path.join(BASE_DIR, "vacancy_dataset.json")

llm = CoverLetterPrompt()

"""
n=10 - 21c
n=30
"""


def get_chunks(data,n:int=3):
    chunks = [data[i : i + n] for i in range(0, len(data), n)]
    return chunks

@time_performance
def main():
    data = None
    with open(test_file_path, "r", encoding="utf-8") as file:
        data = json.load(file)


    if data is not None:
        result = []
        data = data[0:20]
        data_chunks = get_chunks(data)
        for chunk in data_chunks:
            messages = [
                llm.prompt_template.invoke(item)
                for item in chunk
            ]
            items = llm.get_model.batch(messages,config={
                "max_concurrency": 4
            })
            result.append(items)
        print("RESULT\n",len(data), result)


@time_performance
def loop():
    data = None
    with open(test_file_path, "r", encoding="utf-8") as file:
        data = json.load(file)


    if data is not None:
        result = []
        data = data
        for item in data:
            response = llm.get_sync_response(item)
            result.append(response)
        
        print("RESULT\n",len(data), result)

# loop()
main()