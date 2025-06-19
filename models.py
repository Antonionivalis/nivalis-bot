import os
import json
from datetime import datetime

# Simple file-based storage for conversation memory
CONVERSATIONS_FILE = "user_conversations.json"

def load_conversations():
    """Load conversations from file"""
    try:
        with open(CONVERSATIONS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_conversations(conversations):
    """Save conversations to file"""
    with open(CONVERSATIONS_FILE, 'w') as f:
        json.dump(conversations, f, indent=2, default=str)

def get_user_conversation(user_id: int):
    """Get user conversation record"""
    conversations = load_conversations()
    user_key = str(user_id)
    
    if user_key not in conversations:
        conversations[user_key] = {
            'user_id': user_id,
            'skill_area': '',
            'unique_approach': '',
            'target_client': '',
            'transformation': '',
            'offer_details': '',
            'conversation_stage': 'skill_discovery',
            'last_interaction': datetime.utcnow().isoformat(),
            'is_complete': False
        }
        save_conversations(conversations)
    
    return conversations[user_key]

def update_user_conversation(user_id: int, **kwargs):
    """Update user conversation with new information"""
    conversations = load_conversations()
    user_key = str(user_id)
    
    if user_key in conversations:
        for key, value in kwargs.items():
            if key in conversations[user_key]:
                conversations[user_key][key] = value
        conversations[user_key]['last_interaction'] = datetime.utcnow().isoformat()
        save_conversations(conversations)
    
    return conversations.get(user_key)