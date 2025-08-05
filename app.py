from flask import Flask, session, redirect, request, url_for, jsonify
import os
from dotenv import load_dotenv
import sys
import io
import flask_cors
from flask_cors import CORS
import re
from Classes.ChromaDBHandler import ChromaDBHandler
from Classes.Users import User

# Import your agent system
from Agents.AgentMain import app as agent_app, AgentState
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")

# Proper CORS configuration
CORS(app, 
     origins=["http://localhost:8080", "http://127.0.0.1:8080"],  # Specify allowed origins
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)


@app.route('/api/login', methods=["POST", "OPTIONS"])
def login():
    """API endpoint for login"""
    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        username = data['username']
        password = data['password']



        # Get user from database
        existing_user = User.get_user(username=username)

        if existing_user is None:
            return jsonify({"success": False, "error": "User not found"}), 404

        print("Submitted password:", password)
        print("Password in DB:", existing_user.password)
        if existing_user and existing_user.verify_password(password):
            session['admin'] = True
            session['username'] = username
            
            response = jsonify({
                "success": True,
                "message": "Login successful"
            })
            response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response, 200
        else:
            response = jsonify({
                "success": False,
                "error": "Invalid credentials"
            })
            response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response, 401

    except Exception as e:
        response = jsonify({
            "success": False,
            "error": f"Login error: {str(e)}"
        })
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response, 500


@app.route('/api/logout', methods=["POST", "OPTIONS"])
def logout():
    """API endpoint for logout"""
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    session.pop('admin', None)
    session.pop('username', None)
    
    response = jsonify({"success": True, "message": "Logged out successfully"})
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response, 200


@app.route('/api/auth/status', methods=["GET", "OPTIONS"])
def auth_status():
    """Check if user is authenticated"""
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    response = jsonify({
        "authenticated": session.get("admin", False)
    })
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response, 200


@app.route('/api/chat', methods=["POST", "OPTIONS"])
def chat():
    """API endpoint for chat interactions"""
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    if not session.get("admin"):
        response = jsonify({"error": "Not authenticated"})
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response, 401

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
        response = jsonify({"error": "No data provided"})
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response, 400

    user_input = data.get('message', '').strip()
    if not user_input:
        response = jsonify({"error": "No message provided"})
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response, 400

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
            response = jsonify({
                "success": True,
                "response": agent_response,
                "agent_state": {
                    "research_draft": session['agent_state']['research_draft'],
                    "email_draft": session['agent_state']['email_draft'],
                    "messages_count": len(session['agent_state']['messages']),
                    "conversation_history": session['agent_state']['conversation_history']
                }
            })
            response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response, 200

        except Exception as e:
            sys.stdout = sys.__stdout__
            agent_response = f"Error: {str(e)}"
            print(f"Agent error: {e}")

            response = jsonify({
                "success": False,
                "error": agent_response,
                "agent_state": {
                    "research_draft": session['agent_state']['research_draft'],
                    "email_draft": session['agent_state']['email_draft'],
                    "messages_count": len(session['agent_state']['messages']),
                    "conversation_history": session['agent_state']['conversation_history']
                }
            })
            response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response, 500

    except Exception as e:
        response = jsonify({"error": f"Server error: {str(e)}"})
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response, 500


@app.route('/api/state', methods=["GET", "OPTIONS"])
def get_state():
    """Get current agent state"""
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    if not session.get("admin"):
        response = jsonify({"error": "Not authenticated"})
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response, 401

    # Initialize session state if not exists
    if 'agent_state' not in session:
        session['agent_state'] = {
            'messages': [],
            'research_draft': '',
            'email_draft': '',
            'conversation_history': []
        }

    response = jsonify({
        "agent_state": {
            "research_draft": session['agent_state']['research_draft'],
            "email_draft": session['agent_state']['email_draft'],
            "messages_count": len(session['agent_state']['messages']),
            "conversation_history": session['agent_state']['conversation_history']
        }
    })
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response, 200


@app.route('/api/clear', methods=["POST", "OPTIONS"])
def clear_session():
    """Clear the agent session"""
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    if not session.get("admin"):
        response = jsonify({"error": "Not authenticated"})
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response, 401

    if 'agent_state' in session:
        del session['agent_state']

    response = jsonify({"success": True, "message": "Session cleared"})
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response, 200


# Legacy route for backward compatibility (optional)
@app.route('/', methods=["GET"])
def index():
    """Redirect to frontend or return API info"""
    response = jsonify({
        "message": "Agent API Backend",
        "endpoints": {
            "POST /api/login": "Login with username/password",
            "POST /api/logout": "Logout",
            "GET /api/auth/status": "Check authentication status",
            "POST /api/chat": "Send message to agent",
            "GET /api/state": "Get current agent state",
            "POST /api/clear": "Clear agent session"
        }
    })
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response, 200


if __name__ == "__main__":
    app.run(debug=True, port=5895)