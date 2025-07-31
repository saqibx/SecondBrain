from dotenv import load_dotenv
from typing import Annotated, Literal, List
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

load_dotenv()

class AgentState(TypedDict):
    number1: int
    operation: str
    number2: int
    finalNumber: int


def adder(state: AgentState)->AgentState:
    '''This node adds the 2 numbers'''
    state["finalNumber"] = state["number1"] + state["number2"]
    return state

def subtractor(state:AgentState)-> AgentState:
    '''This node subtracts'''
    state["finalNumber"] = state["number1"] - state["number2"]
    return state

def decide(state:AgentState)->AgentState:
    '''decides which node to use'''
    if state["operation"] == "+":
        return "addition_operation"
    elif state["operation"] == "-":
        return "subtraction_operation"


graph = StateGraph(AgentState)
graph.add_node("adder",adder)
graph.add_node("subtractor", subtractor)
graph.add_node("router",lambda state:state) #passthrough function

graph.add_edge(START,"router")
graph.add_conditional_edges(
    "router", decide,

    {
        "addition_operation": "adder",
        "subtraction_operation": "subtractor"
    }
)
graph.add_edge("adder", END)
graph.add_edge("subtractor", END)
init = AgentState(number1=32, operation="-", number2=93)

app = graph.compile()
print(app.invoke(init))