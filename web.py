import os
import logging
import requests
import json
import threading
import datetime
from flask import Flask, render_template, request, redirect, jsonify, url_for
import stripe
from openai import OpenAI
import psycopg2
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SESSION_SECRET") or "nivalis-default-secret-key-change-in-production"

# Configure Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Telegram Bot Configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# OpenAI Configuration
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Database configuration for Railway PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        # Create subscribers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id BIGINT PRIMARY KEY,
                tier VARCHAR(50) DEFAULT 'basic',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Create user_conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_conversations (
                user_id BIGINT PRIMARY KEY,
                conversation_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()

# Initialize database on startup
init_db()

def get_subscribers():
    """Get list of subscribers from PostgreSQL"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM subscribers")
        subscribers = [str(row[0]) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return subscribers
    return []

def add_subscriber(user_id, tier='mvp_lifetime'):
    """Add user to subscribers list"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO subscribers (user_id, tier) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET tier = %s",
            (int(user_id), tier, tier)
        )
        conn.commit()
        cursor.close()
        conn.close()

def is_subscriber(user_id):
    """Check if user is a subscriber"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM subscribers WHERE user_id = %s", (int(user_id),))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result is not None
    return False

def send_telegram_message(chat_id, text, reply_markup=None):
    """Send message to Telegram via Bot API"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return None

def get_ai_response(user_message, user_id):
    """Get AI response from OpenAI"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are Nivalis, Antonio's digital clone and a high-level business strategist. Provide direct, actionable business advice focused on skill monetization and offer creation. Be concise and strategic."
                },
                {
                    "role": "user", 
                    "content": user_message
                }
            ],
            max_tokens=1200,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return "I'm experiencing technical difficulties. Please try again shortly."

@app.route('/')
def index():
    """Main landing page"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Check database connection
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return {"status": "healthy", "database": "connected", "timestamp": datetime.datetime.now().isoformat()}
        else:
            return {"status": "unhealthy", "database": "disconnected"}, 500
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 500

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    """Handle Telegram webhook"""
    try:
        update = request.get_json()
        
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            user_id = str(chat_id)
            
            # Handle /start command
            if text == '/start':
                if is_subscriber(user_id):
                    welcome_text = """🎯 Welcome back to <b>NIVALIS</b>

I'm Antonio's digital clone, your strategic business advisor.

Ready to build your next high-ticket offer? Just tell me:
• What skills do you have?
• What problem are you solving?
• What's your current situation?

Let's turn your expertise into revenue."""
                else:
                    welcome_text = """🎯 Welcome to <b>NIVALIS</b>

I'm Antonio's digital clone - your strategic business advisor for high-ticket offer creation.

<b>Ready to unlock your earning potential?</b>

To access my full strategic consultation capabilities, you'll need Founder's Access (£97 lifetime).

This gives you unlimited access to:
• Strategic business consultation
• High-ticket offer development  
• Market positioning advice
• Revenue optimization strategies

Get started with the Mini App below 👇"""
                    
                    keyboard = {
                        'inline_keyboard': [[
                            {'text': '🚀 Get Founder\'s Access', 'web_app': {'url': f'https://{request.host}'}}
                        ]]
                    }
                    
                    send_telegram_message(chat_id, welcome_text, keyboard)
                    return 'OK'
                
                send_telegram_message(chat_id, welcome_text)
                return 'OK'
            
            # Handle regular messages
            if is_subscriber(user_id):
                ai_response = get_ai_response(text, user_id)
                send_telegram_message(chat_id, ai_response)
            else:
                access_text = """🔒 <b>Full Access Required</b>

To receive strategic consultation, you need Founder's Access.

Get unlimited access to Antonio's business expertise for £97 (lifetime).

Tap below to upgrade 👇"""
                
                keyboard = {
                    'inline_keyboard': [[
                        {'text': '🚀 Get Founder\'s Access', 'web_app': {'url': f'https://{request.host}'}}
                    ]]
                }
                
                send_telegram_message(chat_id, access_text, keyboard)
        
        return 'OK'
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'Error', 500

@app.route('/create-mvp-checkout-session', methods=['POST'])
def create_mvp_checkout_session():
    """Create Stripe checkout session for MVP access"""
    try:
        # Get user_id from form data or Telegram WebApp
        user_id = request.form.get('user_id') or request.json.get('user_id') if request.json else None
        
        if not user_id:
            return "User ID required for payment processing", 400
            
        checkout_session = stripe.checkout.Session.create(
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'product_data': {
                        'name': 'Nivalis Founder\'s Access',
                        'description': 'Lifetime access to Nivalis AI strategic consultation'
                    },
                    'unit_amount': 9700,  # £97.00 in pence
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'https://{request.host}/success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'https://{request.host}/cancel',
            metadata={
                'tier': 'mvp_lifetime',
                'user_id': str(user_id)
            }
        )
        if checkout_session.url:
            return redirect(checkout_session.url, code=303)
        else:
            return "Error creating checkout session", 500
    except Exception as e:
        logger.error(f"Stripe error: {e}")
        return str(e), 400

@app.route('/success')
def success():
    """Payment success page"""
    session_id = request.args.get('session_id')
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == 'paid':
                # Add user to subscribers
                if session.metadata and 'user_id' in session.metadata:
                    user_id = session.metadata['user_id']
                    add_subscriber(user_id, 'mvp_lifetime')
                    logger.info(f"Added subscriber {user_id} via success page")
                
                return render_template('success.html')
        except Exception as e:
            logger.error(f"Success page error: {e}")
    
    return render_template('success.html')

@app.route('/cancel')
def cancel():
    """Payment cancelled page"""
    return render_template('cancel.html')

@app.route('/add-paid-user/<user_id>')
def add_paid_user(user_id):
    """Manually add paid user to subscriber database"""
    try:
        add_subscriber(user_id, 'mvp_lifetime')
        return f"User {user_id} added to subscribers successfully"
    except Exception as e:
        logger.error(f"Error adding user {user_id}: {e}")
        return f"Error: {e}", 500

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET')
        )
        
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = session['metadata'].get('user_id')
            tier = session['metadata'].get('tier', 'mvp_lifetime')
            
            if user_id:
                add_subscriber(user_id, tier)
                logger.info(f"Added subscriber: {user_id} with tier: {tier}")
        
        return 'OK'
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'Error', 400

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
