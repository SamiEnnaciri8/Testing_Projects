import re
import requests
from typing import List, Optional, Type
from pydantic import BaseModel, ConfigDict, Field
from github import Github

# Ollama integration 
from langchain_ollama import ChatOllama  
from langchain.tools import BaseTool
from langchain.callbacks.manager import (
    CallbackManagerForToolRun,
    AsyncCallbackManagerForToolRun,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.messages import SystemMessage, HumanMessage




#this defines what parameters the tool accepts from the agent
class GithubIssuesRetrieverArgs(BaseModel):
    """
    Inputs for the GitHub Issues Retriever tool.
    """
    repo_name: str = Field(
        ..., description="GitHub repo in 'owner/repo' format, e.g. 'octocat/Hello-World'"
    )
    state: Optional[str] = Field(
        "open", description="Filter issues by state: 'open', 'closed', or 'all'"
    )
    issue_number: Optional[int] = Field(
        None, description="If provided, fetch only this specific issue number"
    )
    chunk_size: int = Field(
        1000, description="Maximum characters per chunk when splitting text"
    )
    chunk_overlap: int = Field(
        100, description="Number of overlapping characters between adjacent chunks"
    )


#This is the structure of what the tool returns to the agent


#THe purpose of this class is to represent a hyperlink found in an issue and its fetched content.
class IssueLinkDoc(BaseModel):
    """
    Represents one extracted hyperlink and its fetched content.
        - we take the original HTTP/HTTPS link found in the issue text
        - fetch the page content and store the first 50k characters
        - this is useful for RAG/vector retrieval tasks
    """
    url: str = Field(..., description="The original HTTP(s) link found in the issue")
    content: str = Field(..., description="First 50k characters of the fetched page text")


#this classes purpose is to represent a single chunk of text from an issue 
class IssueChunk(BaseModel):
    """
    A single chunk of an issue+comments, ready for embedding or summarization.
    - issue_number: the GitHub issue number this chunk belongs to
    - chunk_index: sequential index of this chunk within the issue
    - text: the actual text content of this chunk
    """
    issue_number: int = Field(..., description="The GitHub issue number")
    chunk_index: int = Field(..., description="Sequential index of this chunk")
    text: str = Field(..., description="Portion of the combined issue body + comments")


#this class contains all the processed data about a single GitHub issue
class IssueRecord(BaseModel):
    """
    All data about one issue after processing:
      - its number
      - a short LLM-generated summary
      - any link docs we fetched
      - its text chunks
    """
    issue_number: int
    summary: str
    links: List[IssueLinkDoc]
    chunks: List[IssueChunk]


#The comlplete response structure returned by the tool here.
class GithubIssuesRetrieverResponse(BaseModel):
    """
    The tool’s full response: a list of processed IssueRecords.
    """
    issues: List[IssueRecord]


#This class is the main tool that agents will use to retrieve GitHub issues.
class GithubIssuesRetrieverTool(BaseTool):
    """
    Fetch a GitHub issue (or all issues), grab comments + links,
    summarize with Ollama, chunk text for RAG/vector retrieval.
    """
    name: str = "github_issues_retriever"
    description: str = (
        "Use to fetch issues from GitHub, extract comments & links, "
        "produce a bullet-point summary, and split text into chunks."
    )
    args_schema: Type[BaseModel] = GithubIssuesRetrieverArgs
    return_direct: bool = False
    client: Github = None
    llm: ChatOllama = None
    summary_chain: Runnable = None
    model_config = ConfigDict(arbitrary_types_allowed=True)




    # the function initializes the tool with a GitHub access token and an ollama instance
    # Creates a github client using the token and then sets up an Ollama LLM for summarization.
    #Also creates a langChain prompt template for summarization and builds a chain combining the llm and the prompt.
    def __init__(self, access_token: str, llm: Optional[ChatOllama] = None, **kwargs):
        """
        - access_token: Personal Access Token for the GitHub API.
        - llm: Optional Ollama instance; if omitted, defaults to Ollama(model='deepseek-r1:14b').
        """
        super().__init__(**kwargs)
        self.client = Github(access_token)
        # Initialize Ollama LLM for summarization:
        self.llm = llm or ChatOllama(model="deepseek-r1:14b")
        # Build a prompt chain for generating bullet-point summaries
        
        
        


        #This is the main function that performs all the steps to retrieve and process GitHub issues.
    #It fetches the issue(s), concatenates title, body, and comments, extracts links, fetches their content,
    #summarizes the full text using the Ollama LLM, splits it into manageable chunks, and returns a structured response.
    def _run(
        self,
        repo_name: str,
        state: str = "open",
        issue_number: Optional[int] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> GithubIssuesRetrieverResponse:
        """
        1. Fetch the repo and desired issue(s)
        2. Concatenate title + body + all comments into one text blob
        3. Extract all HTTP(s) links, fetch each page’s content
        4. Summarize the full blob with the Ollama LLM
        5. Split (chunk) the blob into manageable pieces
        6. Return a GithubIssuesRetrieverResponse containing:
           - summary bullets
           - link docs
           - text chunks
        """

        prompt = """
Summarize the following GitHub issue and its comments 
into concise bullet points:\n\n{text}\n\nBULLETS:
                """
        repo = self.client.get_repo(repo_name)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

        records: List[IssueRecord] = []
        # Gets the github repo object, and fetches either a specific issue or all issues based on the provided parameters.
        # If issue_number is provided, fetch that specific issue; otherwise, fetch all issues in the given state.
        # Note: state can be 'open', 'closed', or 'all' (default is 'open')
        issues = (
            [repo.get_issue(number=issue_number)]
            if issue_number is not None
            else list(repo.get_issues(state=state))
        )

        for issue in issues:
            # Combines issue title, body, and all comments into one text blob. and then adds "[Comment]" marker to distinguish from the main issue.
            full_text = issue.title + "\n\n" + (issue.body or "")
            for comment in issue.get_comments():
                full_text += "\n\n[Comment]\n" + comment.body

            # Uses regex to find all the HTTPS/HTTP links in the full text.
            # Fetches the content of each link, capping it to the first 50,000 characters.
            #Fetches the content of each URL with a 5 second timeout.
            urls = re.findall(r"https?://\S+", full_text)
            
            # Add the repository URL itself to the list of URLs to fetch
            repo_url = f"https://github.com/{repo_name}"
            if repo_url not in urls:
                urls.append(repo_url)
            
            link_docs: List[IssueLinkDoc] = []
            for url in urls:
                try:
                    resp = requests.get(url, timeout=5)
                    content = resp.text[:50_000]  # cap to first 50k chars
                except Exception:
                    content = ""
                link_docs.append(IssueLinkDoc(url=url, content=content))

            #This is the summary part. This uses LangChain pipeline to generate a bullet point summary. 
            #The Ai model analyzes the full issue text and creates concise bullet points.
            # summary = self.summary_chain.invoke(full_text)
            summary = self.llm.with_structured_output(IssueRecord, method = "json_schema").invoke([
                SystemMessage(
                
                content= prompt)
                
                , HumanMessage(content= full_text)
                ])


           

            #Packages all the processed data into a structured record and each issue becomes one issue record with all its data.
              
            records.append(
                summary
            )

        return GithubIssuesRetrieverResponse(issues=records)


     #This is for later implementation but basically async function in langchain allows a program to perform multiple tasks at the same time without blocking the execution of other tasks.
    #For now, it simply calls the synchronous _run method.
    async def _arun(
        self,
        repo_name: str,
        state: str = "open",
        issue_number: Optional[int] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> GithubIssuesRetrieverResponse:
        """
        Async entrypoint: for now simply delegates to the sync _run.
        Agents calling .ainvoke() will use this.
        """
        return self._run(repo_name, state, issue_number, chunk_size, chunk_overlap)

