import re
import json
from pathlib import Path
from typing import List, Dict, Tuple
import os

def extract_task_hint(litellm_request: str) -> str:
    """Extract the task hint from the litellm request text.
    
    This function uses multiple approaches to find the task hint in the request text,
    handling different formats and patterns.
    
    Args:
        litellm_request: The raw litellm request text
        
    Returns:
        The extracted task hint or 'Unknown Task' if not found
    """
    import re
    
    # Try the most common pattern first: "Current Task: task_text"
    task_match = re.search(r"Current Task: (.*?)(?:\n|$)", litellm_request, re.DOTALL)
    if task_match:
        return task_match.group(1).strip()
    
    # Try alternate format: Sometimes task is after the messages: section
    messages_match = re.search(r"messages=(\[.*\])", litellm_request, re.DOTALL)
    if messages_match:
        messages_text = messages_match.group(1)
        # Look for content fields in the messages
        content_match = re.search(r'"content":\s*"([^"]*)"', messages_text)
        if content_match:
            content = content_match.group(1)
            # See if there's a task description in the content
            task_in_content = re.search(r"Task:(.*?)(?:\\n|$)", content, re.DOTALL)
            if task_in_content:
                return task_in_content.group(1).strip()
    
    # Try to find any labeled task
    alt_task_match = re.search(r"[Tt]ask:?\s+(.*?)(?:\n|$)", litellm_request, re.DOTALL)
    if alt_task_match:
        return alt_task_match.group(1).strip()
    
    # Last resort: Try to find anything that looks like a task description
    for line in litellm_request.split('\n'):
        # Look for lines that start with verbs like "Analyze," "Calculate," etc.
        if re.match(r"^\s*(?:Analyze|Calculate|Process|Generate|Create|Determine|Evaluate|Find|Identify|Extract)\s", line):
            return line.strip()
    
    # If all else fails
    return "Unknown Task"

def extract_token_usage(raw_text: str) -> Dict:
    """Extract token usage information with multiple approaches."""
    # First look for the standard usage format
    usage_match = re.search(r'"usage":\s*({[^}]*"prompt_tokens":[^}]*"completion_tokens":[^}]*"total_tokens":[^}]*})', raw_text, re.DOTALL)
    if usage_match:
        try:
            usage_json = "{" + usage_match.group(0) + "}"
            parsed = json.loads(usage_json)
            return parsed.get('usage', {})
        except:
            pass
    
    # Try direct regex extraction
    prompt_match = re.search(r'"prompt_tokens":\s*(\d+)', raw_text)
    completion_match = re.search(r'"completion_tokens":\s*(\d+)', raw_text)
    total_match = re.search(r'"total_tokens":\s*(\d+)', raw_text)
    
    if prompt_match and completion_match and total_match:
        return {
            'prompt_tokens': int(prompt_match.group(1)),
            'completion_tokens': int(completion_match.group(1)),
            'total_tokens': int(total_match.group(1))
        }
    
    # Try line-by-line approach
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    
    for line in raw_text.split('\n'):
        if '"prompt_tokens"' in line:
            match = re.search(r'\d+', line)
            if match:
                prompt_tokens = int(match.group(0))
        
        if '"completion_tokens"' in line:
            match = re.search(r'\d+', line)
            if match:
                completion_tokens = int(match.group(0))
        
        if '"total_tokens"' in line:
            match = re.search(r'\d+', line)
            if match:
                total_tokens = int(match.group(0))
    
    if prompt_tokens or completion_tokens or total_tokens:
        # Calculate any missing values
        if not total_tokens and (prompt_tokens and completion_tokens):
            total_tokens = prompt_tokens + completion_tokens
        
        return {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens
        }
    
    return {}

