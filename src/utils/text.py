import re


def extract_code_block(text: str) -> str | None:
    if "```" not in text:
        return None
    match = re.search(r"```(?:[a-zA-Z0-9_-]+)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1)
    return None
