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
def refine(email_contents: str) -> str:
    '''This is an email drafting tool'''
    email_prompt = SystemMessage(content=f'''
        The contents attached below will give you everything you need to write the perfect email. For reference my name is
        Saqib Mazhar, I am the Co-VP External of Tech Start UCalgary, A student-led start-up incubator here at the University of 
        Calgary.
        
        Draft a professional, yet human sounding email,
        
        Here is the context: {email_contents}
        ''')

    response = model.invoke(email_prompt)
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




tools = [refine,save]
model = ChatOpenAI(model='gpt-4o').bind_tools(tools)

def research_agent(state:AgentState)->AgentState:
    '''This is the main agent that does our work'''
    sys_prompt = SystemMessage(content=f"""
        
        You are my helpful assistant that will help me write better emails to secure meetings and sponsorships with
        tech industry professionals here in Calgary. You are aware that I am the Co-VP External of Tech Start UCalgary, 
        A student led start-up incubator here at the University of Calgary.
        
        you have the responsibility of drafting an email based on the content I provide you with. Keep a natural human tone, 
        no buzz words or classic AI phrases. Keep it Human sounding.
        
        here is the content, summarize it and hit all key points, then give me a draft of what you came up with.
        
        Content: {state["email"]}
        """)

    if not state['messages'] and state['email']:
        prompt_text = "Hi there, I need some assistance"
        user_message = HumanMessage(content=prompt_text)

    else:
        user_input = input("\nWhat would you like me to research? ")
        user_message = HumanMessage(content=user_input)

    all_messages = [sys_prompt] + list(state['messages']) + [user_message]
    response = model.invoke(all_messages)


    state['email'] = response.content




    print("========= AI =========")
    print(f"\n🤖 AI: {response.content}")
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"🔧 USING TOOLS: {[tc['name'] for tc in response.tool_calls]}")

    return {"messages": list(state["messages"]) + [user_message, response], "email": state['email']}



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
    state = {"messages": [], "doc": "", "email": ""}

    for step in app.stream(state, stream_mode="values"):
        if 'messages' in step:
            print_messages(step['messages'])

    print("\n==== DRAFTER DONE ====")

if __name__ == "__main__":
    run()