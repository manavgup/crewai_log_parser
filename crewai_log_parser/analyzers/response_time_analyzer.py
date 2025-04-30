from datetime import datetime
from typing import List, Dict, Tuple
from crewai_log_parser.models.parsed_block import ParsedBlock

def analyze_response_times(blocks: List[ParsedBlock], verbose=False) -> Dict[ParsedBlock, float]:
    """Analyze response times between LLM calls and return a dictionary of blocks and their response times."""
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
        print("\n--- Response Time Analysis ---")
        for i in range(1, len(times)):
            block = times[i][0]
            duration = (times[i][1] - times[i-1][1]).total_seconds()
            response_times[block] = duration
            
            # Truncate task hint for display
            task_hint = block.task_hint
            if task_hint and len(task_hint) > 50:
                display_hint = task_hint[:47] + "..."
            else:
                display_hint = task_hint or "Unknown Task"
                
            print(f"Task: {display_hint:50} | Response Time: {duration:.2f}s")
    else:
        print("\nNot enough tasks with valid timestamps to analyze response times.")
    
    return response_times