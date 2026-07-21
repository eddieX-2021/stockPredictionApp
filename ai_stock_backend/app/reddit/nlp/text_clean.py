import re

_url = re.compile(r"https?://\S+")
_ws = re.compile(r"\s+")

def clean_text(text: str) -> str:
    if not text:
        return ""
    t = text
    t = _url.sub(" ", t)
    t = t.replace("\n", " ").replace("\r", " ")
    t = _ws.sub(" ", t).strip()
    return t
