from typing import List, Dict
from collections import Counter
from crewai_log_parser.models.parsed_block import ParsedBlock

import re

from crewai_log_parser.utils.parsing_utils import extract_tool_name

import pandas as pd

def analyze_tool_usage(blocks: List[ParsedBlock], print_results=False) -> pd.DataFrame:
    """Analyze tool usage patterns and return a DataFrame of tool names and their usage counts."""
    tool_counter = Counter()
    
    for block in blocks:
        tool = None
        
        if block.tool_used:
            tool = extract_tool_name(block.tool_used)  # <-- sanitize even if tool_used is present
        elif block.action:
            tool = extract_tool_name(block.action)

        if tool:
            tool_counter[tool] += 1

    data = []
    for tool_name, count in tool_counter.items():
        data.append({"Tool": tool_name, "Times Used": count})
    df = pd.DataFrame(data)
    return df
