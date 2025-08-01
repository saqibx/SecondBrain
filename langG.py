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
    operation2: str
    number2: int
    number3: int
    number4: int
    finalNumber: int
    finalNumber2: int


def adder(state: AgentState)->AgentState:
    '''This node adds the 2 numbers'''
    state["finalNumber"] = state["number1"] + state["number2"]
    return state

def subtractor(state:AgentState)-> AgentState:
    '''This node subtracts'''
    state["finalNumber"] = state["number1"] - state["number2"]
    return state


def adder2(state: AgentState) -> AgentState:
    '''This node subtracts'''
    state["finalNumber2"] = state["number3"] + state["number4"]
    return state


def subtractor2(state: AgentState) -> AgentState:
    '''This node subtracts'''
    state["finalNumber2"] = state["number3"] - state["number4"]

    return state

def decide(state:AgentState)->AgentState:
    '''decides which node to use'''
    if state["operation"] == "+":
        return "addition_operation"
    elif state["operation"] == "-":
        return "subtraction_operation"

def decide2(state:AgentState)->AgentState:
    if state["operation2"] == "+":
        return "addition_operation2"
    elif state['operation2'] == "-":
        return "subtraction_operation2"

graph = StateGraph(AgentState)
graph.add_node("adder",adder)
graph.add_node("subtractor", subtractor)
graph.add_node("router",lambda state:state) #passthrough function

graph.add_node('adder2',adder2)
graph.add_node('subtractor2', subtractor2)
graph.add_node("router2", lambda state:state)

graph.add_edge("adder","router2")
graph.add_edge("subtractor", "router2")


graph.add_edge(START,"router")

graph.add_conditional_edges(
    "router", decide,

    {
        "addition_operation": "adder",
        "subtraction_operation": "subtractor"
    }
)

graph.add_conditional_edges(
    "router2", decide2,

    {
        "addition_operation2": "adder2",
        "subtraction_operation2": "subtractor2"
    }
)
graph.add_edge("adder2", END)
graph.add_edge("subtractor2", END)
init = AgentState(number1=32, operation="-", number2=93, operation2="+", number3=70,number4=10)

app = graph.compile()
print(app.invoke(init))