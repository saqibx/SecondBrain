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


from Agents.AgentMain import app as agent_app, AgentState
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")


CORS(app,
     origins=["http://localhost:8080", "http://127.0.0.1:8080"],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
     )


@app.route('/api/login', methods=["POST", "OPTIONS"])
def login():
    """API endpoint for login"""

    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    session.clear()

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        username = data['username']
        password = data['password']


        existing_user = User.get_user(username=username)

        if existing_user is None:
            return jsonify({"success": False, "error": "User not found"}), 404

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
    session.clear()

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

        new_human_message = HumanMessage(content=user_input)


        agent_messages = []

        for stored_msg in session['agent_state']['messages']:
            if stored_msg['type'] == 'human':
                agent_messages.append(HumanMessage(content=stored_msg['content']))
            elif stored_msg['type'] == 'ai':
                agent_messages.append(AIMessage(content=stored_msg['content']))


        agent_messages.append(new_human_message)


        state = {
            "messages": agent_messages,
            "research_draft": session['agent_state']['research_draft'],
            "email_draft": session['agent_state']['email_draft']
        }


        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:

            final_state = agent_app.invoke(state)


            sys.stdout = sys.__stdout__
            agent_response = captured_output.getvalue()

            if final_state:
                research_text = final_state.get('research_draft', '')
                email_text = final_state.get('email_draft', '')


                if research_text and research_text.strip() in agent_response:
                    agent_response = agent_response.replace(research_text.strip(), '')

                if email_text and email_text.strip() in agent_response:
                    agent_response = agent_response.replace(email_text.strip(), '')


                session['agent_state']['research_draft'] = research_text
                session['agent_state']['email_draft'] = email_text


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


                conversation_entry = {
                    'user': user_input,
                    'agent': agent_response,
                    'research': final_state.get('research_draft', ''),
                    'email': final_state.get('email_draft', ''),
                    'timestamp': int(__import__('time').time())
                }
                session['agent_state']['conversation_history'].append(conversation_entry)

            session.modified = True


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
            "POST /api/clear": "Clear agent session",
            "POST /api/register": "Register new account"
        }
    })
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response, 200

@app.route('/api/register', methods=["POST", "OPTIONS"])
def register():
    """API endpoint for user registration"""

    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    session.clear()
    data = request.get_json()

    if not data:
        response = jsonify({"error": "No data provided"})
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response, 400

    try:
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        user_id = data.get('user_id', '').strip()


        if not username:
            response = jsonify({"success": False, "error": "Username is required"})
            response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response, 400

        if not password:
            response = jsonify({"success": False, "error": "Password is required"})
            response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response, 400

        if len(password) < 6:
            response = jsonify({"success": False, "error": "Password must be at least 6 characters long"})
            response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response, 400


        if not user_id:
            import uuid
            user_id = str(uuid.uuid4())


        existing_user = User.get_user(username=username)
        if existing_user:
            response = jsonify({"success": False, "error": "Username already exists"})
            response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response, 409  # Conflict status code


        new_user = User(
            user_id=user_id,
            username=username,
            plain_password=password,
            already_hashed=False  # This is a new password that needs hashing
        )


        result = new_user.set_user()

        if "Finished Pushing To DB" in result:

            session['admin'] = True
            session['username'] = username
            session['user_id'] = user_id

            response = jsonify({
                "success": True,
                "message": "Registration successful and logged in",
                "user": {
                    "user_id": user_id,
                    "username": username
                }
            })
            response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response, 201
        else:

            response = jsonify({
                "success": False,
                "error": "Failed to create user account"
            })
            response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response, 500

    except Exception as e:
        print(f"Registration error: {e}")
        response = jsonify({
            "success": False,
            "error": f"Registration error: {str(e)}"
        })
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response, 500




if __name__ == "__main__":
    app.run(debug=True, port=5895)