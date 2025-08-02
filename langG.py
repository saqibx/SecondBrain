from dotenv import load_dotenv
from typing import Annotated, List, Dict, Union, Sequence, TypedDict
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
document_content = ""
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


@tool
def update(content: str) -> str:
    '''Updates the document with the provided content'''

    global document_content
    document_content = content
    return f"Document has been updated successfully! Current content is \n {document_content}"

@tool
def save(filename: str) -> str:
    '''Saves the information to the TEXT file and finishes the program
    Args: filename: Name for the filename
    '''
    global document_content

    if not filename.endswith(".txt"):
        filename = f"{filename}.txt"

    try:
        with open(filename, 'w') as file:
            file.write(document_content)
            print(f"Successfully saved {filename}")
            return f"document has been saved"

    except Exception as e:
        return f"Error saving document {str(e)}"

tools = [update,save]

model = ChatOpenAI(model="gpt-4o").bind_tools(tools)


def our_agent(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(content=f"""
    You are Drafter, a helpful writing assistant. You are going to help the user update and modify documents.

    - If the user wants to update or modify content, use the 'update' tool with the complete updated content.
    - If the user wants to save and finish, you need to use the 'save' tool.
    - Make sure to always show the current document state after modifications.

    The current document content is:{document_content}
    """)

    if not state["messages"]:
        user_input = "I'm ready to help you update a document. What would you like to create?"
        user_message = HumanMessage(content=user_input)

    else:
        user_input = input("\nWhat would you like to do with the document? ")
        print(f"\n👤 USER: {user_input}")
        user_message = HumanMessage(content=user_input)

    all_messages = [system_prompt] + list(state["messages"]) + [user_message]

    response = model.invoke(all_messages)

    print(f"\n🤖 AI: {response.content}")
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"🔧 USING TOOLS: {[tc['name'] for tc in response.tool_calls]}")

    return {"messages": list(state["messages"]) + [user_message, response]}


def scontinue(state:AgentState)->str:
    '''determine if we should continue this conversation or end it'''

    messages = state['messages']

    if not messages:
        return "continue"

    for message in reversed(messages):
        if (isinstance(message, ToolMessage) and
            "saved" in message.content.lower() and
            "document" in message.content.lower()):
            return "end"

    return "continue"

def print_messages(messages):
    '''function that prints messages in a more readable format'''
    if not messages:
        return

    for message in messages[-3:]:
        if isinstance(message,ToolMessage):
            print(f"TOOL RESULT: {message.content}")

graph = StateGraph(AgentState)
graph.add_node("agent", our_agent)
graph.add_node("tools", ToolNode(tools))
graph.set_entry_point("agent")
graph.add_edge("agent","tools")

graph.add_conditional_edges(
    "tools",
    scontinue,
    {
        "continue": "agent",
        "end": END
    }
)

app = graph.compile()

def run():
    print("\n===== DRAFTER ====")
    state = {"messages": []}

    for step in app.stream(state, stream_mode="values"):
        if 'messages' in step:
            print_messages(step['messages'])

    print("\n==== DRAFTER DONE ====")

if __name__ == "__main__":
    run()