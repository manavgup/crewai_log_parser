import re
import json
from pathlib import Path
from typing import List, Dict, Tuple
import os

def extract_token_usage_from_raw_response(raw_text):
    """Extract token usage information directly from raw response text using regex."""
    import re
    
    # Look for the specific format shown in the example
    # "usage": {"completion_tokens": 6145, "prompt_tokens": 11161, "total_tokens": 17306, ...
    completion_match = re.search(r'"completion_tokens":\s*(\d+)', raw_text)
    prompt_match = re.search(r'"prompt_tokens":\s*(\d+)', raw_text)
    total_match = re.search(r'"total_tokens":\s*(\d+)', raw_text)
    
    if prompt_match and completion_match and total_match:
        return {
            'prompt_tokens': int(prompt_match.group(1)),
            'completion_tokens': int(completion_match.group(1)),
            'total_tokens': int(total_match.group(1))
        }
    
    # Try line-by-line approach for logs with line breaks
    lines = raw_text.split('\n')
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    
    for line in lines:
        if '"prompt_tokens"' in line:
            match = re.search(r'(\d+)', line)
            if match:
                prompt_tokens = int(match.group(1))
        
        if '"completion_tokens"' in line:
            match = re.search(r'(\d+)', line)
            if match:
                completion_tokens = int(match.group(1))
        
        if '"total_tokens"' in line:
            match = re.search(r'(\d+)', line)
            if match:
                total_tokens = int(match.group(1))
    
    if prompt_tokens or completion_tokens or total_tokens:
        # If we have at least one token count, calculate any missing ones
        if not total_tokens and (prompt_tokens and completion_tokens):
            total_tokens = prompt_tokens + completion_tokens
        
        return {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens
        }
    
    # If all else fails, try to extract all numbers after these keywords
    # This is a last-resort approach
    tokens = {}
    for token_type in ['prompt_tokens', 'completion_tokens', 'total_tokens']:
        all_matches = re.findall(rf'"{token_type}":\s*(\d+)', raw_text)
        if all_matches:
            tokens[token_type] = int(all_matches[0])
    
    if tokens:
        return {
            'prompt_tokens': tokens.get('prompt_tokens', 0),
            'completion_tokens': tokens.get('completion_tokens', 0),
            'total_tokens': tokens.get('total_tokens', 0)
        }
    
    # No token information found
    return None

def extract_model_name(text: str) -> str:
    """Extract the model name from the litellm request."""
    # Check for model in different formats
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
    parse_errors = 0
    for idx, block in enumerate(blocks):
        task_match = re.search(r"Current Task: (.*?)\n", block['litellm_request'], re.DOTALL)
        if task_match:
            block['task_hint'] = task_match.group(1).strip()
        else:
            block['task_hint'] = 'Unknown_Task'  # Use underscore for better safety in filenames

        # Extract model information
        block['model'] = extract_model_name(block['litellm_request'])
        
        # Parse the raw response for token usage - this will find the usage data
        # even if it's deeply nested in the response JSON
        raw = block.get('raw_response', '')
        usage = extract_token_usage_from_raw_response(raw)
        
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
            
            # Calculate cost (can be adjusted based on your model pricing)
            cost = (usage.get('prompt_tokens', 0) * 1.5e-07) + (usage.get('completion_tokens', 0) * 6e-07)
            token_info['cost_usd'] = cost
            
            token_usage_info.append(token_info)
            
        # Try to extract content for thought, action, final answer
        try:
            # First look for direct final answer pattern
            final_answer_match = re.search(r"Final Answer:(.*?)$", raw, re.DOTALL)
            if final_answer_match:
                block['final_answer'] = final_answer_match.group(1).strip()
            
            # Look for actions/tools
            action_match = re.search(r"Action:(.*?)\n", raw, re.DOTALL)
            if action_match:
                block['action'] = action_match.group(1).strip()
            
            # Look for thought patterns
            thought_match = re.search(r"Thought:(.*?)\n", raw, re.DOTALL)
            if thought_match:
                block['thought'] = thought_match.group(1).strip()
            
            # If no direct matches, try looking in the content field
            if not (block['final_answer'] or block['action'] or block['thought']):
                content_pattern = r'"content":\s*"([^"]*)"'
                content_match = re.search(content_pattern, raw, re.DOTALL)
                if content_match:
                    content = content_match.group(1)
                    # Unescape any escaped characters
                    content = content.encode().decode('unicode_escape')
                    
                    # Check content for our patterns
                    if "Final Answer:" in content:
                        final_match = re.search(r"Final Answer:(.*?)(?:$|\\n\\n)", content, re.DOTALL)
                        if final_match:
                            block['final_answer'] = final_match.group(1).strip()
                    
                    if "Action:" in content:
                        action_match = re.search(r"Action:(.*?)(?:\\n|$)", content, re.DOTALL)
                        if action_match:
                            block['action'] = action_match.group(1).strip()
                    
                    if "Thought:" in content:
                        thought_match = re.search(r"Thought:(.*?)(?:\\n|$)", content, re.DOTALL)
                        if thought_match:
                            block['thought'] = thought_match.group(1).strip()
            
        except Exception as e:
            if verbose:
                print(f"Error parsing content for block {idx}: {str(e)}")
            
    return blocks, token_usage_info

def save_analysis(blocks: List[Dict], output_dir: str, verbose=False):
    """Save each LLM call's input and output to a file."""
    os.makedirs(output_dir, exist_ok=True)
    if verbose:
        print(f"Saving {len(blocks)} input/output pairs to: {output_dir}")
    saved_files = 0
    
    for idx, block in enumerate(blocks):
        # Create a safe filename from the task hint
        if not block.get('task_hint'):
            task_hint = 'Unknown_Task'
        else:
            task_hint = block['task_hint']
            # Sanitize task hint for filename
            task_hint = re.sub(r'[^a-zA-Z0-9_-]', '_', task_hint)
            # Truncate to avoid overly long filenames
            task_hint = task_hint[:80]
        
        # Create filenames
        file_prefix = f"{idx+1:03d}_{task_hint}"
        input_path = Path(output_dir) / f"{file_prefix}_input.txt"
        output_path = Path(output_dir) / f"{file_prefix}_output.txt"
        
        # Write files
        try:
            with open(input_path, 'w') as f:
                f.write(block.get('litellm_request', ''))
            
            with open(output_path, 'w') as f:
                f.write(block.get('raw_response', ''))
                
            saved_files += 1
        except Exception as e:
            if verbose:
                print(f"Error saving files for block {idx}: {str(e)}")