from flask import Flask, render_template, request, redirect, session
import requests
import uuid
from datetime import datetime
from config import API_KEY, API_URL, MODEL

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

active_chats = {}

def get_ai_response(prompt, history):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "messages": history + [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        return "I'm having trouble responding. Please try again later."

@app.route('/', methods=['GET', 'POST'])
def chat():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    current_chat_id = session.get('current_chat_id')
    if not current_chat_id or current_chat_id not in active_chats:
        current_chat_id = init_new_chat()
    
    current_chat = active_chats[current_chat_id]
    
    if request.method == 'POST':
        if 'new_chat' in request.form:
            if len(current_chat['messages']) > 0:
                current_chat_id = init_new_chat()
            return redirect('/')
            
        elif 'delete_chat' in request.form:
            return handle_delete_chat(request.form['delete_chat'])
            
        elif 'switch_chat' in request.form:
            return handle_switch_chat(request.form['switch_chat'])
            
        elif 'user_message' in request.form:
            return handle_user_message(current_chat, request.form['user_message'])
    
    cleanup_empty_chats(current_chat_id)
    
    return render_template('index.html',
                         messages=current_chat['messages'],
                         chats=get_active_chats(),
                         current_chat_id=current_chat_id)

def init_new_chat():
    new_id = str(uuid.uuid4())
    active_chats[new_id] = {
        'id': new_id,
        'title': "New Chat",
        'created': datetime.now(),
        'messages': [],
        'is_new': True
    }
    session['current_chat_id'] = new_id
    return new_id

def handle_delete_chat(chat_id):
    if chat_id in active_chats:
        del active_chats[chat_id]
        if chat_id == session.get('current_chat_id'):
            init_new_chat()
    return redirect('/')

def handle_switch_chat(chat_id):
    if chat_id in active_chats:
        session['current_chat_id'] = chat_id
        active_chats[chat_id]['is_new'] = False
    return redirect('/')

def handle_user_message(chat, message):
    if message.strip():
        response = get_ai_response(message, chat['messages'])
        chat['messages'].extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": response}
        ])
        if len(chat['messages']) == 2:
            chat['title'] = message[:30] + ("..." if len(message) > 30 else "")
        chat['is_new'] = False
    return redirect('/')

def get_active_chats():
    return {k: v for k, v in active_chats.items() if not v['is_new']}

def cleanup_empty_chats(current_chat_id):
    empty_chats = [
        chat_id for chat_id, chat in active_chats.items()
        if chat['is_new'] and len(chat['messages']) == 0 and chat_id != current_chat_id
    ]
    for chat_id in empty_chats:
        del active_chats[chat_id]

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)