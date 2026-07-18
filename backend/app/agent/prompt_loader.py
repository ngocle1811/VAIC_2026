from pathlib import Path

PROMPT_DIR = Path(__file__).with_name("prompts")


def load_prompt(name: str) -> str:
    path = (PROMPT_DIR / name).resolve()
    if PROMPT_DIR.resolve() not in path.parents:
        raise ValueError("Prompt path escapes prompt directory")
    return path.read_text(encoding="utf-8")
