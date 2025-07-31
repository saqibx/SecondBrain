from dotenv import load_dotenv
from typing import Annotated, Literal, List
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

load_dotenv()

class AgentState(TypedDict):
    values: List[int]
    name: str
    operation: str
    answer: float
    result: str

def process_values(state:AgentState) -> AgentState:
    '''This function handles multiple different inputs'''
    u_name = state["name"]
    u_values = state["values"]
    u_operation = state["operation"]
    a, b, c, d = u_values

    if u_operation == "+":
        state["answer"] = sum(u_values)
    elif u_operation == "-":

        sub = lambda a,b,c,d: a-b-c-d
        state["answer"] = sub(a,b,c,d)
    elif u_operation == "*":
        multiply = lambda a,b,c,d:a*b*c*d
        state["answer"] = multiply(a,b,c,d)
    else:
        divide = lambda a,b,c,d: (a/b)/(c/d)
        state["answer"] = divide(a,b,c,d)

    state['result'] = f"Hi there {state['name']}! Your answer is {(state['answer'])}"
    return state

graph = StateGraph(AgentState)
graph.add_node("process", process_values)
graph.set_entry_point("process")
graph.set_finish_point("process")
app = graph.compile()

answers = app.invoke({"values": [1,2,3,4], "name": "saqib","operation":"*"})
print(answers["result"])