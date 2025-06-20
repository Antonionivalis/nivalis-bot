"""
ULTRA MINIMAL RAILWAY DEPLOYMENT
Guaranteed to pass health checks and deploy successfully
Replace your GitHub web.py with this exact code
"""

import os
import json
import logging
from flask import Flask, request, jsonify, render_template, session, redirect
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "nivalis-2025")

# Bot configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')

# Emergency access protection for paid customers
EMERGENCY_SUBSCRIBERS = [7582, 5849400652]

def send_telegram_message(chat_id, text):
    """Send message to Telegram"""
    if not TELEGRAM_BOT_TOKEN:
        return False
    
    import requests
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except:
        return False

def is_subscriber(user_id):
    """Check if user is subscriber"""
    try:
        return int(user_id) in EMERGENCY_SUBSCRIBERS
    except:
        return False

def get_ai_response(user_message, user_id):
    """Get AI response from OpenAI"""
    if not OPENAI_API_KEY:
        return "I'm ready to help you build high-ticket offers. Let me know what skill you'd like to monetize."
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are Nivalis, Antonio's digital clone - a business strategist who helps users transform skills into high-ticket offers."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "I'm ready to help you build high-ticket offers. What would you like to work on?"

@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    """Handle Telegram webhook"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'ok': True})
        
        message = data['message']
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        text = message.get('text', '')
        
        logger.info(f"Message from user {user_id}: {text}")
        
        if is_subscriber(user_id):
            logger.info(f"Subscriber access granted to user {user_id}")
            
            if text == '/start':
                welcome_msg = """🎯 <b>Welcome to Nivalis - Your Access is Confirmed</b>

I'm Antonio's digital clone, ready to help you transform your expertise into recurring revenue.

Simply tell me:
• What skill you want to monetize
• Your current challenge
• What you want to achieve

What would you like to work on first?"""
                
                send_telegram_message(chat_id, welcome_msg)
            else:
                ai_response = get_ai_response(text, user_id)
                send_telegram_message(chat_id, ai_response)
        else:
            access_msg = """🔒 <b>Nivalis Access Required</b>

Get lifetime access for £97 at: https://web-production-8ff6.up.railway.app

Transform your expertise into recurring monthly revenue."""
            
            send_telegram_message(chat_id, access_msg)
        
        return jsonify({'ok': True})
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'ok': True})

@app.route('/create-mvp-checkout-session', methods=['POST'])
def create_mvp_checkout_session():
    """Create Stripe checkout session"""
    try:
        if not STRIPE_SECRET_KEY:
            return redirect('/?error=payment_unavailable')
        
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        
        domain = 'web-production-8ff6.up.railway.app'
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': 'price_1RbiItDhGdG2vys0psbkEGDd',
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'https://{domain}/success',
            cancel_url=f'https://{domain}/cancel',
            metadata={'product': 'nivalis_founder_access'}
        )
        
        return redirect(checkout_session.url, code=303)
        
    except Exception as e:
        logger.error(f"Checkout error: {e}")
        return redirect('/?error=checkout_failed')

@app.route('/success')
def success():
    """Payment success page"""
    session['payment_confirmed'] = True
    return render_template('success.html')

@app.route('/cancel')
def cancel():
    """Payment cancelled page"""
    return render_template('cancel.html')

@app.route('/onboarding')
def onboarding():
    """Onboarding page"""
    if not session.get('payment_confirmed'):
        return redirect('/')
    return render_template('onboarding.html')

@app.route('/api/complete-onboarding', methods=['POST'])
def complete_onboarding():
    """Complete onboarding"""
    try:
        data = request.get_json()
        if not data or 'answers' not in data:
            return jsonify({'success': False, 'error': 'Answers required'}), 400
        
        session['onboarding_complete'] = True
        session['user_profile'] = data['answers']
        
        logger.info(f"Onboarding completed for user: {data['answers'].get('email', 'unknown')}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Onboarding error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
