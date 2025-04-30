import argparse
from pathlib import Path
from crewai_log_parser.parsers.log_parser_v2 import parse_log_file_v2, save_analysis, extract_token_usage_v2
from crewai_log_parser.models.parsed_block import ParsedBlock
from crewai_log_parser.analyzers.unified_analyzer import unified_analysis

def main():
    parser = argparse.ArgumentParser(description="CrewAI Log Parser CLI")
    parser.add_argument("log_path", type=str, help="Path to the log file.")
    parser.add_argument("output_dir", type=str, help="Directory to save extracted input/output files.")
    parser.add_argument("--debug", action="store_true", help="Show debug information")
    parser.add_argument("--verbose", action="store_true", help="Show verbose output")
    parser.add_argument("--separate", action="store_true", help="Show separate analysis tables instead of unified")
    args = parser.parse_args()
    
    log_path = args.log_path
    output_dir = args.output_dir
    debug_mode = args.debug
    verbose_mode = args.verbose
    separate_mode = args.separate
    
    # Read log file content directly
    log_content = Path(log_path).read_text()
    lines_count = len(log_content.splitlines())
    print(f"Got {lines_count} lines from {log_path}")
    
    # --- Use the enhanced parser with working token extraction ---
    raw_blocks, token_usage_info = parse_log_file_v2(log_path, verbose=verbose_mode)
    
    print(f"Total LLM calls detected: {len(raw_blocks)}")
    
    # Debug: Check token_usage_info
    if verbose_mode:
        print(f"Token usage entries collected: {len(token_usage_info)}")
        if token_usage_info and debug_mode:
            # Show the first token entry to help verify format
            sample = token_usage_info[0]
            print(f"Sample token entry: {sample}")
    
    # --- Save parsed input/output files using original working approach ---
    save_analysis(raw_blocks, output_dir, verbose=verbose_mode)
    print(f"Saved detailed LLM input/output to folder: {output_dir}")
    
    # --- VERY IMPORTANT: CONVERT raw_blocks -> ParsedBlock objects ---
    parsed_blocks = [ParsedBlock(**block) for block in raw_blocks]
    
    # --- Show token usage in separate table if requested or in debug mode ---
    if debug_mode or separate_mode:
        token_df = extract_token_usage_v2(token_usage_info)
        print("\n--- Token Usage Summary ---")
        if not token_df.empty:
            import pandas as pd
            pd.set_option('display.max_rows', None)
            pd.set_option('display.width', 120)
            pd.set_option('display.float_format', lambda x: f"{x:.6f}" if x < 0.01 else f"{x:.4f}")
            print(token_df.to_string(index=False))
        else:
            print("No valid token usage could be parsed.")
    
    # --- Show separate or unified analysis based on mode ---
    if separate_mode:
        # Run separate analyzers like in the old version
        from crewai_log_parser.analyzers.response_time_analyzer import analyze_response_times
        from crewai_log_parser.analyzers.task_completion_analyzer import analyze_task_completion
        from crewai_log_parser.analyzers.tool_usage_analyzer import analyze_tool_usage
        
        analyze_response_times(parsed_blocks, verbose=verbose_mode)
        analyze_task_completion(parsed_blocks)
        analyze_tool_usage(parsed_blocks)
    else:
        # Generate a unified analysis table
        unified_analysis(parsed_blocks, verbose=verbose_mode)
    
    # --- Report parsing errors and summary if in verbose mode ---
    if verbose_mode:
        errors = sum(1 for block in raw_blocks if block.get('parsing_error', False))
        print(f"\n--- Parsing Summary ---")
        print(f"Total parsing errors: {errors} out of {len(raw_blocks)} calls")
        
        final_answers = sum(1 for block in raw_blocks if block.get('final_answer'))
        print(f"Final answers detected: {final_answers} out of {len(raw_blocks)} calls")

if __name__ == "__main__":
    main()