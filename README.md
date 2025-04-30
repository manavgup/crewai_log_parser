# Implementation Guide for Log Filtering

This guide explains how to implement the log filtering solution to clean up the "wall of text" output on your console.

## Problem

The CrewAI logs contain tool usage output that creates a "wall of text" in the console output, which includes:
- Tool: entries 
- Action Input: entries with large JSON payloads
- Usage information and token counts embedded in the logs
- "Times Used: N" entries

## Solution Components

1. **Log Filtering Function** - Filters out tool logs and other noisy content
2. **Modified CLI** - Pre-processes logs to remove noise before analysis
3. **Final Log Parser** - Enhanced to better extract token usage data

## Implementation Steps

### 1. Create the log_filter.py file

Create this file in the `crewai_log_parser/utils/` folder:

```python
# crewai_log_parser/utils/log_filter.py
def filter_tool_logs(log_content: str) -> str:
    """Filter out tool logs and other verbose content from log files."""
    import re
    
    # Lines to filter out (exact matches)
    filter_patterns = [
        r'^Tool: .*$',                           # Tool: lines
        r'^Action Input: .*$',                   # Action Input: lines
        r'.*"usage": \{.*\}.*$',                 # Lines containing usage data
        r'.*"completion_tokens": \d+.*$',        # Lines with completion tokens
        r'.*"prompt_tokens": \d+.*$',            # Lines with prompt tokens
        r'.*"total_tokens": \d+.*$',             # Lines with total tokens
        r'.*"tool_calls": .*$',                  # Lines with tool calls  
        r'.*"function_call": .*$',               # Lines with function calls
        r'.*Times Used: \d+$',                   # "Times Used: N" lines
    ]
    
    # Compile all patterns
    regex_patterns = [re.compile(pattern, re.MULTILINE) for pattern in filter_patterns]
    
    # Filter line by line
    filtered_lines = []
    lines = log_content.split('\n')
    
    for line in lines:
        # Skip if any pattern matches
        if any(pattern.match(line) for pattern in regex_patterns):
            continue
            
        # Skip long JSON blobs
        if len(line) > 300 and ('{' in line and '}' in line):
            continue
            
        filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)
```

### 2. Replace the CLI with the Modified Version

Update `cli.py` with the modified version that filters logs before processing:

- Creates a temporary filtered log file for processing
- Adds a `--raw` flag to bypass filtering if needed
- Processes the filtered log instead of the raw log

### 3. Update the Log Parser

Replace `log_parser_v2.py` with the final version that includes:
- Better token extraction
- Improved regex patterns
- Multiple extraction methods to ensure token counts are found

## Usage

Run with default filtering:
```bash
python -m crewai_log_parser.cli /path/to/log_file.log logs/analysis
```

Run with raw unfiltered logs (if needed):
```bash
python -m crewai_log_parser.cli /path/to/log_file.log logs/analysis --raw
```

## Folder Structure

```
crewai_log_parser/
├── parsers/
│   └── log_parser_v2.py  # Replace with final-log-parser-v2
├── analyzers/
│   └── unified_analyzer.py  # Keep this unchanged
├── utils/
│   └── log_filter.py  # Add this new file
└── cli.py  # Replace with modified-cli
```

## Troubleshooting

If you see issues with the filtering:

1. Ensure the `utils` folder exists and is recognized as a Python package (has an `__init__.py` file)
2. Add more filter patterns if you see other types of noisy output
3. Use the `--raw` flag to compare raw vs. filtered output
4. Adjust the "long JSON blob" threshold (300 characters) if needed

The filtered logs will be processed exactly the same way for token extraction and analysis, but without the wall of text in your console output.