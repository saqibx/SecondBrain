from dotenv import load_dotenv
from typing import Annotated, Sequence
from typing_extensions import TypedDict
from tavily import TavilyClient
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
import os
import time

load_dotenv()

# ---- STATE ----
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    doc: str
    email: str

# ---- TOOLS ----
@tool
def refine(topic: str) -> str:
    """Research a topic using Tavily and summarize key points."""
    client = TavilyClient(os.getenv("TAVILY_API_KEY"))
    search = client.search(query=topic)
    url_list = [item["url"] for item in search['results']][:3]
    extract = client.extract(urls=url_list)

    summarized = []
    for raw in extract['results']:
        text = raw["raw_content"]
        url = raw.get("url", "")
        prompt = f"Summarize this article in 5 bullet points max. Skip ads. Content:\n{text}"
        time.sleep(4)
        answer = model.invoke(prompt)
        summary = f"{answer.content.strip()}\n(Source: {url})"
        summarized.append(summary)

    return "\n\n---\n\n".join(summarized)


@tool
def email_drafter(email_contents: str) -> str:
    """Draft a professional email using provided content."""
    prompt = f'''
    You are Saqib Mazhar, Co-VP External of Tech Start UCalgary, a student-led startup incubator.
    Based on the content below, write a professional but human-sounding email. Avoid buzzwords.

    Content: {email_contents}
    '''
    response = model.invoke(prompt)
    return response.content


@tool
def save(filename: str, content: str) -> str:
    """Save content to a file."""
    if not filename.endswith(".txt"):
        filename += ".txt"
    try:
        with open(filename, 'w') as f:
            f.write(content)
        return f"Document saved as {filename}"
    except Exception as e:
        return f"Failed to save: {e}"

tools = [refine, email_drafter, save]
model = ChatOpenAI(model="gpt-4o").bind_tools(tools)

# ---- SMART AGENT ----
def smart_agent(state: AgentState) -> AgentState:
    if not state['messages']:
        user_input = input("What do you want help with? (e.g., write an email to Enbridge): ")
        state['messages'] = [HumanMessage(content=user_input)]

    # Don't keep appending HumanMessage every loop
    # Just use what’s already there

    sys_prompt = SystemMessage(content="""
    You are an assistant who can:
    - Use `refine()` to research
    - Use `email_drafter()` to write professional emails
    - Use `save()` to store finished content

    IF ASKED TO RESEARCH ONLY DO IT ONCE, NO MORE.
    If the user's question has been resolved, call save() and stop.
    If you’ve already handled their request, do not repeat it again.
    """)

    response = model.invoke([sys_prompt] + list(state['messages']))
    return {
        "messages": state['messages'] + [response],
        "doc": state.get("doc", ""),
        "email": state.get("email", "")
    }


# ---- CONDITIONAL STOPPER ----
def should_continue(state: AgentState) -> str:
    for msg in reversed(state['messages']):
        if isinstance(msg, ToolMessage) and "document saved" in msg.content.lower():
            return "end"
    if state.get("doc") and state.get("email"):
        return "end"
    return "agent"

# ---- GRAPH ----
graph = StateGraph(AgentState)
graph.add_node("agent", smart_agent)
graph.add_node("tools", ToolNode(tools))
graph.set_entry_point("agent")
graph.add_edge("agent", "tools")
graph.add_conditional_edges("tools", should_continue, {
    "agent": "agent",
    "end": END
})

app = graph.compile()

# ---- RUN LOOP ----
def run():
    print("\n=== AGENTIC EMAIL + RESEARCH SYSTEM ===")
    state = {"messages": [], "doc": "", "email": ""}
    for step in app.stream(state, stream_mode="values"):
        if "messages" in step:
            for msg in step["messages"]:
                print(f"\n🔹 {type(msg).__name__}: {msg.content.strip()}")
    print("\n=== DONE ===")

if __name__ == "__main__":
    run()
