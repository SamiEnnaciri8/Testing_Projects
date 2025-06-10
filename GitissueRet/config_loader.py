"""
Configuration loader for GitHub Issues Retriever Tool.
This module handles loading configuration from YAML files.
"""

import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from langchain_ollama import ChatOllama
from github_issues_retriever_tool import GithubIssuesRetrieverTool


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        Dictionary containing the configuration data
        
    Raises:
        FileNotFoundError: If the config file doesn't exist
        yaml.YAMLError: If the YAML file is malformed
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
            
        if not config:
            raise ValueError("Configuration file is empty or invalid")
            
        return config
        
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML configuration: {e}")


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate that the configuration contains required fields.
    
    Args:
        config: Configuration dictionary to validate
        
    Raises:
        ValueError: If required configuration is missing
    """
    required_fields = ["github_token"]
    
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Required configuration field missing: {field}")
    
    if not config["github_token"]:
        raise ValueError("GitHub token cannot be empty")


def create_tool_from_config(config_path: str) -> GithubIssuesRetrieverTool:
    """
    Create a GithubIssuesRetrieverTool instance from a YAML configuration file.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        Configured GithubIssuesRetrieverTool instance
        
    Example config.yaml:
        ```yaml
        github_token: "your_github_token_here"
        ollama_model: "llama2"  # optional, defaults to "llama2"
        ```
    """
    # Load and validate configuration
    config = load_config(config_path)
    validate_config(config)
    
    # Create Ollama LLM instance with specified model
    model_name = config.get("ollama_model", "llama2")
    llm = ChatOllama(model=model_name)
    
    # Create and return the tool
    return GithubIssuesRetrieverTool(
        access_token=config["github_token"],
        llm=llm,
    )


def create_example_config(output_path: str) -> None:
    """
    Create an example configuration file with placeholder values.
    
    Args:
        output_path: Path where to create the example config file
    """
    example_config = {
        "github_token": "your_github_personal_access_token_here",
        "ollama_model": "llama2",  # Optional: can be llama2, llama3, codellama, etc.
    }
    
    output_file = Path(output_path)
    
    with open(output_file, 'w') as file:
        yaml.dump(example_config, file, default_flow_style=False, indent=2)
    
    print(f"Example configuration created at: {output_path}")
    print("Please edit the file and add your actual GitHub token.")


# Convenience function for backward compatibility
def from_config(path: str) -> GithubIssuesRetrieverTool:
    """
    Legacy function name for backward compatibility.
    Use create_tool_from_config() for new code.
    """
    return create_tool_from_config(path)


if __name__ == "__main__":
    # Create an example configuration file if run directly
    create_example_config("example_config.yaml")
