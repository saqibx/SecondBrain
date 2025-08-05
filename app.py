from flask import Flask, session, redirect, request, url_for, render_template_string, jsonify
import os
from dotenv import load_dotenv
import sys
import io
import flask_cors
from flask_cors import CORS

# Import your agent system
from Agents.AgentMain import app as agent_app, AgentState
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

load_dotenv()
app = Flask(__name__)
app.secret_key = '67'
CORS(app)


@app.route('/', methods=["POST", "GET"])
def admin():
    username = " "
    password = " "
    if request.method == "POST":
        username = request.form['username'].lower()
        password = request.form['password'].lower()

    actual_user = (os.getenv("ADMIN_USERNAME").lower())
    actual_pass = (os.getenv("ADMIN_PASSWORD").lower())

    print(f"proper\nuser: {actual_user}\npass: {actual_pass}")
    print(f"given\nuser: {username}\npass: {password}")

    if username == actual_user and password == actual_pass:
        session['admin'] = True
        return redirect(url_for('home'))

    if request.method == "POST":
        return "Invalid Credentials", 403

    return '''
        <form method="post">
            <input name="username" placeholder="Username"><br>
            <input name="password" type="password" placeholder="Password"><br>
            <input type="submit" value="Login">
        </form>
    '''


@app.route('/home', methods=["POST", "GET"])
def home():
    if not session.get("admin"):
        return redirect(url_for("admin"))

    # Initialize session state for agent if not exists
    if 'agent_state' not in session:
        session['agent_state'] = {
            'messages': [],
            'research_draft': '',
            'email_draft': '',
            'conversation_history': []
        }

    agent_response = ""
    user_input = ""

    if request.method == "POST":
        user_input = request.form.get('user_input', '').strip()

        if user_input:
            # Create new human message
            new_human_message = HumanMessage(content=user_input)

            # Build complete message history for the agent
            # For now, let's use a simpler approach: only keep Human and AI messages
            # This avoids the tool message complexity while maintaining conversation context
            agent_messages = []

            for stored_msg in session['agent_state']['messages']:
                if stored_msg['type'] == 'human':
                    agent_messages.append(HumanMessage(content=stored_msg['content']))
                elif stored_msg['type'] == 'ai':
                    # Only include the text content, not tool calls
                    # This keeps the conversation context without tool complexity
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
                # final_state = None
                # for step_output in agent_app.stream(state, stream_mode="values"):
                #     final_state = step_output
                final_state = agent_app.invoke(state)

                # Restore stdout
                sys.stdout = sys.__stdout__
                agent_response = captured_output.getvalue()

                if final_state:
                    research_text = final_state.get('research_draft', '')
                    email_text = final_state.get('email_draft', '')

                    # 🧠 Check if printed logs duplicate the returned research/email
                    if research_text and research_text.strip() in agent_response:
                        agent_response = agent_response.replace(research_text.strip(), '')

                    if email_text and email_text.strip() in agent_response:
                        agent_response = agent_response.replace(email_text.strip(), '')

                    # Update session state
                    session['agent_state']['research_draft'] = research_text
                    session['agent_state']['email_draft'] = email_text

                    # Store only Human and AI messages for conversation context
                    # This avoids tool message serialization complexity
                    serializable_messages = []
                    for msg in final_state.get('messages', []):
                        if isinstance(msg, HumanMessage):
                            serializable_messages.append({
                                'type': 'human',
                                'content': msg.content
                            })
                        elif isinstance(msg, AIMessage):
                            # Store just the content for conversation context
                            serializable_messages.append({
                                'type': 'ai',
                                'content': msg.content
                            })

                    session['agent_state']['messages'] = serializable_messages

                    # Add to conversation history for display
                    session['agent_state']['conversation_history'].append({
                        'user': user_input,
                        'agent': agent_response,
                        'research': final_state.get('research_draft', ''),
                        'email': final_state.get('email_draft', '')
                    })

                session.modified = True
                return redirect(url_for('home'))

            except Exception as e:
                sys.stdout = sys.__stdout__
                agent_response = f"Error: {str(e)}"
                print(f"Agent error: {e}")

    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Admin Panel - Agentic Assistant</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .header { border-bottom: 2px solid #007bff; padding-bottom: 10px; margin-bottom: 20px; }
                .chat-container { border: 1px solid #ddd; height: 400px; overflow-y: auto; padding: 15px; margin-bottom: 20px; background-color: #fafafa; border-radius: 5px; }
                .message { margin-bottom: 15px; padding: 10px; border-radius: 5px; }
                .user-message { background-color: #007bff; color: white; text-align: right; }
                .agent-message { background-color: #e9ecef; color: #333; }
                .input-container { display: flex; gap: 10px; margin-bottom: 20px; }
                .input-container input[type="text"] { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
                .input-container button { padding: 10px 20px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
                .input-container button:hover { background-color: #0056b3; }
                .status-panel { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
                .status-box { padding: 15px; border-radius: 5px; border: 1px solid #ddd; }
                .research-box { background-color: #d4edda; border-color: #c3e6cb; }
                .email-box { background-color: #d1ecf1; border-color: #bee5eb; }
                .logout { text-align: right; margin-top: 20px; }
                .logout a { color: #dc3545; text-decoration: none; }
                .logout a:hover { text-decoration: underline; }
                .debug-info { background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; margin-bottom: 20px; border-radius: 5px; font-size: 12px; }
                pre { white-space: pre-wrap; word-wrap: break-word; max-height: 200px; overflow-y: auto; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🤖 Agentic Research & Email Assistant</h1>
                    <p>Welcome, admin! Use this interface to interact with your AI agent.</p>
                </div>

                <!-- Debug Info -->
                <div class="debug-info">
                    <strong>Debug Info:</strong>
                    Messages in memory: {{ agent_state.messages|length }} |
                    Conversation history: {{ agent_state.conversation_history|length }} |
                    Research: {{ '✅' if agent_state.research_draft else '❌' }} |
                    Email: {{ '✅' if agent_state.email_draft else '❌' }}
                </div>

                <!-- Status Panel -->
                <div class="status-panel">
                    <div class="status-box research-box">
                        <h3>📝 Research Status</h3>
                        <p><strong>Status:</strong> {{ '✅ Complete' if agent_state.research_draft else '❌ None' }}</p>
                        {% if agent_state.research_draft %}
                        <details>
                            <summary>View Research</summary>
                            <pre>{{ agent_state.research_draft[:500] }}{% if agent_state.research_draft|length > 500 %}...{% endif %}</pre>
                        </details>
                        {% endif %}
                    </div>

                    <div class="status-box email-box">
                        <h3>📧 Email Status</h3>
                        <p><strong>Status:</strong> {{ '✅ Complete' if agent_state.email_draft else '❌ None' }}</p>
                        {% if agent_state.email_draft %}
                        <details>
                            <summary>View Email</summary>
                            <pre>{{ agent_state.email_draft }}</pre>
                        </details>
                        {% endif %}
                    </div>
                </div>

                <!-- Chat Interface -->
                <div class="chat-container" id="chat">
                    {% for conv in agent_state.conversation_history %}
                        <div class="message user-message">
                            <strong>You:</strong> {{ conv.user }}
                        </div>
                        <div class="message agent-message">
                            <strong>🤖 Agent:</strong><br>
                            <pre>{{ conv.agent }}</pre>
                        </div>
                    {% endfor %}

                    {% if user_input %}
                        <div class="message user-message">
                            <strong>You:</strong> {{ user_input }}
                        </div>
                        <div class="message agent-message">
                            <strong>🤖 Agent:</strong><br>
                            <pre>{{ agent_response }}</pre>
                        </div>
                    {% endif %}
                </div>

                <!-- Input Form -->
                <form method="post">
                    <div class="input-container">
                        <input type="text" name="user_input" placeholder="Ask your agent anything... (e.g., 'Research OpenAI', 'Draft an email to Google', 'Save my research')" required>
                        <button type="submit">Send</button>
                    </div>
                </form>

                <!-- Quick Actions -->
                <div style="margin-bottom: 20px;">
                    <h4>💡 Quick Actions:</h4>
                    <button onclick="fillInput('Research Tesla and their latest AI developments')" style="margin: 5px; padding: 8px 12px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer;">Research Tesla</button>
                    <button onclick="fillInput('Draft a professional email for collaboration')" style="margin: 5px; padding: 8px 12px; background: #17a2b8; color: white; border: none; border-radius: 4px; cursor: pointer;">Draft Email</button>
                    <button onclick="fillInput('Save my research to a file')" style="margin: 5px; padding: 8px 12px; background: #ffc107; color: black; border: none; border-radius: 4px; cursor: pointer;">Save Content</button>
                    <button onclick="fillInput('What do you know about Tech Start UCalgary?')" style="margin: 5px; padding: 8px 12px; background: #6f42c1; color: white; border: none; border-radius: 4px; cursor: pointer;">Ask About Tech Start</button>
                    <a href="{{ url_for('clear_session') }}" style="margin: 5px; padding: 8px 12px; background: #dc3545; color: white; border: none; border-radius: 4px; text-decoration: none; display: inline-block;">🗑️ Clear Memory</a>
                </div>

                <div class="logout">
                    <a href="{{ url_for('admin') }}">🚪 Logout</a>
                </div>
            </div>

            <script>
                // Auto scroll to bottom of chat
                function scrollToBottom() {
                    const chat = document.getElementById('chat');
                    chat.scrollTop = chat.scrollHeight;
                }
                scrollToBottom();

                // Quick action buttons
                function fillInput(text) {
                    document.querySelector('input[name="user_input"]').value = text;
                }

                // Auto-focus input
                document.querySelector('input[name="user_input"]').focus();
            </script>
        </body>
        </html>
    ''',
                                  agent_state=session['agent_state'],
                                  user_input=user_input,
                                  agent_response=agent_response
                                  )


@app.route('/clear_session')
def clear_session():
    """Clear the agent session"""
    if 'agent_state' in session:
        del session['agent_state']
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True, port=5895)