def extract_model_name(text: str) -> str:
    """Extract the model name from the text."""
    patterns = [
        r'model="([^"]+)"',
        r"model='([^']+)'",
        r'model=([a-zA-Z0-9\-\.]+)',
        r'"model":\s*"([^"]+)"'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return "unknown"

def slugify_filename(text: str) -> str:
    """Create a filesystem-safe filename from task hint."""
    if not text or text == "Unknown Task":
        return "unknown_task"
    return re.sub(r'[^a-zA-Z0-9_-]', '_', text)[:80]

def parse_log_file_v2(log_path: str, verbose=False) -> Tuple[List[Dict], List[Dict]]:
    """Parse CrewAI log file into structured LLM call blocks and token usage."""
    lines = Path(log_path).read_text().splitlines()
    blocks = []
    token_usage_info = []
    current_block = None
    inside_request = inside_response = False

    for idx, line in enumerate(lines):
        if "Request to litellm:" in line:
            # Get timestamp if available
            timestamp = None
            timestamp_match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
            if timestamp_match:
                timestamp = timestamp_match.group(1)
            
            if current_block:
                blocks.append(current_block)
            current_block = {
                'task_hint': '',
                'litellm_request': '',
                'raw_response': '',
                'thought': '',
                'action': '',
                'final_answer': '',
                'parsed_usage': {},
                'parsing_error': False,
                'start_time': timestamp,
                'end_time': None,
                'model': None,
                'api_errors': []
            }
            inside_request = True
            inside_response = False
            current_block['litellm_request'] += line + '\n'
        elif "RAW RESPONSE:" in line and current_block:
            inside_response = True
            inside_request = False
            current_block['raw_response'] += line + '\n'
        elif "APIStatusError" in line and current_block:
            current_block['api_errors'].append(line.strip())
        else:
            if inside_request and current_block:
                current_block['litellm_request'] += line + '\n'
            if inside_response and current_block:
                current_block['raw_response'] += line + '\n'

    if current_block:
        blocks.append(current_block)

    # Extract information from each block
    for idx, block in enumerate(blocks):
        # Extract task hint using the dedicated function
        block['task_hint'] = extract_task_hint(block['litellm_request'])
        
        # Extract model information
        block['model'] = extract_model_name(block['litellm_request'])
        if block['model'] == "unknown":
            # Try finding in response if not found in request
            model_in_resp = extract_model_name(block['raw_response'])
            if model_in_resp != "unknown":
                block['model'] = model_in_resp
        
        # Extract token usage
        raw = block.get('raw_response', '')
        usage = extract_token_usage(raw)
        
        if usage:
            if verbose:
                print(f"Found token usage for block {idx}: {usage}")
            
            block['parsed_usage'] = usage
            
            # Add token usage info to the collection
            token_info = {
                'task_hint': block['task_hint'],
                'model': block['model'],
                'prompt_tokens': usage.get('prompt_tokens', 0),
                'completion_tokens': usage.get('completion_tokens', 0),
                'total_tokens': usage.get('total_tokens', 0)
            }
            
            # Calculate cost
            cost = (usage.get('prompt_tokens', 0) * 1.5e-07) + (usage.get('completion_tokens', 0) * 6e-07)
            token_info['cost_usd'] = cost
            
            token_usage_info.append(token_info)
        
        # Extract thought, action, final answer
        try:
            # Try to find patterns directly in the raw response
            final_match = re.search(r"Final Answer:(.*?)(?:\n\n|$)", raw, re.DOTALL)
            action_match = re.search(r"Action:(.*?)(?:\n|$)", raw, re.DOTALL)
            thought_match = re.search(r"Thought:(.*?)(?:\n|$)", raw, re.DOTALL)
            
            if final_match:
                block['final_answer'] = final_match.group(1).strip()
            if action_match:
                block['action'] = action_match.group(1).strip()
            if thought_match:
                block['thought'] = thought_match.group(1).strip()
            
            # If direct patterns failed, try JSON extraction
            if not (block['final_answer'] or block['action'] or block['thought']):
                # Try to extract JSON content
                json_match = re.search(r'(\{.*\})', raw, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group(1))
                        content = parsed.get('choices', [{}])[0].get('message', {}).get('content', '')
                        
                        if content:
                            f_match = re.search(r"Final Answer:(.*?)(?:\n\n|$)", content, re.DOTALL)
                            a_match = re.search(r"Action:(.*?)(?:\n|$)", content, re.DOTALL)
                            t_match = re.search(r"Thought:(.*?)(?:\n|$)", content, re.DOTALL)
                            
                            if f_match:
                                block['final_answer'] = f_match.group(1).strip()
                            if a_match:
                                block['action'] = a_match.group(1).strip()
                            if t_match:
                                block['thought'] = t_match.group(1).strip()
                    except:
                        pass
        except Exception as e:
            if verbose:
                print(f"Error processing block {idx}: {str(e)}")
            block['parsing_error'] = True

    return blocks, token_usage_info

def save_analysis(blocks: List[Dict], output_dir: str, verbose=False):
    """Save each LLM call's input and output to a file."""
    os.makedirs(output_dir, exist_ok=True)
    saved_files = 0
    
    for idx, block in enumerate(blocks):
        # Create a safe filename from the task hint
        safe_task_hint = slugify_filename(block.get('task_hint', 'Unknown Task'))
        file_prefix = f"{idx+1:03d}_{safe_task_hint}"
        input_path = Path(output_dir) / f"{file_prefix}_input.txt"
        output_path = Path(output_dir) / f"{file_prefix}_output.txt"
        
        # Write files
        try:
            input_path.write_text(block.get('litellm_request', ''))
            output_path.write_text(block.get('raw_response', ''))
            saved_files += 1
        except Exception as e:
            if verbose:
                print(f"Error saving files for block {idx}: {str(e)}")
    
    if verbose:
        print(f"Successfully saved {saved_files} input/output pairs.")

def extract_token_usage_v2(token_usage_info: List[Dict]):
    """Extract token usage and cost into a DataFrame."""
    try:
        import pandas as pd
        if not token_usage_info:
            # Return empty DataFrame with the expected columns
            return pd.DataFrame(columns=[
                'task_hint', 'model', 'prompt_tokens', 'completion_tokens', 'total_tokens', 'cost_usd'
            ])
        return pd.DataFrame(token_usage_info)
    except ImportError:
        print("Warning: pandas not installed. Token usage summary will not be available.")
        return []  # Return empty list as fallback