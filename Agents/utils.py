from dotenv import load_dotenv
from typing import Annotated, List, Dict, Union, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

load_dotenv()
combined_tools = []

model = ChatOpenAI(model="gpt-4o").bind_tools([])

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    doc: str
    email: str
