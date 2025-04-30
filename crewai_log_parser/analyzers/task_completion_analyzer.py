from typing import List, Dict
from crewai_log_parser.models.parsed_block import ParsedBlock

def clean_task_hint(task_hint: str) -> str:
    """Sanitize and truncate the task hint for display."""
    if not task_hint:
        return "Unknown Task"
    
    # Clean up newlines and tabs for display
    clean_hint = task_hint.replace("\n", " ").replace("\t", " ")
    
    # Collapse multiple spaces
    while "  " in clean_hint:
        clean_hint = clean_hint.replace("  ", " ")
    
    # Truncate to reasonable length
    if len(clean_hint) > 80:
        return clean_hint[:77] + "..."
    
    return clean_hint

def analyze_task_completion(blocks: List[ParsedBlock]) -> Dict[ParsedBlock, bool]:
    """Analyze task completion status for each block and return a dictionary mapping blocks to completion status."""
    task_completion = {}
    
    print("\n--- Task Completion Metrics ---")
    for idx, block in enumerate(blocks):
        short_hint = clean_task_hint(block.task_hint)
        final_answer_present = bool(block.final_answer)
        task_completion[block] = final_answer_present
        
        result = "✅" if final_answer_present else "❌"
        print(f"Step {idx+1:02}: Task Hint: {short_hint:80} | Final Answer: {result}")
    
    # Print a summary
    completed_count = sum(1 for status in task_completion.values() if status)
    if blocks:
        completion_pct = (completed_count / len(blocks)) * 100
        print(f"\nTask Completion Rate: {completed_count}/{len(blocks)} ({completion_pct:.1f}%)")
    
    return task_completion