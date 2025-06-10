# test_github_tool.py

from config_loader import from_config

def main():


    
    # 1) Load your token + optional Ollama model from config.yaml
    tool = from_config("config.yaml")

    # 2) Call the tool: fetch issue #1 from a small repo you control
    resp = tool._run(
        repo_name="AI-Emerging-Tech/ET-SDLC-App-Maintenance",
        state="open",
        issue_number=1,
        chunk_size=800,
        chunk_overlap=50,
    )

    # 3) Print out each issue’s summary
    for record in resp.issues:
        print(f"\n--- Issue #{record.issue_number} Summary ---")
        print(record.summary)
        print(f"Chunks returned: {len(record.chunks)}")
        print(f"Links fetched: {[link.url for link in record.links]}")

if __name__ == "__main__":
    main()
