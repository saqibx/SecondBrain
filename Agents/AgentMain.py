from dotenv import load_dotenv
from typing import Annotated, List, Dict, Union, Sequence
from typing_extensions import TypedDict
from tavily import TavilyClient
import os
import time
from langgraph.graph import StateGraph
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
import Agents.utils as utils

START = "__start__"
END = "__end__"



load_dotenv()


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    research_draft: str
    email_draft: str


tools = [utils.researcher, utils.emailer, utils.saver, utils.retriever, utils.embedder]
model = ChatOpenAI(model="gpt-4o").bind_tools(tools)

def agent_node(state: AgentState) -> AgentState:
    """Main agent that decides what to do next"""

    # Create system prompt
    agent_prompt = SystemMessage(content="""
    You are an intelligent assistant designed to help write professional emails by researching companies and tailoring outreach accordingly.
    
    You have access to 4 tools:
    - `researcher(topic: str)`: Use this to research a company or topic.
    - `emailer(content: str)`: Use this to write a professional email based on provided notes or research.
    - `saver(filename: str, content: str)`: Use this to save finished content to a file.
    - retriever(query: str) use this when the user asks you something that may be stored in the personal knowledge db
    - embedder(docs: str) : ALWAYS USE THIS AT THE END, WHENEVER A USER ASKS YOU TO SAVE SOMETHING, IMMEDIATELY AFTER THAT
        USE THE EMBEDDER AND PASS IN THE STRING RESULT FROM RETRIEVER(). ALWAYS EMBED EVERYTHING.
    
    Your job is to:
    1. Understand the user's request.
    2. If they want research, call researcher() with the topic
    3. If they want an email draft, call emailer() with relevant content (use research if available)
    4. If they want to save something, call saver() with filename and content
        4b. If they want to save the research you need to save the return value from the researcher tool, not the AI summary that is displayed in console.
    5. You can do multiple research calls if needed for different topics
    6. Always be helpful and explain what you're doing
    7. If the user asks a question that is related to Tech Start or maybe something they have studied before use retriever to look for that information
    8. At the end of the users request, always embed the result.
    You are Saqib Mazhar, Co-VP External of Tech Start UCalgary, a student-led startup incubator at the University of Calgary.
    
    Be deliberate and think before acting. If you're not sure what the user wants, ask for clarification.
    """)


    context_msg = SystemMessage(content=f"""
    Your prior work this session:
    - Research completed: {'Yes' if state['research_draft'] else 'No'}
    - Email drafted: {'Yes' if state['email_draft'] else 'No'}
    
    Research draft:
    {state['research_draft'] or 'None yet'}
    
    Email draft:
    {state['email_draft'] or 'None yet'}
    
    Use this context to avoid repeating work unless specifically requested.
    """)


    all_messages = [agent_prompt, context_msg] + list(state['messages'])


    response = model.invoke(all_messages)

    print(f"\n🤖 AI: {response.content}")

    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_names = [tc['name'] for tc in response.tool_calls]
        print(f"🔧 Using tools: {tool_names}")

    return {
        "messages": [response],
        "research_draft": state["research_draft"],
        "email_draft": state["email_draft"]
    }


def update_state(state: AgentState) -> AgentState:
    """Update research_draft and email_draft based on tool results"""


    for msg in reversed(state['messages']):
        if isinstance(msg, ToolMessage):
            content = msg.content


            if ("Source:" in content or
                    "ERROR: No research topic" in content or
                    "RESEARCHER ERROR:" in content):
                if not state['research_draft'] or "ERROR" not in content:
                    state['research_draft'] = content


            elif ("Best regards" in content or
                  "Subject:" in content or
                  "EMAILER ERROR:" in content):
                if not state['email_draft'] or "ERROR" not in content:
                    state['email_draft'] = content


            break

    return state


def should_continue(state: AgentState) -> str:
    """Decide whether to continue or end"""

    last_message = state["messages"][-1]

    # If the last message has tool calls execute them
    if isinstance(last_message, AIMessage) and hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    
    return "end"



workflow = StateGraph(AgentState)


workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("update_state", update_state)


workflow.set_entry_point("agent")

workflow.add_conditional_edges("agent", should_continue, {
    "tools": "tools",
    "end": END
})
workflow.add_edge("tools", "update_state")
workflow.add_edge("update_state", "agent")


app = workflow.compile()


def run_session():
    """Run an interactive session"""
    print("=== AGENTIC RESEARCH & EMAIL SYSTEM ===")

    print("Type 'quit' to exit.\n")

    state = {
        "messages": [],
        "research_draft": "",
        "email_draft": ""
    }

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break

            if not user_input:
                continue


            user_message = HumanMessage(content=user_input)
            state["messages"].append(user_message)

            print(f"\nProcessing: {user_input}")


            final_state = None
            for step_output in app.stream(state, stream_mode="values"):
                final_state = step_output


            if final_state:
                state = final_state


            print(f"\n📊 Status:")
            print(f"   Research: {'Complete' if state['research_draft'] else ' None'}")
            print(f"   Email: {'Complete' if state['email_draft'] else ' None'}")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f" Error: {e}")
            continue


def run_single_request(request: str):
    """Run a single request (useful for testing)"""
    print(f"=== Processing: {request} ===")

    state = {
        "messages": [HumanMessage(content=request)],
        "research_draft": "",
        "email_draft": ""
    }

    final_state = None
    for step_output in app.stream(state, stream_mode="values"):
        final_state = step_output

    if final_state:
        print(f"\nFinal Results:")
        if final_state['research_draft']:
            print(f"\nResearch:\n{final_state['research_draft']}")
        if final_state['email_draft']:
            print(f"\nEmail:\n{final_state['email_draft']}")

    return final_state


if __name__ == "__main__":


    # Interactive mode
    run_session()

