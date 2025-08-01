from dotenv import load_dotenv
from typing import Annotated, Literal, List, Dict
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

load_dotenv()

class AgentState(TypedDict):
    messages: List[HumanMessage]

llm = ChatOpenAI(model="gpt-4o")

def process(state:AgentState)-> AgentState:
    response = llm.invoke(state['messages'])
    print(f"\nAI: {response.content}")
    return state

graph = StateGraph(AgentState)
graph.add_node("process", process)
graph.add_edge(START, "process")
graph.add_edge("process", END)
agent = graph.compile()

user = input("Enter: ")
agent.invoke({"messages": [HumanMessage(content=user)]})

