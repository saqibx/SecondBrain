from flask import Flask, session, redirect, request, url_for, jsonify
import os
from dotenv import load_dotenv
import sys
import io
import flask_cors
from flask_cors import CORS
import re

# Import your agent system
from Agents.AgentMain import app as agent_app, AgentState
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

load_dotenv()
app = Flask(__name__)
app.secret_key = '67'
CORS(app,supports_credentials=True)


@app.route('/api/login', methods=["POST"])
def login():
    """API endpoint for login"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get('username', '').lower()
    password = data.get('password', '').lower()

    actual_user = (os.getenv("ADMIN_USERNAME").lower())
    actual_pass = (os.getenv("ADMIN_PASSWORD").lower())

    print(f"proper\nuser: {actual_user}\npass: {actual_pass}")
    print(f"given\nuser: {username}\npass: {password}")

    if username == actual_user and password == actual_pass:
        session['admin'] = True
        return jsonify({
            "success": True,
            "message": "Login successful"
        }), 200
    else:
        return jsonify({
            "success": False,
            "error": "Invalid credentials"
        }), 401


@app.route('/api/logout', methods=["POST"])
def logout():
    """API endpoint for logout"""
    session.pop('admin', None)
    return jsonify({"success": True, "message": "Logged out successfully"}), 200


@app.route('/api/auth/status', methods=["GET"])
def auth_status():
    """Check if user is authenticated"""
    return jsonify({
        "authenticated": session.get("admin", False)
    }), 200


@app.route('/api/chat', methods=["POST"])
def chat():
    """API endpoint for chat interactions"""
    if not session.get("admin"):
        return jsonify({"error": "Not authenticated"}), 401

    # Initialize session state for agent if not exists
    if 'agent_state' not in session:
        session['agent_state'] = {
            'messages': [],
            'research_draft': '',
            'email_draft': '',
            'conversation_history': []
        }

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    user_input = data.get('message', '').strip()
    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    try:
        # Create new human message
        new_human_message = HumanMessage(content=user_input)

        # Build complete message history for the agent
        agent_messages = []

        for stored_msg in session['agent_state']['messages']:
            if stored_msg['type'] == 'human':
                agent_messages.append(HumanMessage(content=stored_msg['content']))
            elif stored_msg['type'] == 'ai':
                agent_messages.append(AIMessage(content=stored_msg['content']))

        # Add the new human message
        agent_messages.append(new_human_message)

        # Create agent state with full conversation history
        state = {
            "messages": agent_messages,
            "research_draft": session['agent_state']['research_draft'],
            "email_draft": session['agent_state']['email_draft']
        }

        # Capture the agent output
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            # Run the agent
            final_state = agent_app.invoke(state)

            # Restore stdout
            sys.stdout = sys.__stdout__
            agent_response = captured_output.getvalue()

            if final_state:
                research_text = final_state.get('research_draft', '')
                email_text = final_state.get('email_draft', '')

                # Clean up duplicate content in response
                if research_text and research_text.strip() in agent_response:
                    agent_response = agent_response.replace(research_text.strip(), '')

                if email_text and email_text.strip() in agent_response:
                    agent_response = agent_response.replace(email_text.strip(), '')

                # Update session state
                session['agent_state']['research_draft'] = research_text
                session['agent_state']['email_draft'] = email_text

                # Store only Human and AI messages for conversation context
                serializable_messages = []
                for msg in final_state.get('messages', []):
                    if isinstance(msg, HumanMessage):
                        serializable_messages.append({
                            'type': 'human',
                            'content': msg.content
                        })
                    elif isinstance(msg, AIMessage):
                        serializable_messages.append({
                            'type': 'ai',
                            'content': msg.content
                        })

                session['agent_state']['messages'] = serializable_messages

                # Add to conversation history for display
                conversation_entry = {
                    'user': user_input,
                    'agent': agent_response,
                    'research': final_state.get('research_draft', ''),
                    'email': final_state.get('email_draft', ''),
                    'timestamp': int(__import__('time').time())
                }
                session['agent_state']['conversation_history'].append(conversation_entry)

            session.modified = True

            # Return the response data
            return jsonify({
                "success": True,
                "response": agent_response,
                "agent_state": {
                    "research_draft": session['agent_state']['research_draft'],
                    "email_draft": session['agent_state']['email_draft'],
                    "messages_count": len(session['agent_state']['messages']),
                    "conversation_history": session['agent_state']['conversation_history']
                }
            }), 200

        except Exception as e:
            sys.stdout = sys.__stdout__
            agent_response = f"Error: {str(e)}"
            print(f"Agent error: {e}")

            return jsonify({
                "success": False,
                "error": agent_response,
                "agent_state": {
                    "research_draft": session['agent_state']['research_draft'],
                    "email_draft": session['agent_state']['email_draft'],
                    "messages_count": len(session['agent_state']['messages']),
                    "conversation_history": session['agent_state']['conversation_history']
                }
            }), 500

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route('/api/state', methods=["GET"])
def get_state():
    """Get current agent state"""
    if not session.get("admin"):
        return jsonify({"error": "Not authenticated"}), 401

    # Initialize session state if not exists
    if 'agent_state' not in session:
        session['agent_state'] = {
            'messages': [],
            'research_draft': '',
            'email_draft': '',
            'conversation_history': []
        }

    return jsonify({
        "agent_state": {
            "research_draft": session['agent_state']['research_draft'],
            "email_draft": session['agent_state']['email_draft'],
            "messages_count": len(session['agent_state']['messages']),
            "conversation_history": session['agent_state']['conversation_history']
        }
    }), 200


@app.route('/api/clear', methods=["POST"])
def clear_session():
    """Clear the agent session"""
    if not session.get("admin"):
        return jsonify({"error": "Not authenticated"}), 401

    if 'agent_state' in session:
        del session['agent_state']

    return jsonify({"success": True, "message": "Session cleared"}), 200


# Legacy route for backward compatibility (optional)
@app.route('/', methods=["GET"])
def index():
    """Redirect to frontend or return API info"""
    return jsonify({
        "message": "Agent API Backend",
        "endpoints": {
            "POST /api/login": "Login with username/password",
            "POST /api/logout": "Logout",
            "GET /api/auth/status": "Check authentication status",
            "POST /api/chat": "Send message to agent",
            "GET /api/state": "Get current agent state",
            "POST /api/clear": "Clear agent session"
        }
    }), 200


if __name__ == "__main__":
    app.run(debug=True, port=5895)