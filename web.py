import os
import json
import logging
import requests
from flask import Flask, request, jsonify, render_template, redirect
import stripe
from openai import OpenAI

# Emergency production configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "emergency-secret")

# Initialize services
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# Emergency subscriber list - user 7582 is guaranteed access
EMERGENCY_SUBSCRIBERS = {7582: True}

def send_telegram_message(chat_id, text, reply_markup=None):
    """Send message to Telegram"""
    if not BOT_TOKEN:
        return False
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    if reply_markup:
        data['reply_markup'] = reply_markup
    
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False

def is_emergency_subscriber(user_id):
    """Emergency subscriber check"""
    try:
        user_id = int(user_id)
        return user_id in EMERGENCY_SUBSCRIBERS
    except:
        return False

def get_emergency_ai_response(message, user_id):
    """Emergency AI response handler"""
    if not client:
        return "I'm ready to provide strategic consultation. What's your current business challenge?"
    
    try:
        if user_id == 7582:
            system_prompt = """You are Nivalis, Antonio's digital clone. Your paying customer experienced technical issues accessing the service. Acknowledge this professionally and immediately provide high-value strategic business consultation. Be direct and actionable."""
        else:
            system_prompt = "You are Nivalis, Antonio's digital clone providing elite business strategy consultation."
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=800,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"AI error: {e}")
        if user_id == 7582:
            return "Your access is confirmed. Technical issues are resolved. I'm ready to provide strategic consultation. What business challenge can I help you solve?"
        return "I'm experiencing technical difficulties. Please try again."

@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Emergency health check"""
    return jsonify({
        "status": "emergency_mode",
        "user_7582_protected": True,
        "emergency_active": True
    })

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    """Emergency webhook - bulletproof for user 7582"""
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'ok': True})
        
        message = data['message']
        user_id = message['from']['id']
        chat_id = message['chat']['id']
        text = message.get('text', '').strip()
        first_name = message['from'].get('first_name', 'Customer')
        
        logger.info(f"Emergency webhook processing user {user_id}: {text}")
        
        # Emergency handling for user 7582
        if user_id == 7582:
            logger.info("EMERGENCY: Processing user 7582")
            
            if text.startswith('/start'):
                welcome = f"""🎯 <b>Service Restored - Welcome Back</b>

{first_name}, your Founder's Access is confirmed and technical issues have been resolved.

I'm Antonio's digital clone providing elite business strategy consultation. Your premium access includes:

• Strategic business planning and execution
• High-ticket offer development 
• Market analysis and positioning
• Revenue optimization strategies
• Content and marketing frameworks

What's your most pressing business challenge right now?"""
                
                send_telegram_message(chat_id, welcome)
                return jsonify({'ok': True})
            
            else:
                # AI consultation for user 7582
                try:
                    ai_response = get_emergency_ai_response(text, user_id)
                    send_telegram_message(chat_id, ai_response)
                except Exception as ai_error:
                    logger.error(f"AI error for 7582: {ai_error}")
                    fallback = "Your access is confirmed. I'm ready to help with strategic consultation. Could you rephrase your question?"
                    send_telegram_message(chat_id, fallback)
                
                return jsonify({'ok': True})
        
        # Handle other users
        if not is_emergency_subscriber(user_id):
            if text.startswith('/start'):
                access_message = """🚀 <b>Welcome to Nivalis</b>

I'm Antonio's digital clone providing elite business strategy consultation.

<b>Founder's Access - £97 (Lifetime)</b>
• Unlimited strategic consultation
• Business framework development  
• High-ticket offer creation
• Market analysis and positioning

Ready to unlock your potential?"""
                
                keyboard = json.dumps({
                    'inline_keyboard': [[
                        {'text': '🔥 Get Founder\'s Access', 'web_app': {'url': 'https://web-production-8ff6.up.railway.app/'}}
                    ]]
                })
                
                send_telegram_message(chat_id, access_message, keyboard)
            else:
                send_telegram_message(chat_id, "Please get Founder's Access to unlock strategic consultation.")
            
            return jsonify({'ok': True})
        
        # Handle emergency subscribers
        if text.startswith('/start'):
            welcome = f"""🎯 <b>Welcome to Nivalis</b>

{first_name}, your access is confirmed. I'm ready to provide strategic consultation.

What business challenge can I help you solve today?"""
            send_telegram_message(chat_id, welcome)
        else:
            ai_response = get_emergency_ai_response(text, user_id)
            send_telegram_message(chat_id, ai_response)
        
        return jsonify({'ok': True})
        
    except Exception as e:
        logger.error(f"Emergency webhook error: {e}")
        
        # Final failsafe for user 7582
        try:
            data = request.get_json()
            if data and 'message' in data and data['message']['from']['id'] == 7582:
                chat_id = data['message']['chat']['id']
                emergency_msg = "Your Founder's Access is confirmed. System operational. I'm ready for strategic consultation."
                send_telegram_message(chat_id, emergency_msg)
        except:
            pass
        
        return jsonify({'ok': True})

@app.route('/create-mvp-checkout-session', methods=['POST'])
def create_mvp_checkout():
    """Emergency checkout"""
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[{
                'price': 'price_1QKlH1DhGdG2vys0NhcVWvmJ',
                'quantity': 1,
            }],
            mode='payment',
            success_url='https://web-production-8ff6.up.railway.app/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://web-production-8ff6.up.railway.app/cancel',
            metadata={'user_id': 'new_user', 'tier': 'mvp_lifetime'}
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        logger.error(f"Checkout error: {e}")
        return "Payment temporarily unavailable", 500

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/cancel') 
def cancel():
    return render_template('cancel.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
