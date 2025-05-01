from typing import List, Dict, Optional, Set
from crewai_log_parser.models.enhanced_parsed_block import EnhancedParsedBlock
from crewai_log_parser.models.config_models import CrewAITask, CrewAIAgent

class WorkflowNode:
    """Represents a node in the workflow graph"""
    def __init__(self, task_id: str, blocks: List[EnhancedParsedBlock] = None):
        self.task_id = task_id
        self.blocks = blocks or []
        self.dependencies = set()
        self.dependents = set()

    def add_dependency(self, task_id: str):
        self.dependencies.add(task_id)

    def add_dependent(self, task_id: str):
        self.dependents.add(task_id)

    @property
    def total_tokens(self) -> int:
        return sum(block.parsed_usage.total_tokens for block in self.blocks if block.parsed_usage is not None)

    @property
    def total_cost(self) -> float:
        return sum(block.parsed_usage.cost_usd for block in self.blocks if block.parsed_usage is not None)

    @property
    def success_rate(self) -> float:
        if not self.blocks:
            return 0.0
        return sum(1 for block in self.blocks if block.final_answer) / len(self.blocks)

    @property
    def agent_id(self) -> Optional[str]:
        for block in self.blocks:
            if block.agent_id:
                return block.agent_id
        return None

class WorkflowReconstructor:
    """Reconstructs the workflow from parsed blocks"""
    def __init__(self, blocks: List[EnhancedParsedBlock], tasks: Dict[str, CrewAITask], agents: Dict[str, CrewAIAgent]):
        self.blocks = blocks
        self.tasks = tasks
        self.agents = agents
        self.nodes: Dict[str, WorkflowNode] = {}

    def reconstruct(self) -> Dict[str, WorkflowNode]:
        # Group blocks by task
        task_blocks: Dict[str, List[EnhancedParsedBlock]] = {}
        for block in self.blocks:
            if block.task_id:
                if block.task_id not in task_blocks:
                    task_blocks[block.task_id] = []
                task_blocks[block.task_id].append(block)
        # Create nodes for each task
        for task_id, blocks in task_blocks.items():
            self.nodes[task_id] = WorkflowNode(task_id, blocks)
        # Add dependencies from task definitions
        for task_id, task in self.tasks.items():
            if task_id in self.nodes:
                for dep in task.dependencies:
                    if dep in self.nodes:
                        self.nodes[task_id].add_dependency(dep)
                        self.nodes[dep].add_dependent(task_id)
        return self.nodes

    def generate_mermaid_diagram(self) -> str:
        if not self.nodes:
            self.reconstruct()
        mermaid_code = "graph TD\n"
        # Add nodes
        for task_id, node in self.nodes.items():
            agent_id = node.agent_id or "unknown"
            tokens = node.total_tokens
            cost = node.total_cost
            success = node.success_rate * 100
            mermaid_code += f"    {task_id}[{task_id}<br/>Agent: {agent_id}<br/>Tokens: {tokens}<br/>Cost: ${cost:.6f}<br/>Success: {success:.1f}%]\n"
        # Add edges
        for task_id, node in self.nodes.items():
            for dep in node.dependencies:
                mermaid_code += f"    {dep} --> {task_id}\n"
        return mermaid_code
