from dotenv import load_dotenv
from typing import Annotated, List, Dict, Union, Sequence
from typing_extensions import TypedDict
from tavily import TavilyClient
import os
import time
from utils import AgentState, model


'''
Annotated - Adds meta data to our variable
Sequence - Automaticallu handles the state ipdates for sequences such as by adding new messages
add_message - reducer function that helps append updates from nodes to your state
'''
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, HumanMessage
'''
Base Message - Foundational Class for all message types in LangGraph
Tool Message - Passes data back to LLM after it calls a tool such as the content and the tool_call_id
System Message - Message for providing instructions to the LLM
'''
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

load_dotenv()




@tool
def refine(topic: str) -> str:
    '''This is a researching tool that finds and summarizes articles'''
    client = TavilyClient(os.getenv("TAVILY_API_KEY"))
    search = client.search(query=topic)

    url_list = [item["url"] for item in search['results']][:3]
    extract = client.extract(urls=url_list)

    summarized_articles = []

    for raw in extract['results']:
        text = raw["raw_content"]
        url = raw.get("url", "")

        sum_prompt = f"""Summarize this article in 5-6 bullet points. DO NOT exceed that.
Include any useful links related to the topic at the end. Skip ads or irrelevant content.

Content:
{text}
        """
        time.sleep(8)
        answer = model.invoke(sum_prompt)
        summary = f"{answer.content.strip()}\n(Source: {url})"
        summarized_articles.append(summary)

    return "\n\n---\n\n".join(summarized_articles)


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




tools = [refine,save]


def research_agent(state:AgentState)->AgentState:
    '''This is the main agent that does our work'''
    sys_prompt = SystemMessage(content=f"""
        You are an expert research assistant. Here's how you must behave:

        - When you receive research results from the refine tool, your job is to:
            1. Read the research carefully
            2. Extract key points and insights (DO NOT repeat the entire article)
            3. Format your reply as bullet points or brief sections (max 5–7 key takeaways)
            4. Include a "Sources" section at the end with all relevant URLs
            5. Once you have returned your research include a brief entry giving a TLDR.
        - DO NOT dump full paragraphs from the original research.
        - When the user wants additional research, call the refine tool again.
        - When the research is complete, call the save tool and pass the filename and document content.

        Current document content: {state["doc"]}
        """)

    if not state['messages'] and state['doc']:
        prompt_text = "Hi there, I need some assistance"
        user_message = HumanMessage(content=prompt_text)

    else:
        user_input = input("\nWhat would you like me to research? ")
        user_message = HumanMessage(content=user_input)

    all_messages = [sys_prompt] + list(state['messages']) + [user_message]
    response = model.invoke(all_messages)

    tool_data = response.tool_calls


    state['doc'] = response.content




    print("========= AI =========")
    print(f"\n🤖 AI: {response.content}")
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"🔧 USING TOOLS: {[tc['name'] for tc in response.tool_calls]}")

    return {"messages": list(state["messages"]) + [user_message, response], "doc": state['doc']}



def cont(state:AgentState)->str:
    '''determines whether or not we should continue refining, if not then decides to save'''

    messages = state['messages']
    if not messages:
        return "continue"

    for message in reversed(messages):
        if (isinstance(message, ToolMessage) and
        "saved" in message.content.lower() and
        "document" in message.content.lower()):
            return "end"

    return "continue"



graph = StateGraph(AgentState)
graph.add_node("research_agent", research_agent)
graph.add_node("tools", ToolNode(tools))
graph.set_entry_point("research_agent")
graph.add_edge("research_agent","tools")

graph.add_conditional_edges(
    "tools",
    cont,
    {
        "continue": "research_agent",
        "end": END
    }
)

app = graph.compile()

def print_messages(messages):
    '''function that prints messages in a more readable format'''
    if not messages:
        return

    for message in messages[-3:]:
        if isinstance(message,ToolMessage):
            print(f"TOOL RESULT: {message.content}")


def run():
    print("\n===== DRAFTER ====")
    state = {"messages": [], "doc": ""}

    for step in app.stream(state, stream_mode="values"):
        if 'messages' in step:
            print_messages(step['messages'])

    print("\n==== DRAFTER DONE ====")

if __name__ == "__main__":
    run()