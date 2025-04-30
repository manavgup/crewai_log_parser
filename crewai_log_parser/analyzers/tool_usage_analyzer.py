from typing import List, Dict
from collections import Counter
from crewai_log_parser.models.parsed_block import ParsedBlock

import re

def extract_tool_name(raw_line: str) -> str:
    """
    Extract the tool name from a line like:
    'Tool: Repository Analyzer\\nAction Input: {....}'
    
    Keeps only the clean tool name.
    """
    # First, make sure it starts with 'Tool: '
    if not raw_line.startswith("Tool: "):
        return ""
    
    # Remove 'Tool: ' prefix
    trimmed = raw_line[len("Tool: "):]
    
    # Now split at the first '\nAction Input'
    if "\\nAction Input:" in trimmed:
        trimmed = trimmed.split("\\nAction Input:")[0]
    
    return trimmed.strip()




def analyze_tool_usage(blocks: List[ParsedBlock], print_results=True) -> Dict[str, int]:
    """Analyze tool usage patterns and return a dictionary of tool names and their usage counts."""
    tool_counter = Counter()
    
    for block in blocks:
        tool = None
        
        if block.tool_used:
            tool = extract_tool_name(block.tool_used)  # <-- sanitize even if tool_used is present
        elif block.action:
            tool = extract_tool_name(block.action)

        if tool:
            tool_counter[tool] += 1

    if print_results:
        if tool_counter:
            print("\n--- Tool Usage Summary ---")
            for tool_name, count in tool_counter.items():
                print(f"Tool: {tool_name} | Times Used: {count}")
        else:
            print("\nNo tool usage data available.")

    return dict(tool_counter)

