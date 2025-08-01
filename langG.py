from dotenv import load_dotenv
from typing import Annotated, Literal, List, Dict
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
import random

load_dotenv()

class AgentState(TypedDict):
    name: str
    number: List[int]
    counter: int

def greet(state: AgentState)->AgentState:
    '''Greeting node'''

    state['name'] = f"Hi there {state['name']} "
    state['counter'] = 0

    return state

def randomnode(state:AgentState)->AgentState:
    '''random node'''
    state['number'].append(random.randint(0,10))
    state['counter'] +=1

    return state

def scountinue(state:AgentState)->AgentState:
    ''''''
    if state["counter"] < 5:
        print("Entering Loop", state["counter"])
        return "loop"
    else:
        return "exit"

graph = StateGraph(AgentState)
graph.add_node("greeting", greet)
graph.add_node("random", randomnode)
graph.add_edge("greeting","random")

graph.add_conditional_edges(
    "random", # source  node
    scountinue, # Action
    {
        "loop": "random", # self loop back to the same node
        "exit": END # end the graph
    }
)

graph.set_entry_point("greeting")
app = graph.compile()

app.invoke({"name":"saqib", "number": [], "counter":-1})