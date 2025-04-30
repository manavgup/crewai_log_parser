import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from crewai_log_parser.models.parsed_block import ParsedBlock
from collections import Counter
import re
def extract_tool_name(action: str) -> str:
    """Extract clean tool name using regex."""
    if not action:
        return ""
    
    # Try to find everything before first '\n' or '('
    match = re.match(r"^(.*?)\s*(?:\\n|\()", action)
    if match:
        return match.group(1).strip()
    
    return action.strip()

def truncate_task_hint(hint: str, max_length: int = 40) -> str:
    """Truncate task hint to a reasonable length for display."""
    if not hint:
        return "Unknown Task"
    
    if len(hint) > max_length:
        return hint[:max_length-3] + "..."
    
    return hint

def unified_analysis(blocks: List[ParsedBlock], verbose: bool = False) -> Optional[pd.DataFrame]:
    """Generate a unified analysis table with all metrics for LLM calls."""
    # Calculate response times first
    times = []
    for block in blocks:
        if block.start_time: 
            try:
                start_dt = datetime.strptime(block.start_time, "%Y-%m-%d %H:%M:%S")
                times.append((block, start_dt))
            except Exception as e:
                if verbose:
                    print(f"Error processing timestamp: {e}")
                continue
    
    times.sort(key=lambda x: x[1])
    
    response_times = {}
    if len(times) >= 2:
        for i in range(1, len(times)):
            block = times[i][0]
            duration = (times[i][1] - times[i-1][1]).total_seconds()
            response_times[block] = duration
    
    # Debug token usage if verbose mode
    if verbose:
        for idx, block in enumerate(blocks):
            if block.parsed_usage:
                print(f"Block {idx}: {block.parsed_usage}")
            else:
                print(f"Block {idx}: No token usage data")
    
    # Create data for unified table
    data = []
    for idx, block in enumerate(blocks):
        # Truncate task hint for display
        display_hint = truncate_task_hint(block.task_hint)
            
        # Get tokens if available
        prompt_tokens = block.parsed_usage.get('prompt_tokens', 0) if block.parsed_usage else 0
        completion_tokens = block.parsed_usage.get('completion_tokens', 0) if block.parsed_usage else 0
        total_tokens = block.parsed_usage.get('total_tokens', 0) if block.parsed_usage else 0
        
        # Calculate cost
        cost = 0
        if prompt_tokens or completion_tokens:
            cost = (prompt_tokens * 1.5e-07) + (completion_tokens * 6e-07)
        
        # Get response time
        response_time = response_times.get(block, None)
        
        # Check for final answer
        has_final_answer = "✅" if block.final_answer else "❌"
        
        # Get tool used
        tool_used = extract_tool_name(block.action) if block.action else ""
        
        # Build the row
        row = {
            "Step": idx + 1,
            "Task": display_hint,
            "Model": block.model or "unknown",
            "Prompt Tokens": prompt_tokens,
            "Completion Tokens": completion_tokens, 
            "Total Tokens": total_tokens,
            "Cost (USD)": cost,
            "Response Time (s)": response_time if response_time is not None else "",
            "Final Answer": has_final_answer,
            "Tool Used": tool_used
        }

        data.append(row)
    
    # Exit if no data
    if not data:
        print("No data available for analysis.")
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Add a summary row with totals
    summary = {
        "Step": "",
        "Task": "TOTAL",
        "Model": "",
        "Prompt Tokens": df["Prompt Tokens"].sum(),
        "Completion Tokens": df["Completion Tokens"].sum(),
        "Total Tokens": df["Total Tokens"].sum(),
        "Cost (USD)": df["Cost (USD)"].sum()
    }
    
    # Handle response time total
    if any(isinstance(x, (int, float)) for x in df["Response Time (s)"]):
        valid_times = [t for t in df["Response Time (s)"] if isinstance(t, (int, float))]
        summary["Response Time (s)"] = sum(valid_times) if valid_times else ""
    else:
        summary["Response Time (s)"] = ""
    
    # Handle final answer count
    check_count = df["Final Answer"].value_counts().get("✅", 0)
    summary["Final Answer"] = f"{check_count}/{len(df)}"
    
    # No tool summary
    summary["Tool Used"] = ""
    
    # Add summary row
    df = pd.concat([df, pd.DataFrame([summary])], ignore_index=True)
    
    # Print the unified table
    print("\n--- Unified Analysis ---")
    # Format the DataFrame nicely for display
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    pd.set_option('display.float_format', lambda x: f"{x:.6f}" if x < 0.01 else f"{x:.4f}")
    print(df.to_string(index=False))
    
    # Also separately print tool usage summary since it might be useful
    tool_counter = Counter()
    for block in blocks:
        if block.action:
            tool = extract_tool_name(block.action)
            if tool:  # Only count non-empty tool names
                tool_counter[tool] += 1
    
    print("\n--- Tool Usage Summary ---")
    if tool_counter:
        for tool, count in sorted(tool_counter.items(), key=lambda x: x[1], reverse=True):
            print(f"Tool: {tool:30} | Times Used: {count}")
    else:
        print("No tool usage detected.")
    
    return df