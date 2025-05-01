import re
import json
from typing import List, Dict, Tuple, Optional, Any
from crewai_log_parser.models.enhanced_parsed_block import EnhancedParsedBlock, TokenUsage
from crewai_log_parser.models.config_models import CrewAITask, CrewAIAgent
from crewai_log_parser.utils.config_loader import load_tasks, load_agents

class ConfigAwareLogParser:
    def __init__(self, tasks_yaml_path: Optional[str] = None, agents_yaml_path: Optional[str] = None):
        self.tasks = load_tasks(tasks_yaml_path) if tasks_yaml_path else {}
        self.agents = load_agents(agents_yaml_path) if agents_yaml_path else {}

    def _match_task_to_block(self, block: Dict) -> Optional[str]:
        task_hint = block.get('task_hint', '').lower()
        for task_id, task in self.tasks.items():
            desc_simple = task.description.lower()
            if task_id.lower() in task_hint or any(phrase in task_hint for phrase in desc_simple.split('.')[:2]):
                return task_id
        for task_id, task in self.tasks.items():
            if task.expected_output.lower() in block.get('raw_response', '').lower():
                return task_id
        return None

    def _match_agent_to_block(self, block: Dict) -> Optional[str]:
        litellm_request = block.get('litellm_request', '').lower()
        for agent_id, agent in self.agents.items():
            if agent.role.lower() in litellm_request:
                return agent_id
        return None

    def _extract_tool_info(self, block: Dict) -> Tuple[Optional[str], Optional[Dict], Optional[str], Optional[bool]]:
        tool_used = None
        tool_input = None
        tool_output = None
        tool_success = None
        action = block.get('action', '')
        if action:
            tool_match = re.search(r'^(.*?)(?:\s*\(|\s*:|\s*$)', action)
            if tool_match:
                tool_used = tool_match.group(1).strip()
        litellm_request = block.get('litellm_request', '')
        input_match = re.search(r'Action Input:\s*({.*?})', litellm_request, re.DOTALL)
        if input_match:
            try:
                tool_input = json.loads(input_match.group(1))
            except Exception:
                pass
        raw_response = block.get('raw_response', '')
        output_match = re.search(r'Observation:\s*(.*?)(?:\n\n|$)', raw_response, re.DOTALL)
        if output_match:
            tool_output = output_match.group(1).strip()
        if tool_output and not "error" in tool_output.lower():
            tool_success = True
        elif "error" in raw_response.lower():
            tool_success = False
        return tool_used, tool_input, tool_output, tool_success

    def parse_log_file(self, log_path: str, verbose: bool = False) -> List[EnhancedParsedBlock]:
        from crewai_log_parser.parsers.log_parser_v2 import parse_log_file_v2
        raw_blocks, _ = parse_log_file_v2(log_path, verbose=verbose)
        enhanced_blocks = []
        for block in raw_blocks:
            task_id = self._match_task_to_block(block)
            agent_id = self._match_agent_to_block(block)
            tool_used, tool_input, tool_output, tool_success = self._extract_tool_info(block)
            token_usage = None
            if block.get('parsed_usage'):
                token_usage = TokenUsage(
                    prompt_tokens=block['parsed_usage'].get('prompt_tokens', 0),
                    completion_tokens=block['parsed_usage'].get('completion_tokens', 0),
                    total_tokens=block['parsed_usage'].get('total_tokens', 0),
                    cost_usd=block['parsed_usage'].get('cost_usd', 0.0)
                )
            enhanced_block = EnhancedParsedBlock(
                task_hint=block.get('task_hint', ''),
                litellm_request=block.get('litellm_request', ''),
                raw_response=block.get('raw_response', ''),
                thought=block.get('thought'),
                action=block.get('action'),
                final_answer=block.get('final_answer'),
                parsed_usage=token_usage,
                parsing_error=block.get('parsing_error', False),
                start_time=block.get('start_time'),
                end_time=block.get('end_time'),
                model=block.get('model'),
                api_errors=block.get('api_errors', []),
                task_id=task_id,
                agent_id=agent_id,
                expected_output_format=self.tasks.get(task_id).expected_output if task_id and task_id in self.tasks else None,
                dependencies=self.tasks.get(task_id).dependencies if task_id and task_id in self.tasks else [],
                tool_used=tool_used,
                tool_input=tool_input,
                tool_output=tool_output,
                tool_success=tool_success
            )
            enhanced_blocks.append(enhanced_block)
        return enhanced_blocks
