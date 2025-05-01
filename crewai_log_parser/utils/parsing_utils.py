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

def extract_tool_name(raw_line: str) -> str:
    """
    Extract the tool name from a line like:
    'Tool: Repository Analyzer\\nAction Input: {....}'
    
    Keeps only the clean tool name.
    """
    # First, make sure it starts with 'Tool: '
    if not raw_line.startswith("Tool: "):
        return raw_line.split("\\nAction Input")[0].strip()
    
    # Remove 'Tool: ' prefix
    trimmed = raw_line[len("Tool: "):]
    
    # Now split at the first '\nAction Input'
    if "\\nAction Input" in trimmed:
        trimmed = trimmed.split("\\nAction Input")[0]
    
    return trimmed.strip()
