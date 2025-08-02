from dotenv import load_dotenv
from typing import Annotated, List, Dict, Union, Sequence, TypedDict
'''
Annotated - Adds meta data to our variable
Sequence - Automaticallu handles the state ipdates for sequences such as by adding new messages
add_message - reducer function that helps append updates from nodes to your state
'''
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage
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

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

@tool
def add(a:int, b:int):
    '''This is an addition function that adds two numbers together'''

    return a+b

@tool
def subtract(a:int, b:int):
    '''This is a subtraction function'''
    return a-b

@tool
def multiply(a:int,b:int):
    '''This is a multiplication function'''
    return a*b

tools = [add, subtract, multiply]

model = ChatOpenAI(model="gpt-4o").bind_tools(tools)

def model_call(state:AgentState)->AgentState:
    system_prompt = SystemMessage(content="You are my AI assistant, please answer my query")

    response = model.invoke([system_prompt] + state['messages'])
    return {"messages":[response]}
    # Another way of updating state, same as state['messages'] = response


def scontinue(state:AgentState)->AgentState:
    messages = state["messages"]
    last_message = messages[-1]

    if not last_message.tool_calls:
        return "end"
    else:
        return "continue"



graph = StateGraph(AgentState)
graph.add_node("our_agent", model_call)

tool_node = ToolNode(tools=tools)
graph.add_node("tools", tool_node)

graph.set_entry_point("our_agent")

graph.add_conditional_edges(
    "our_agent",
    scontinue,

    {
        "continue": 'tools',
        "end": END
    }
)

graph.add_edge("tools", "our_agent")

app = graph.compile()


def print_stream(stream):
    for s in stream:
        message = s["messages"][-1]
        if isinstance(message, tuple):
            print(message)
        else:
            message.pretty_print()

inputs = {"messages": [("user", " (1+5) * (9-5) + (3*5)")]}
print_stream(app.stream(inputs, stream_mode="values"))