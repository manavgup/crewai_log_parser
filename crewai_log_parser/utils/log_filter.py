def filter_tool_logs(log_content: str) -> str:
    """Filter out tool logs and other verbose content from log files.
    
    This function removes the noisy tool logs, action inputs, and other verbose
    content that might be displayed when parsing the log files, while preserving
    important information needed for analysis.
    
    Args:
        log_content: The raw log content
        
    Returns:
        Filtered log content without tool logs
    """
    import re
    
    # Lines to definitely filter out (exact matches)
    filter_patterns = [
        r'^Tool: .*Times Used: \d+$',            # Complete "Tool: X | Times Used: N" lines
        r'.*Times Used: \d+$',                   # Lines ending with "Times Used: N"
    ]
    
    # Compile patterns that should be completely filtered
    regex_patterns = [re.compile(pattern, re.MULTILINE) for pattern in filter_patterns]
    
    # Filter line by line but preserve critical information
    filtered_lines = []
    lines = log_content.split('\n')
    keep_next_n_lines = 0  # Counter to keep certain section lines
    
    for line in lines:
        # Always keep lines with "Request to litellm:" as they contain task info
        if "Request to litellm:" in line:
            filtered_lines.append(line)
            keep_next_n_lines = 10  # Keep next few lines to preserve task info
            continue
            
        # Always keep lines with "RAW RESPONSE:" as they contain usage data
        if "RAW RESPONSE:" in line:
            filtered_lines.append(line)
            keep_next_n_lines = 10  # Keep next few lines to preserve usage info
            continue
            
        # Keep a few lines after request/response headers to capture key information
        if keep_next_n_lines > 0:
            filtered_lines.append(line)
            keep_next_n_lines -= 1
            continue
            
        # Skip if any pattern matches from the complete filter list
        if any(pattern.match(line) for pattern in regex_patterns):
            continue
            
        # Skip long JSON blobs
        if len(line) > 500 and ('{' in line and '}' in line):
            continue
            
        # Keep any line with token usage information
        if '"usage"' in line or '"tokens"' in line or "Current Task:" in line:
            filtered_lines.append(line)
            continue
            
        # Keep model information lines
        if "model=" in line or '"model":' in line:
            filtered_lines.append(line)
            continue
            
        # Keep any line that's reasonably short (not large JSON)
        if len(line) < 300:
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)