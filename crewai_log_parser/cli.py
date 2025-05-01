import argparse
from pathlib import Path
import pandas as pd
from typing import Optional

from rich.console import Console
from rich.table import Table

from crewai_log_parser.parsers.log_parser_v2 import parse_log_file_v2, save_analysis
from crewai_log_parser.parsers.config_aware_parser import ConfigAwareLogParser
from crewai_log_parser.analyzers.unified_analyzer import unified_analysis
from crewai_log_parser.analyzers.task_aware_analyzer import (
    analyze_task_performance, 
    analyze_agent_performance,
    analyze_tool_usage
)
from crewai_log_parser.analyzers.workflow_reconstructor import WorkflowReconstructor
from crewai_log_parser.utils.config_loader import load_tasks, load_agents

def print_rich_table(df, title=None):
    console = Console()
    table = Table(title=title, show_lines=True, header_style="bold magenta")
    for col in df.columns:
        table.add_column(str(col), overflow="fold")
    for _, row in df.iterrows():
        table.add_row(*[str(x) if x is not None else "" for x in row])
    console.print(table)

def main():
    parser = argparse.ArgumentParser(description="CrewAI Log Parser CLI")
    parser.add_argument("log_path", type=str, help="Path to the log file.")
    parser.add_argument("output_dir", type=str, help="Directory to save extracted input/output files.")
    parser.add_argument("--debug", action="store_true", help="Show debug information")
    parser.add_argument("--verbose", action="store_true", help="Show verbose output")
    parser.add_argument("--separate", action="store_true", help="Show separate analysis tables instead of unified")
    parser.add_argument("--crewai-config", type=str, help="Path to the CrewAI configuration directory")
    parser.add_argument("--tasks-yaml", type=str, help="Path to the tasks.yaml file (overrides --crewai-config)")
    parser.add_argument("--agents-yaml", type=str, help="Path to the agents.yaml file (overrides --crewai-config)")
    parser.add_argument("--task-aware", action="store_true", help="Use task-aware analysis")
    parser.add_argument("--workflow-diagram", action="store_true", help="Generate workflow diagram")
    args = parser.parse_args()

    log_path = args.log_path
    output_dir = args.output_dir
    debug_mode = args.debug
    verbose_mode = args.verbose
    separate_mode = args.separate
    task_aware_mode = args.task_aware

    # Determine paths to configuration files
    tasks_yaml_path: Optional[str] = None
    agents_yaml_path: Optional[str] = None

    if args.tasks_yaml:
        tasks_yaml_path = args.tasks_yaml
    elif args.crewai_config:
        tasks_yaml_path = str(Path(args.crewai_config) / "tasks.yaml")

    if args.agents_yaml:
        agents_yaml_path = args.agents_yaml
    elif args.crewai_config:
        agents_yaml_path = str(Path(args.crewai_config) / "agents.yaml")

    # Read log file content directly
    log_content = Path(log_path).read_text()
    lines_count = len(log_content.splitlines())
    print(f"Got {lines_count} lines from {log_path}")

    if task_aware_mode and (tasks_yaml_path or agents_yaml_path):
        # Use the config-aware parser
        config_parser = ConfigAwareLogParser(tasks_yaml_path, agents_yaml_path)
        enhanced_blocks = config_parser.parse_log_file(log_path, verbose=verbose_mode)

        print(f"Total LLM calls detected: {len(enhanced_blocks)}")

        # Save parsed input/output files
        raw_blocks, _ = parse_log_file_v2(log_path, verbose=verbose_mode)
        save_analysis(raw_blocks, output_dir, verbose=verbose_mode)
        print(f"Saved detailed LLM input/output to folder: {output_dir}")

        # Perform task-aware analysis
        if tasks_yaml_path and agents_yaml_path:
            tasks = load_tasks(tasks_yaml_path)
            agents = load_agents(agents_yaml_path)

            print()
            print_rich_table(analyze_task_performance(enhanced_blocks, tasks, agents), title="Task Performance Analysis")

            print()
            print_rich_table(analyze_agent_performance(enhanced_blocks, agents), title="Agent Performance Analysis")

            print()
            print_rich_table(analyze_tool_usage(enhanced_blocks), title="Tool Usage Analysis")

            if args.workflow_diagram:
                reconstructor = WorkflowReconstructor(enhanced_blocks, tasks, agents)
                reconstructor.reconstruct()
                mermaid_code = reconstructor.generate_mermaid_diagram()
                diagram_path = Path(output_dir) / "workflow_diagram.md"
                with open(diagram_path, 'w') as f:
                    f.write("# Workflow Diagram\n\n")
                    f.write("```mermaid\n")
                    f.write(mermaid_code)
                    f.write("\n```\n")
                print(f"\nWorkflow diagram saved to: {diagram_path}")
        else:
            unified_analysis(enhanced_blocks, verbose=verbose_mode)
    else:
        # Use the original parser
        raw_blocks, token_usage_info = parse_log_file_v2(log_path, verbose=verbose_mode)
        print(f"Total LLM calls detected: {len(raw_blocks)}")
        save_analysis(raw_blocks, output_dir, verbose=verbose_mode)
        print(f"Saved detailed LLM input/output to folder: {output_dir}")
        from crewai_log_parser.models.parsed_block import ParsedBlock
        parsed_blocks = [ParsedBlock(**block) for block in raw_blocks]
        unified_analysis(parsed_blocks, verbose=verbose_mode)

    if verbose_mode:
        if task_aware_mode and (tasks_yaml_path or agents_yaml_path):
            errors = sum(1 for block in enhanced_blocks if block.parsing_error)
            print(f"\n--- Parsing Summary ---")
            print(f"Total parsing errors: {errors} out of {len(enhanced_blocks)} calls")
            final_answers = sum(1 for block in enhanced_blocks if block.final_answer)
            print(f"Final answers detected: {final_answers} out of {len(enhanced_blocks)} calls")
            matched_tasks = sum(1 for block in enhanced_blocks if block.task_id)
            print(f"Blocks matched to tasks: {matched_tasks} out of {len(enhanced_blocks)} calls")
            matched_agents = sum(1 for block in enhanced_blocks if block.agent_id)
            print(f"Blocks matched to agents: {matched_agents} out of {len(enhanced_blocks)} calls")
        else:
            errors = sum(1 for block in raw_blocks if block.get('parsing_error', False))
            print(f"\n--- Parsing Summary ---")
            print(f"Total parsing errors: {errors} out of {len(raw_blocks)} calls")
            final_answers = sum(1 for block in raw_blocks if block.get('final_answer'))
            print(f"Final answers detected: {final_answers} out of {len(raw_blocks)} calls")

if __name__ == "__main__":
    main()
