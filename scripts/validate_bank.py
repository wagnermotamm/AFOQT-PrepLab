"""Check data/questions.json before the trainer loads it."""

import json
import sys
from pathlib import Path


def validate(bank):
    if not isinstance(bank, dict) or not isinstance(bank.get("themes"), list) or not isinstance(bank.get("questions"), list):
        return ["banco incompleto"]
    themes = {theme.get("id") for theme in bank["themes"]}
    seen = set()
    errors = []
    for question in bank["questions"]:
        qid = question.get("id")
        if qid in seen:
            errors.append(f"id repetido: {qid}")
        seen.add(qid)
        if question.get("theme") not in themes:
            errors.append(f"tema invalido: {qid}")
        options = question.get("options")
        if not isinstance(options, list) or len(options) < 2:
            errors.append(f"opcoes invalidas: {qid}")
            continue
        ids = [option.get("id") for option in options if isinstance(option, dict)]
        if question.get("correct") not in ids:
            errors.append(f"gabarito invalido: {qid}")
        if question.get("usesTable"):
            table = bank.get("table") or {}
            xs = table.get("x")
            rows = table.get("rows")
            if not isinstance(xs, list) or not isinstance(rows, list):
                errors.append(f"tabela ausente: {qid}")
                continue
            col = xs.index(question.get("x")) if question.get("x") in xs else -1
            row = next((item for item in rows if item.get("y") == question.get("y")), None)
            value = str(row["cells"][col]) if row and col >= 0 else ""
            correct = next((option for option in options if option.get("id") == question.get("correct")), None)
            if not correct or correct.get("text") != value:
                errors.append(f"tabela divergente: {qid}")
    return errors


def main():
    path = Path(__file__).resolve().parents[1] / "data" / "questions.json"
    bank = json.loads(path.read_text(encoding="utf-8"))
    errors = validate(bank)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"ok: {len(bank['questions'])} questions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
