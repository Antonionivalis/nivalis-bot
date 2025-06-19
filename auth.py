"""
User Authentication and Session Management for Nivalis
Handles secure login, user registration, and session management
"""
import os
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, session, jsonify, redirect, url_for
from replit import db
import logging

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET = os.getenv('SESSION_SECRET', 'nivalis-jwt-secret')
JWT_ALGORITHM = 'HS256'
TOKEN_EXPIRY_HOURS = 24

class AuthManager:
    """Manages user authentication and authorization"""
    
    @staticmethod
    def hash_password(password):
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', 
                                          password.encode('utf-8'), 
                                          salt.encode('utf-8'), 
                                          100000)
        return f"{salt}:{password_hash.hex()}"
    
    @staticmethod
    def verify_password(password, password_hash):
        """Verify password against stored hash"""
        try:
            salt, stored_hash = password_hash.split(':')
            password_hash_check = hashlib.pbkdf2_hmac('sha256',
                                                    password.encode('utf-8'),
                                                    salt.encode('utf-8'),
                                                    100000)
            return stored_hash == password_hash_check.hex()
        except:
            return False
    
    @staticmethod
    def generate_token(user_id):
        """Generate JWT token for user"""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def verify_token(token):
        """Verify JWT token and return user_id"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload['user_id']
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

class UserManager:
    """Manages user data and operations"""
    
    @staticmethod
    def create_user(telegram_id, email=None, name=None):
        """Create new user account"""
        user_data = {
            'telegram_id': str(telegram_id),
            'email': email,
            'name': name,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'onboarding_completed': False,
            'subscription_status': 'none',  # none, basic, mvp_lifetime, premium
            'onboarding_data': {},
            'chat_history': [],
            'preferences': {}
        }
        
        # Store user data
        user_key = f"user:{telegram_id}"
        db[user_key] = user_data
        
        # Add to user index
        user_index = db.get("user_index", [])
        if str(telegram_id) not in user_index:
            user_index.append(str(telegram_id))
            db["user_index"] = user_index
        
        logger.info(f"Created user account for Telegram ID: {telegram_id}")
        return user_data
    
    @staticmethod
    def get_user(telegram_id):
        """Get user by Telegram ID"""
        user_key = f"user:{telegram_id}"
        return db.get(user_key)
    
    @staticmethod
    def update_user(telegram_id, updates):
        """Update user data"""
        user_key = f"user:{telegram_id}"
        user_data = db.get(user_key)
        if user_data:
            user_data.update(updates)
            user_data['updated_at'] = datetime.utcnow().isoformat()
            db[user_key] = user_data
            return user_data
        return None
    
    @staticmethod
    def complete_onboarding(telegram_id, onboarding_data):
        """Mark onboarding as complete and store data"""
        updates = {
            'onboarding_completed': True,
            'onboarding_data': onboarding_data
        }
        return UserManager.update_user(telegram_id, updates)
    
    @staticmethod
    def is_subscriber(telegram_id):
        """Check if user has active subscription"""
        user = UserManager.get_user(telegram_id)
        if not user:
            return False
        
        subscription_status = user.get('subscription_status', 'none')
        return subscription_status in ['basic', 'mvp_lifetime', 'premium']
    
    @staticmethod
    def add_subscription(telegram_id, tier):
        """Add subscription to user"""
        updates = {'subscription_status': tier}
        return UserManager.update_user(telegram_id, updates)

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for session token
        token = session.get('auth_token')
        if not token:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Verify token
        user_id = AuthManager.verify_token(token)
        if not user_id:
            session.pop('auth_token', None)
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Add user to Flask g context
        from flask import g
        g.current_user_id = user_id
        return f(*args, **kwargs)
    
    return decorated_function

def require_subscription(f):
    """Decorator to require active subscription"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = getattr(request, 'current_user_id', None)
        if not user_id or not UserManager.is_subscriber(user_id):
            return jsonify({'error': 'Active subscription required'}), 403
        return f(*args, **kwargs)
    
    return decorated_function

def get_current_user():
    """Get current authenticated user"""
    from flask import g
    user_id = getattr(g, 'current_user_id', None)
    if user_id:
        return UserManager.get_user(user_id)
    return None