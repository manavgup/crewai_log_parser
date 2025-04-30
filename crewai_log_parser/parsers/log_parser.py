from crewai_log_parser.models.parsed_block import ParsedBlock
from crewai_log_parser.utils.parsing_utils import extract_json_from_response, extract_datetime
from typing import List
from pathlib import Path

def parse_log_file(log_path: str) -> List[ParsedBlock]:
    lines = Path(log_path).read_text().splitlines()
    blocks = []
    current_block = None
    inside_request = inside_response = False

    for line in lines:
        if "Request to litellm:" in line:
            if current_block:
                blocks.append(current_block)
            current_block = ParsedBlock(
                task_hint='Unknown Task',
                litellm_request='',
                raw_response='',
                start_time=extract_datetime(line),
                end_time=None,
                parsed_usage={},
                model='unknown',
                thought='',
                action='',
                final_answer='',
                parsing_error=False
            )
            inside_request = True
            inside_response = False
            current_block.litellm_request += line + '\n'

        elif "RAW RESPONSE:" in line and current_block:
            inside_request = False
            inside_response = True
            current_block.raw_response += line + '\n'

        elif inside_request and current_block:
            current_block.litellm_request += line + '\n'
        elif inside_response and current_block:
            current_block.raw_response += line + '\n'

    if current_block:
        blocks.append(current_block)

    for block in blocks:
        parsed = extract_json_from_response(block.raw_response)
        if parsed:
            usage = parsed.get('usage', {})
            block.parsed_usage = usage
            block.model = parsed.get('model', 'unknown')
            message = parsed.get('choices', [{}])[0].get('message', {}).get('content', '')
            if message:
                block.thought = re.search(r"Thought:(.*?)\n", message, re.DOTALL).group(1).strip() if 'Thought:' in message else ''
                block.action = re.search(r"Action:(.*?)\n", message, re.DOTALL).group(1).strip() if 'Action:' in message else ''
                block.final_answer = re.search(r"Final Answer:(.*?)$", message, re.DOTALL).group(1).strip() if 'Final Answer:' in message else ''
        else:
            block.parsing_error = True

    return blocks