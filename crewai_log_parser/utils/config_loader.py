import yaml
from typing import Dict
from crewai_log_parser.models.config_models import CrewAITask, CrewAIAgent

def load_tasks(yaml_path: str) -> Dict[str, CrewAITask]:
    """Load and parse tasks from a YAML file"""
    tasks_dict = {}
    try:
        with open(yaml_path, 'r') as file:
            yaml_content = yaml.safe_load(file)
        for task_id, task_data in yaml_content.items():
            # Extract dependencies from description (heuristic)
            dependencies = []
            if 'description' in task_data:
                desc = task_data['description']
                for potential_dep in yaml_content.keys():
                    if potential_dep != task_id and f"'{potential_dep}'" in desc:
                        dependencies.append(potential_dep)
            tasks_dict[task_id] = CrewAITask(
                task_id=task_id,
                description=task_data.get('description', ''),
                expected_output=task_data.get('expected_output', ''),
                agent=task_data.get('agent', ''),
                dependencies=dependencies
            )
    except Exception as e:
        print(f"Error loading tasks: {str(e)}")
    return tasks_dict

def load_agents(yaml_path: str) -> Dict[str, CrewAIAgent]:
    """Load and parse agents from a YAML file"""
    agents_dict = {}
    try:
        with open(yaml_path, 'r') as file:
            yaml_content = yaml.safe_load(file)
        for agent_id, agent_data in yaml_content.items():
            agents_dict[agent_id] = CrewAIAgent(
                role=agent_data.get('role', ''),
                goal=agent_data.get('goal', ''),
                backstory=agent_data.get('backstory', ''),
                allow_delegation=agent_data.get('allow_delegation', False),
                verbose=agent_data.get('verbose', False)
            )
    except Exception as e:
        print(f"Error loading agents: {str(e)}")
    return agents_dict
