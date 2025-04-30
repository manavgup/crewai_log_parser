def extract_token_usage_from_raw_response(raw_text):
    """Extract token usage information directly from raw response text using regex.
    
    This function uses multiple approaches to find token usage data in the raw API response
    text, even when the JSON is malformed or incomplete.
    """
    import re
    
    # Try direct token extraction with individual regex searches
    prompt_match = re.search(r'"prompt_tokens"\s*:\s*(\d+)', raw_text)
    completion_match = re.search(r'"completion_tokens"\s*:\s*(\d+)', raw_text)
    total_match = re.search(r'"total_tokens"\s*:\s*(\d+)', raw_text)
    
    if prompt_match and completion_match and total_match:
        return {
            'prompt_tokens': int(prompt_match.group(1)),
            'completion_tokens': int(completion_match.group(1)),
            'total_tokens': int(total_match.group(1))
        }
    
    # If individual matches failed, try to find the full usage section
    usage_pattern = r'"usage"\s*:\s*\{([^}]*)\}'
    usage_match = re.search(usage_pattern, raw_text)
    
    if usage_match:
        usage_text = usage_match.group(1)
        
        # Try to extract individual values from the usage section
        prompt_match = re.search(r'"prompt_tokens"\s*:\s*(\d+)', usage_text)
        completion_match = re.search(r'"completion_tokens"\s*:\s*(\d+)', usage_text)
        total_match = re.search(r'"total_tokens"\s*:\s*(\d+)', usage_text)
        
        if prompt_match and completion_match and total_match:
            return {
                'prompt_tokens': int(prompt_match.group(1)),
                'completion_tokens': int(completion_match.group(1)),
                'total_tokens': int(total_match.group(1))
            }
    
    # Final attempt: look for these patterns anywhere in the text
    # This is the most lenient approach
    try:
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        
        for line in raw_text.split('\n'):
            if '"prompt_tokens"' in line and not prompt_tokens:
                match = re.search(r'(\d+)', line)
                if match:
                    prompt_tokens = int(match.group(1))
            
            if '"completion_tokens"' in line and not completion_tokens:
                match = re.search(r'(\d+)', line)
                if match:
                    completion_tokens = int(match.group(1))
            
            if '"total_tokens"' in line and not total_tokens:
                match = re.search(r'(\d+)', line)
                if match:
                    total_tokens = int(match.group(1))
        
        if prompt_tokens or completion_tokens or total_tokens:
            return {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': total_tokens or (prompt_tokens + completion_tokens)
            }
    except:
        pass
        
    # No token information found
    return None