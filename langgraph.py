from dotenv import load_dotenv
from typing import Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

load_dotenv()

class AgentState(TypedDict):
    message: str


def greet(state:AgentState) -> AgentState:

    state["message"] = f"Hey {state['message']}"
    return state

graph = StateGraph(AgentState)
graph.add_node("greetr", greet)
graph.set_entry_point("greetr")
graph.set_finish_point("greetr")


app = graph.compile()
result = app.invoke({"message":"huzz"})
print(result["message"])