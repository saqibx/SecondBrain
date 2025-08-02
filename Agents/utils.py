from dotenv import load_dotenv
from typing import Annotated, List, Dict, Union, Sequence
from typing_extensions import TypedDict

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

tools = []
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    doc: str
    email: str

model = ChatOpenAI(model='gpt-4o').bind_tools(tools)