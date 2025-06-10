"""
Example usage of the GitHub Issues Retriever Tool with configuration.
"""

from config_loader import create_tool_from_config, create_example_config
from github_issues_retriever_tool import GithubIssuesRetrieverTool


def main():
    """
    Example of how to use the GitHub Issues Retriever Tool with configuration.
    """
    
    # First time setup: create an example config file
    # Uncomment the line below to create a template config file
    # create_example_config("config.yaml")
    
    try:
        # Load the tool from configuration
        tool = create_tool_from_config("config.yaml")
        
        # Example: Fetch a specific issue
        result = tool._run(
            repo_name="octocat/Hello-World",
            issue_number=1,
            chunk_size=500,
            chunk_overlap=50
        )
        
        # Print the results
        for issue_record in result.issues:
            print(f"\n{'='*60}")
            print(f"Issue #{issue_record.issue_number}")
            print(f"{'='*60}")
            
            print(f"\n📝 Summary:")
            print(issue_record.summary)
            
            print(f"\n🔗 Links found: {len(issue_record.links)}")
            for link in issue_record.links:
                print(f"   • {link.url}")
            
            print(f"\n📄 Text chunks: {len(issue_record.chunks)}")
            for i, chunk in enumerate(issue_record.chunks[:3]):  # Show first 3 chunks
                print(f"   Chunk {i+1}: {chunk.text[:100]}...")
    
    except FileNotFoundError:
        print("Configuration file not found. Creating example config...")
        create_example_config("config.yaml")
        print("Please edit config.yaml with your GitHub token and run again.")
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
