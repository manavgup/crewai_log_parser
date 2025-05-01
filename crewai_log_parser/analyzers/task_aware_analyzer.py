from typing import List, Dict, Optional
import pandas as pd
from crewai_log_parser.models.enhanced_parsed_block import EnhancedParsedBlock
from crewai_log_parser.models.config_models import CrewAITask, CrewAIAgent
from crewai_log_parser.utils.parsing_utils import extract_tool_name

def analyze_task_performance(blocks: List[EnhancedParsedBlock], tasks: Dict[str, CrewAITask], agents: Dict[str, CrewAIAgent]) -> pd.DataFrame:
    task_blocks: Dict[str, List[EnhancedParsedBlock]] = {}
    for block in blocks:
        if block.task_id:
            if block.task_id not in task_blocks:
                task_blocks[block.task_id] = []
            task_blocks[block.task_id].append(block)
    data = []
    
    # Track totals for summary row
    total_tokens = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cost = 0
    
    for task_id, blocks_list in task_blocks.items():
        task = tasks.get(task_id)
        agent_id = blocks_list[0].agent_id if blocks_list else None
        agent = agents.get(agent_id) if agent_id else None
        token_usage = sum(block.parsed_usage.total_tokens for block in blocks_list if block.parsed_usage is not None)
        prompt_tokens = sum(block.parsed_usage.prompt_tokens for block in blocks_list if block.parsed_usage is not None)
        completion_tokens = sum(block.parsed_usage.completion_tokens for block in blocks_list if block.parsed_usage is not None)
        cost = sum(getattr(block.parsed_usage, "cost_usd", 0) for block in blocks_list if block.parsed_usage is not None)
        
        # Update totals
        total_tokens += token_usage
        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens
        total_cost += cost
        
        response_time = 0
        response_time_blocks = 0
        for block in blocks_list:
            if block.start_time and block.end_time:
                try:
                    start = pd.to_datetime(block.start_time)
                    end = pd.to_datetime(block.end_time)
                    response_time += (end - start).total_seconds()
                    response_time_blocks += 1
                except Exception:
                    pass
        avg_response_time = response_time / response_time_blocks if response_time_blocks > 0 else 0
        
        tools_used = {}
        for block in blocks_list:
            if block.tool_used:
                clean_tool = extract_tool_name(block.tool_used)
                tools_used[clean_tool] = tools_used.get(clean_tool, 0) + 1
        tools_list = [f"- {tool} ({count})" for tool, count in tools_used.items()]
        tools_str = "\n".join(tools_list)
        
        row = {
            "Task ID": task_id,
            "Agent": agent_id or "Unknown",
            "Agent Role": agent.role if agent else "Unknown",
            "Total Tokens": token_usage,
            "Prompt Tokens": prompt_tokens,
            "Completion Tokens": completion_tokens,
            "Cost (USD)": cost,
            "Avg Response Time (s)": avg_response_time,
            "Tools Used": tools_str,
            "Total Token Usage": token_usage,
            "Total Cost": cost
        }
        data.append(row)
    
    # Add totals row
    totals_row = {
        "Task ID": "TOTALS",
        "Agent": "",
        "Agent Role": "",
        "Total Tokens": total_tokens,
        "Prompt Tokens": total_prompt_tokens,
        "Completion Tokens": total_completion_tokens,
        "Cost (USD)": total_cost,
        "Avg Response Time (s)": "",
        "Tools Used": "",
        "Total Token Usage": total_tokens,
        "Total Cost": total_cost
    }
    
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values("Task ID")
        # Append totals row
        df = pd.concat([df, pd.DataFrame([totals_row])], ignore_index=True)
    
    return df

def analyze_agent_performance(blocks: List[EnhancedParsedBlock], agents: Dict[str, CrewAIAgent]) -> pd.DataFrame:
    agent_blocks: Dict[str, List[EnhancedParsedBlock]] = {}
    for block in blocks:
        if block.agent_id:
            if block.agent_id not in agent_blocks:
                agent_blocks[block.agent_id] = []
            agent_blocks[block.agent_id].append(block)
    data = []
    
    # Track totals for summary row
    total_tokens = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cost = 0
    
    for agent_id, blocks_list in agent_blocks.items():
        agent = agents.get(agent_id)
        token_usage = sum(block.parsed_usage.total_tokens for block in blocks_list if block.parsed_usage is not None)
        prompt_tokens = sum(block.parsed_usage.prompt_tokens for block in blocks_list if block.parsed_usage is not None)
        completion_tokens = sum(block.parsed_usage.completion_tokens for block in blocks_list if block.parsed_usage is not None)
        cost = sum(getattr(block.parsed_usage, "cost_usd", 0) for block in blocks_list if block.parsed_usage is not None)
        
        # Update totals
        total_tokens += token_usage
        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens
        total_cost += cost
        
        unique_tasks = set(block.task_id for block in blocks_list if block.task_id)
        row = {
            "Agent ID": agent_id,
            "Agent Role": agent.role if agent else "Unknown",
            "Unique Tasks": len(unique_tasks),
            "Total Tokens": token_usage,
            "Prompt Tokens": prompt_tokens,
            "Completion Tokens": completion_tokens,
            "Cost (USD)": cost
        }
        data.append(row)
    
    # Add totals row
    totals_row = {
        "Agent ID": "TOTALS",
        "Agent Role": "",
        "Unique Tasks": "",
        "Total Tokens": total_tokens,
        "Prompt Tokens": total_prompt_tokens,
        "Completion Tokens": total_completion_tokens,
        "Cost (USD)": total_cost
    }
    
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values("Total Tokens", ascending=False)
        # Append totals row
        df = pd.concat([df, pd.DataFrame([totals_row])], ignore_index=True)
    
    return df

from crewai_log_parser.analyzers.tool_usage_analyzer import analyze_tool_usage as base_analyze_tool_usage

def analyze_tool_usage(blocks: List[EnhancedParsedBlock]) -> pd.DataFrame:
    # Reuse the existing analyze_tool_usage function from tool_usage_analyzer.py for consistency
    return base_analyze_tool_usage(blocks)
