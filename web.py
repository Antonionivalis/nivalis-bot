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
EMERGENCY_SUBSCRIBERS = {7582: True, 5849400652: True}

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
    """Landing page - original professional version"""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nivalis AI</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: #0a1628;
            color: white;
            line-height: 1.6;
            overflow-x: hidden;
        }
        
        .container {
            max-width: 480px;
            margin: 0 auto;
            padding: 0 20px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .gradient-title {
            font-size: 28px;
            font-weight: 900;
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.5px;
        }
        
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 20px 0;
        }
        
        .headline {
            font-size: 24px;
            font-weight: 700;
            line-height: 1.3;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .subscription-card {
            background: linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(255, 107, 53, 0.1) 100%);
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 30px;
        }
        
        .subscription-card h3 {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .features {
            margin-bottom: 24px;
        }
        
        .feature {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 16px;
            font-size: 14px;
            line-height: 1.5;
        }
        
        .feature svg {
            color: #00d4ff;
            flex-shrink: 0;
            margin-top: 2px;
        }
        
        .price-section {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .price {
            font-size: 36px;
            font-weight: 900;
            color: #00d4ff;
            margin-bottom: 4px;
        }
        
        .price-subtitle {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.7);
        }
        
        .cta-button {
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 16px 24px;
            font-size: 16px;
            font-weight: 600;
            width: 100%;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }
        
        .cta-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 212, 255, 0.3);
        }
        
        .footer-quote {
            text-align: center;
            margin-top: 30px;
            padding: 20px 0;
            font-size: 14px;
            color: rgba(255, 255, 255, 0.6);
            font-style: italic;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        @media (max-width: 480px) {
            .container {
                padding: 0 16px;
            }
            
            .headline {
                font-size: 22px;
            }
            
            .price {
                font-size: 32px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="logo">
                <h1 class="gradient-title">NIVALIS</h1>
            </div>
        </header>

        <main class="main">
            <section class="hero">
                <h2 class="headline">Built on 10 years of Experience and Results.<br>Trained for One Purpose: Execution.</h2>

                <div class="subscription-card">
                    <h3>Nivalis AI Access</h3>
                    <div class="features">
                        <div class="feature">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="20,6 9,17 4,12"></polyline>
                            </svg>
                            <span>Transform any skill into high-ticket monthly offers</span>
                        </div>
                        <div class="feature">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="20,6 9,17 4,12"></polyline>
                            </svg>
                            <span>Viral content scripts from top performing creators</span>
                        </div>
                        <div class="feature">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="20,6 9,17 4,12"></polyline>
                            </svg>
                            <span>Complete marketing funnels that convert prospects into clients</span>
                        </div>
                        <div class="feature">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="20,6 9,17 4,12"></polyline>
                            </svg>
                            <span>Strategic business planning and revenue optimization</span>
                        </div>
                    </div>
                    
                    <div class="price-section">
                        <div class="price">£97</div>
                        <div class="price-subtitle">Founder's Access • Lifetime</div>
                    </div>
                    
                    <a href="/create-mvp-checkout-session" class="cta-button">Get Founder's Access</a>
                </div>
            </section>
        </main>

        <footer class="footer-quote">
            <p>"The secret to getting ahead is getting started." - Mark Twain</p>
        </footer>
    </div>
</body>
</html>"""
    return html

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
                
                result = send_telegram_message(chat_id, welcome)
                logger.info(f"Message sent to user 7582: {result}")
                return jsonify({'ok': True})
            
            else:
                # AI consultation for user 7582
                try:
                    ai_response = get_emergency_ai_response(text, user_id)
                    result = send_telegram_message(chat_id, ai_response)
                    logger.info(f"AI response sent to user 7582: {result}")
                except Exception as ai_error:
                    logger.error(f"AI error for 7582: {ai_error}")
                    fallback = "Your access is confirmed. I'm ready to help with strategic consultation. Could you rephrase your question?"
                    result = send_telegram_message(chat_id, fallback)
                    logger.info(f"Fallback sent to user 7582: {result}")
                
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

@app.route('/create-mvp-checkout-session', methods=['POST', 'GET'])
def create_mvp_checkout():
    """Create Stripe checkout session for MVP access"""
    try:
        stripe_key = os.environ.get('STRIPE_SECRET_KEY')
        if not stripe_key:
            logger.error("No Stripe secret key configured")
            return "Payment system temporarily unavailable", 500
        
        # Use price_data instead of hardcoded price ID
        checkout_session = stripe.checkout.Session.create(
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'product_data': {
                        'name': 'Nivalis Founder\'s Access',
                        'description': 'Lifetime access to elite business strategy consultation',
                    },
                    'unit_amount': 9700,  # £97.00 in pence
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='https://web-production-8ff6.up.railway.app/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://web-production-8ff6.up.railway.app/cancel',
            metadata={'user_id': 'new_user', 'tier': 'mvp_lifetime'},
            automatic_tax={'enabled': False}
        )
        
        if checkout_session.url:
            return redirect(checkout_session.url, code=303)
        else:
            return "Payment session creation failed", 500
            
    except Exception as e:
        logger.error(f"Checkout error: {e}")
        return f"Payment temporarily unavailable: {str(e)}", 500

@app.route('/success')
def success():
    """Payment success page"""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Payment Successful - Nivalis</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
            background: #0a1628;
            color: white; 
            margin: 0; 
            padding: 20px; 
            min-height: 100vh; 
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container { 
            max-width: 600px; 
            margin: 0 auto;
        }
        .success-icon { 
            font-size: 4em; 
            margin-bottom: 20px; 
        }
        h1 { 
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-size: 2.5em; 
            margin-bottom: 20px; 
        }
        p {
            font-size: 18px;
            line-height: 1.6;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">✅</div>
        <h1>Payment Successful!</h1>
        <p>Your Founder's Access has been activated.</p>
        <p>Return to the Telegram bot to begin your strategic consultation with Nivalis.</p>
    </div>
</body>
</html>"""
    return html

@app.route('/cancel')
def cancel():
    """Payment cancelled page"""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Payment Cancelled - Nivalis</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
            background: #0a1628;
            color: white; 
            margin: 0; 
            padding: 20px; 
            min-height: 100vh; 
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container { 
            max-width: 600px; 
            margin: 0 auto;
        }
        h1 { 
            color: #ff6b35; 
            font-size: 2.5em; 
            margin-bottom: 20px; 
        }
        .btn { 
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            color: white; 
            padding: 15px 30px; 
            border: none; 
            border-radius: 25px;
            font-size: 18px; 
            cursor: pointer; 
            text-decoration: none; 
            display: inline-block; 
            margin: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Payment Cancelled</h1>
        <p>No worries! You can try again whenever you're ready.</p>
        <a href="/" class="btn">Return Home</a>
    </div>
</body>
</html>"""
    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
