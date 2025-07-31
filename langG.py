from dotenv import load_dotenv
from typing import Annotated, Literal, List
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

load_dotenv()

class AgentState(TypedDict):
    name: str
    age: str
    skills: List[str]
    final: str



def first(state: AgentState) -> AgentState:
    '''First node of our sequence'''

    state["final"] = f"Hi {state['name']}!"
    return state


def second(state: AgentState) -> AgentState:
    '''second node of our sequence'''

    state["final"] = state["final"] + f" You are {state['age']} years old!"
    return state

def third(state: AgentState) -> AgentState:
    '''Third node of our sequence'''
    Skills = state["skills"]
    state["final"] = state["final"] + f"You are skilled in {', '.join(Skills)}"
    return state

graph = StateGraph(AgentState)
graph.add_node("first", first)
graph.add_node("second", second)
graph.add_node("third",third)
graph.set_entry_point("first")
graph.add_edge("first","second")
graph.add_edge("second","third")
graph.set_finish_point("third")

app = graph.compile()

result = app.invoke({"name":"saqib","age":19,"skills":["Python", "LangGraph"]})
print(result["final"])