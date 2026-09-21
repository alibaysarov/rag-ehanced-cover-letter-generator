"""Rewrite SFT outputs into natural plain-text cover letters using local Ollama.

The script checkpoints every completed record, so it can be safely resumed.
It sends only the already-present instruction and source facts to a local model.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "datasets" / "cover_letter_dataset_3000.json"
DEFAULT_OUTPUT = ROOT / "datasets" / "cover_letter_dataset_3000_humanized.json"


def generate(model: str, instruction: str, source: str) -> str:
    prompt = f"""{instruction}

Данные вакансии и кандидата:
{source}

Напиши одно естественное сопроводительное письмо на русском языке длиной 75–120 слов.
Начни с приветствия, но не называй кандидата по имени. Указывай технологии кандидата только если они явно есть в блоке projects.
В projects перечислены лишь название и стек, поэтому нельзя писать, что кандидат что-либо реализовал, внедрил, оптимизировал,
руководил, поддерживал или достиг результата. Можно нейтрально написать: «в портфолио есть проект ... со стеком ...».
Требования вакансии не доказывают опыт кандидата: их можно упомянуть лишь как интересные задачи.
Не используй JSON, Markdown, списки, заголовки, поле `output`, рассуждения или объяснения.
Не повторяй текст вакансии и не добавляй непроверяемые достижения, уровни опыта или качества работы. Верни только письмо."""
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {"temperature": 0.85, "top_p": 0.92, "num_predict": 240},
        }
    ).encode()
    request = Request("http://127.0.0.1:11434/api/generate", data=payload, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=300) as response:
        result = json.loads(response.read().decode())
    return result["response"].strip()


def valid_letter(text: str) -> bool:
    forbidden = ("{", "[", "```", "\"output\"", "<think>")
    words = text.split()
    return 55 <= len(words) <= 230 and not any(marker in text.lower() for marker in forbidden)


def save(path: Path, records: list[dict[str, str]]) -> None:
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default="qwen3.5:4b")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--checkpoint-every", type=int, default=10)
    args = parser.parse_args()

    source_records = json.loads(args.source.read_text(encoding="utf-8"))
    records = json.loads(args.output.read_text(encoding="utf-8")) if args.output.exists() else []
    if records and [record["input"] for record in records] != [record["input"] for record in source_records[: len(records)]]:
        raise ValueError("Checkpoint does not match the source dataset")

    stop_at = min(len(source_records), args.limit) if args.limit else len(source_records)
    for index in range(len(records), stop_at):
        record = source_records[index]
        for attempt in range(3):
            letter = generate(args.model, record["instruction"], record["input"])
            if valid_letter(letter):
                records.append({**record, "output": letter})
                break
            if attempt == 2:
                raise ValueError(f"Invalid model response at record {index}: {letter[:200]!r}")
        if (index + 1) % args.checkpoint_every == 0:
            save(args.output, records)
            print(f"Completed {index + 1}/{stop_at}", flush=True)
        time.sleep(0.05)

    save(args.output, records)
    print(f"Saved {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()
