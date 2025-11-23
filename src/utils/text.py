import re


def extract_code_block(text: str) -> str | None:
    if "```" not in text:
        return None

    match = re.search(r"```(?:[a-zA-Z0-9_-]+)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    lines = text.splitlines()
    if len(lines) >= 2 and lines[0].strip().startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1])

    return None
