
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Set, Any
from crewai_log_parser.models.parsed_block import ParsedBlock
from collections import Counter, defaultdict
import re
import logging

logger = logging.getLogger(__name__)

def extract_tool_name(action: str) -> str:
    """Extract clean tool name using regex."""
    if not action:
        return ""
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

# --- Function to normalize task hints for grouping ---
def normalize_task_hint(hint: str, max_length: int = 50) -> str:
    """Normalize and truncate task hint for grouping."""
    if not hint:
        return "Unknown Task"
    normalized = hint.strip().lower()
    normalized = re.sub(r"^\d+\.\s*", "", normalized)
    normalized = re.sub(r"^task\s*\d*:\s*", "", normalized)
    # Remove common prefixes/suffixes if needed
    normalized = normalized.replace("**critical batch processing:**", "").strip()
    normalized = normalized.replace("**critical merging task:**", "").strip()
    normalized = normalized.replace("**critical naming task:**", "").strip()
    normalized = normalized.replace("**critical final refinement task:**", "").strip()
    # Use the *truncated* version for grouping to match display
    return truncate_task_hint(normalized, max_length) # Group by the truncated hint

def unified_analysis(blocks: List[ParsedBlock], verbose: bool = False) -> Optional[pd.DataFrame]:
    """Generate a unified analysis table with metrics grouped by task."""
    # Calculate response times first
    times: List[tuple[ParsedBlock, datetime]] = []
    prompt_token_cost: float = 1.5e-07
    completion_token_cost: float = 6e-07

    # Attempt to parse token costs from blocks if available
    for block in blocks:
        usage = block.parsed_usage or {}
        if 'prompt_token_cost' in usage:
            prompt_token_cost = usage['prompt_token_cost']
        if 'completion_token_cost' in usage:
            completion_token_cost = usage['completion_token_cost']
        # Break early if both found
        if prompt_token_cost != 1.5e-07 and completion_token_cost != 6e-07:
            break

    for block in blocks:
        if block.start_time:
            try:
                start_dt = datetime.strptime(block.start_time, "%Y-%m-%d %H:%M:%S")
                times.append((block, start_dt))
            except Exception as e:
                if verbose:
                    logger.error(f"Error processing timestamp: {e}")
                continue
    times.sort(key=lambda x: x[1])

    response_times_map: Dict[ParsedBlock, float] = {}
    if len(times) >= 2:
        for i in range(1, len(times)):
            current_block, current_time = times[i]
            prev_block, prev_time = times[i-1]
            duration = (current_time - prev_time).total_seconds()
            response_times_map[current_block] = duration

    # --- Group blocks by normalized task hint and aggregate metrics ---
    grouped_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "First Step": float('inf'),
        "Models": set(),
        "Prompt Tokens": 0,
        "Completion Tokens": 0,
        "Total Tokens": 0,
        "Cost (USD)": 0.0,
        "Total Response Time (s)": 0.0,
        "Final Answers Count": 0,
        "Block Count": 0,
        "Tools": Counter(),
        "Original Hint Sample": "" # Store one representative original hint
    })

    overall_tool_counter: Counter = Counter() # For the separate summary

    for idx, block in enumerate(blocks):
        # Use the *truncated* hint for grouping key, matching display
        group_key = truncate_task_hint(block.task_hint)
        group = grouped_data[group_key]

        # Store the first step number encountered for this group
        group["First Step"] = min(group["First Step"], idx + 1)
        if not group["Original Hint Sample"]: # Keep the first hint encountered
             group["Original Hint Sample"] = group_key

        if block.model:
            group["Models"].add(block.model)

        usage = block.parsed_usage or {}
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)
        cost = (prompt_tokens * prompt_token_cost) + (completion_tokens * completion_token_cost)

        group["Prompt Tokens"] += prompt_tokens
        group["Completion Tokens"] += completion_tokens
        group["Total Tokens"] += total_tokens
        group["Cost (USD)"] += cost

        response_time = response_times_map.get(block)
        if response_time is not None:
            group["Total Response Time (s)"] += response_time

        if block.final_answer:
            group["Final Answers Count"] += 1
        group["Block Count"] += 1

        if block.action:
            tool_name = extract_tool_name(block.action)
            if tool_name:
                group["Tools"][tool_name] += 1
                overall_tool_counter[tool_name] += 1 # Update overall counter too

    # --- Create DataFrame rows from aggregated data ---
    data = []
    # Sort groups based on the first step they appeared in
    sorted_groups = sorted(grouped_data.items(), key=lambda item: item[1]["First Step"])

    for task_key, metrics in sorted_groups:
        model_str = ", ".join(sorted(list(metrics["Models"]))) if metrics["Models"] else "unknown"
        # Format tool usage string for the row
        tool_str = ", ".join(f"{tool}({count})" for tool, count in metrics["Tools"].most_common())

        row = {
            "Step": metrics["First Step"], # Show the first step number
            "Task": metrics["Original Hint Sample"], # Use the representative truncated hint
            "Model": model_str,
            "Prompt Tokens": metrics["Prompt Tokens"],
            "Completion Tokens": metrics["Completion Tokens"],
            "Total Tokens": metrics["Total Tokens"],
            "Cost (USD)": metrics["Cost (USD)"],
            "Response Time (s)": metrics["Total Response Time (s)"] if metrics["Total Response Time (s)"] > 0 else "",
            "Final Answer": f"{metrics['Final Answers Count']}/{metrics['Block Count']}", # Show as X/Y
            "Tool Used": tool_str # Show aggregated tools for the group
        }
        data.append(row)

    if not data:
        logger.warning("No data available for analysis.")
        return None

    # Convert aggregated data to DataFrame
    df_grouped = pd.DataFrame(data)

    # --- Calculate and add summary row ---
    total_prompt = df_grouped["Prompt Tokens"].sum()
    total_completion = df_grouped["Completion Tokens"].sum()
    total_tokens_overall = df_grouped["Total Tokens"].sum()
    total_cost = df_grouped["Cost (USD)"].sum()
    # Sum response time correctly (handle empty strings)
    total_response_time = pd.to_numeric(df_grouped["Response Time (s)"], errors='coerce').sum()
    # Calculate total final answers and total blocks from the grouped data
    final_answers_split = df_grouped['Final Answer'].str.split('/', expand=True)
    total_final_answers = pd.to_numeric(final_answers_split[0], errors='coerce').sum()
    total_blocks = pd.to_numeric(final_answers_split[1], errors='coerce').sum()


    summary = {
        "Step": "",
        "Task": "TOTAL",
        "Model": "",
        "Prompt Tokens": total_prompt,
        "Completion Tokens": total_completion,
        "Total Tokens": total_tokens_overall,
        "Cost (USD)": total_cost,
        "Response Time (s)": total_response_time if total_response_time > 0 else "",
        "Final Answer": f"{int(total_final_answers)}/{int(total_blocks)}",
        "Tool Used": ""
    }
    df_grouped = pd.concat([df_grouped, pd.DataFrame([summary])], ignore_index=True)

    # --- Print the final grouped table ---
    print("\n--- Unified Analysis (Tasks Combined) ---")
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    pd.set_option('display.max_colwidth', 40) # Keep truncation consistent
    pd.set_option('display.float_format', lambda x: f"{x:.6f}" if isinstance(x, float) and abs(x) < 0.01 else (f"{x:.4f}" if isinstance(x, float) else x))
    print(df_grouped.to_string(index=False, justify='left'))

    # --- Print the separate overall tool usage summary ---
    print("\n--- Overall Tool Usage Summary ---")
    if overall_tool_counter:
        for tool, count in sorted(overall_tool_counter.items(), key=lambda x: x[1], reverse=True):
            # Adjust spacing for alignment
            print(f"Tool: {tool:35} | Times Used: {count}")
    else:
        print("No tool usage detected.")

    return df_grouped # Return the grouped DataFrame
