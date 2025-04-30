import json
import re
from typing import Optional

def safe_json_loads(text: str) -> Optional[dict]:
    try:
        return json.loads(text)
    except Exception:
        return None

def extract_json_from_response(response: str) -> Optional[dict]:
    if 'RAW RESPONSE:' in response:
        split = response.split('RAW RESPONSE:', 1)[-1]
        idx = split.find('{')
        if idx >= 0:
            raw_json = split[idx:].strip()
            return safe_json_loads(raw_json)
    return None

def extract_datetime(line: str) -> Optional[str]:
    match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
    if match:
        return match.group(1)
    return None