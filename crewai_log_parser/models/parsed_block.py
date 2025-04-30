from typing import Optional, List

class ParsedBlock:
    def __init__(
        self,
        task_hint: str,
        litellm_request: str,
        raw_response: str,
        thought: Optional[str] = None,
        action: Optional[str] = None,
        final_answer: Optional[str] = None,
        parsed_usage: Optional[dict] = None,
        parsing_error: bool = False,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        model: Optional[str] = None,
        api_errors: Optional[List[str]] = None,   
    ):
        self.task_hint = task_hint
        self.litellm_request = litellm_request
        self.raw_response = raw_response
        self.thought = thought
        self.action = action
        self.final_answer = final_answer
        self.parsed_usage = parsed_usage or {}
        self.parsing_error = parsing_error
        self.start_time = start_time
        self.end_time = end_time
        self.model = model
        self.api_errors = api_errors or []
