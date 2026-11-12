"""Genera el catálogo web a partir del mismo manual que se importa en el RAG."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "knowledge/manual_tecnicas_miniaturas.md"
OUTPUT = ROOT / "frontend/src/features/techniques/catalog.json"


def main() -> None:
    manifest = json.loads(MANUAL.with_suffix(".json").read_text(encoding="utf-8"))
    sections = re.split(r"(?m)^## ", MANUAL.read_text(encoding="utf-8"))[1:]
    techniques = []
    for section in sections:
        heading, body = section.strip().split("\n", 1)
        number, title = heading.split(". ", 1)
        if not 2 <= int(number) <= 23:
            continue
        level = re.search(r"\*\*Nivel:\*\* ([^.]+)\.", body)
        if level is None:
            raise ValueError(f"Falta nivel: {title}")
        difficulty = (
            "advanced"
            if "avanzado" in level[1]
            else "intermediate"
            if "intermedio" in level[1]
            else "beginner"
        )
        objective = re.search(r"\*\*Objetivo:\*\* (.*?) \*\*Nivel:", body)
        if objective is None:
            raise ValueError(f"Falta objetivo: {title}")
        blocks = []
        for chunk in re.split(r"\n\s*\n", body.strip()):
            lines = chunk.splitlines()
            if all(re.match(r"\d+\. ", line) for line in lines):
                blocks.append(
                    {
                        "type": "ordered",
                        "items": [re.sub(r"^\d+\. ", "", line) for line in lines],
                    }
                )
            elif all(line.startswith("- ") for line in lines):
                blocks.append(
                    {"type": "unordered", "items": [line[2:] for line in lines]}
                )
            else:
                blocks.append({"type": "paragraph", "text": " ".join(lines)})
        techniques.append(
            {
                "id": number,
                "title": title,
                "difficulty": difficulty,
                "summary": objective[1],
                "blocks": blocks,
            }
        )
    if len(techniques) != 22:
        raise ValueError("El manual debe contener las 22 técnicas previstas")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            {
                "title": manifest["title"],
                "version": manifest["version"],
                "reviewStatus": manifest["review_status"],
                "techniques": techniques,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Exportadas {len(techniques)} técnicas del manual v{manifest['version']}")


if __name__ == "__main__":
    main()
