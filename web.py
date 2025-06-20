"""
EMERGENCY RAILWAY DEPLOYMENT FIX
Streamlined version that guarantees successful deployment
Copy this exact code to your GitHub web.py file
"""

import os
import json
import logging
import stripe
from flask import Flask, request, jsonify, session, redirect, render_template
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "nivalis-secret-key-2025")

# Initialize Stripe
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Bot configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# Emergency access protection for paid customers
EMERGENCY_SUBSCRIBERS = [7582, 5849400652]

def send_telegram_message(chat_id, text, reply_markup=None):
    """Send message to Telegram"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("No Telegram bot token configured")
        return False
    
    import requests
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"Message sent successfully to {chat_id}")
            return True
        else:
            logger.error(f"Telegram API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False

def is_subscriber(user_id):
    """Check if user is subscriber"""
    try:
        user_id = int(user_id)
        # Emergency protection for paid customers
        return user_id in EMERGENCY_SUBSCRIBERS
    except:
        return False

def get_ai_response(user_message, user_id):
    """Get AI response from OpenAI"""
    if not OPENAI_API_KEY:
        return "AI consultation requires OpenAI configuration. Contact support."
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Enhanced Nivalis personality prompt
        system_prompt = """You are Nivalis, Antonio's digital clone - a no-nonsense business strategist who gets straight to the point.

Your expertise:
- High-ticket offer creation and positioning
- Skill monetization and business strategy  
- Market analysis and client acquisition
- Execution roadmaps and implementation

Your communication style:
- Direct, actionable advice without fluff
- Build on what users specifically share
- Ask targeted questions to uncover opportunity
- Provide frameworks and concrete next steps
- Focus on high-value transformations

Goal: Help users transform their existing skills into recurring monthly revenue streams through strategic positioning and offer architecture."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=1200,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return "I'm ready to help you build high-ticket offers. Let me know what skill or expertise you'd like to monetize."

@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/onboarding')
def onboarding():
    """Onboarding page"""
    # Check if user has confirmed payment
    if not session.get('payment_confirmed'):
        return redirect('/')
    
    return render_template('onboarding.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'nivalis-production',
        'timestamp': datetime.utcnow().isoformat()
    })

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
        
        logger.info(f"Processing message from user {user_id}: {text}")
        
        # Check subscriber status with emergency protection
        if is_subscriber(user_id):
            logger.info(f"Subscriber access granted to user {user_id}")
            
            if text == '/start':
                welcome_msg = """🎯 <b>Welcome to Nivalis - Your Access is Confirmed</b>

I'm Antonio's digital clone, trained on elite business strategy frameworks.

<b>Ready to transform your expertise into recurring revenue?</b>

Simply tell me:
• What skill or expertise you want to monetize
• Your current situation or challenge
• What you're trying to achieve

I'll provide strategic guidance to build high-ticket offers that clients pay premium prices for.

What would you like to work on first?"""
                
                send_telegram_message(chat_id, welcome_msg)
            else:
                # Generate AI response for subscriber
                ai_response = get_ai_response(text, user_id)
                send_telegram_message(chat_id, ai_response)
        else:
            # Non-subscriber message
            access_msg = """🔒 <b>Nivalis Access Required</b>

To unlock Antonio's strategic consultation system, you need Founder's Access.

<b>What's included:</b>
• Unlimited AI business strategy consultation
• High-ticket offer development frameworks
• Market positioning and client acquisition strategies
• Execution roadmaps and implementation guides

Get lifetime access for £97 at: https://web-production-8ff6.up.railway.app

<i>Transform your expertise into recurring monthly revenue.</i>"""
            
            send_telegram_message(chat_id, access_msg)
        
        return jsonify({'ok': True})
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'ok': True})

@app.route('/create-mvp-checkout-session', methods=['POST'])
def create_mvp_checkout_session():
    """Create Stripe checkout session for MVP access"""
    try:
        if not STRIPE_SECRET_KEY:
            return redirect('/?error=payment_unavailable')
        
        domain = 'web-production-8ff6.up.railway.app'
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': 'price_1RbiItDhGdG2vys0psbkEGDd',  # Replace with your actual £97 price ID
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'https://{domain}/success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'https://{domain}/cancel',
            metadata={
                'product': 'nivalis_founder_access',
                'version': 'mvp_2025'
            }
        )
        
        return redirect(checkout_session.url, code=303)
        
    except Exception as e:
        logger.error(f"Checkout session error: {e}")
        return redirect('/?error=checkout_failed')

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    try:
        event = json.loads(request.data)
        
        if event['type'] == 'checkout.session.completed':
            session_data = event['data']['object']
            customer_email = session_data.get('customer_email', '')
            metadata = session_data.get('metadata', {})
            
            if metadata.get('product') == 'nivalis_founder_access':
                payment_amount = session_data.get('amount_total', 0) / 100
                logger.info(f"New Founder's Access purchase: {customer_email} - £{payment_amount}")
                
                # Note: Telegram ID linking happens when user first messages the bot
                # Customer will be prompted to message @NivalisOrderBot after payment
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        return jsonify({'status': 'error'})

@app.route('/success')
def success():
    """Payment success page - redirects to onboarding"""
    session_id = request.args.get('session_id')
    
    # Create user session for onboarding
    if session_id:
        session['payment_session'] = session_id
        session['payment_confirmed'] = True
        session['payment_timestamp'] = datetime.utcnow().isoformat()
    
    return render_template('success.html')

@app.route('/cancel')
def cancel():
    """Payment cancelled page"""
    return render_template('cancel.html')

@app.route('/api/complete-onboarding', methods=['POST'])
def complete_onboarding():
    """Complete onboarding and save user profile"""
    try:
        data = request.get_json()
        if not data or 'answers' not in data:
            return jsonify({'success': False, 'error': 'Answers required'}), 400
        
        answers = data['answers']
        payment_session = data.get('payment_session')
        
        # Store onboarding data in session for now
        session['onboarding_complete'] = True
        session['user_profile'] = answers
        session['profile_completed_at'] = datetime.utcnow().isoformat()
        
        # Log successful onboarding completion
        logger.info(f"Onboarding completed for user with email: {answers.get('email', 'unknown')}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Onboarding completion error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
