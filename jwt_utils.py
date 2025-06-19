"""
JWT Authentication Utilities for Nivalis Dashboard
"""
import jwt
import datetime
import os
from functools import wraps
from flask import request, jsonify, current_app

def get_secret_key():
    """Get the secret key for JWT operations"""
    secret_key = current_app.secret_key
    if isinstance(secret_key, str):
        return secret_key.encode('utf-8')
    return secret_key or b'nivalis-default-secret'

def generate_token(telegram_id, remember_me=False):
    """Generate JWT token for user"""
    try:
        secret_key = get_secret_key()
        expires_in_days = 30 if remember_me else 1
        
        payload = {
            'telegram_id': str(telegram_id),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=expires_in_days),
            'iat': datetime.datetime.utcnow()
        }
        
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        return token
    except Exception as e:
        print(f"Token generation error: {e}")
        return None

def verify_token(token):
    """Verify JWT token and return telegram_id"""
    try:
        secret_key = get_secret_key()
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload.get('telegram_id')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception as e:
        print(f"Token verification error: {e}")
        return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import g
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        telegram_id = verify_token(token)
        
        if not telegram_id:
            return jsonify({'success': False, 'message': 'Invalid or expired token'}), 401
        
        # Add telegram_id to Flask g context
        g.telegram_id = telegram_id
        return f(*args, **kwargs)
    
    return decorated_function