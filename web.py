"""
Complete Railway Deployment Package for GitHub Upload
Copy this exact file to your GitHub repository as web.py
"""

import os
import json
import logging
import stripe
from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

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
    """Landing page with embedded HTML"""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NIVALIS - Elite Business Strategy</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #0a1628 0%, #1e3a8a 50%, #0a1628 100%);
            color: #ffffff;
            line-height: 1.6;
            min-height: 100vh;
            overflow-x: hidden;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }

        .hero {
            padding: 60px 0 80px;
            text-align: center;
            position: relative;
        }

        .logo {
            font-size: 4rem;
            font-weight: 900;
            letter-spacing: 0.05em;
            margin-bottom: 20px;
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .tagline {
            font-size: 1.5rem;
            margin-bottom: 50px;
            color: #94a3b8;
            font-weight: 400;
        }

        .offer-section {
            background: rgba(15, 23, 42, 0.8);
            border-radius: 24px;
            padding: 50px 40px;
            margin-bottom: 50px;
            border: 1px solid rgba(0, 212, 255, 0.2);
            backdrop-filter: blur(10px);
        }

        .offer-title {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 15px;
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .offer-subtitle {
            font-size: 1.2rem;
            color: #94a3b8;
            margin-bottom: 40px;
        }

        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 30px;
            margin-bottom: 50px;
        }

        .feature {
            background: rgba(30, 41, 59, 0.5);
            padding: 30px;
            border-radius: 16px;
            border: 1px solid rgba(0, 212, 255, 0.1);
            transition: all 0.3s ease;
        }

        .feature:hover {
            transform: translateY(-5px);
            border-color: rgba(0, 212, 255, 0.3);
            box-shadow: 0 20px 40px rgba(0, 212, 255, 0.1);
        }

        .feature h3 {
            font-size: 1.3rem;
            margin-bottom: 15px;
            color: #00d4ff;
        }

        .feature p {
            color: #94a3b8;
            line-height: 1.6;
        }

        .cta-button {
            display: inline-block;
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            color: white;
            text-decoration: none;
            padding: 20px 50px;
            border-radius: 50px;
            font-weight: 700;
            font-size: 1.2rem;
            transition: all 0.3s ease;
            border: none;
            cursor: pointer;
            box-shadow: 0 10px 30px rgba(0, 212, 255, 0.3);
        }

        .cta-button:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 40px rgba(0, 212, 255, 0.4);
        }

        .price {
            font-size: 3rem;
            font-weight: 900;
            margin: 30px 0;
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .footer {
            text-align: center;
            padding: 60px 0 40px;
            color: #64748b;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            margin-top: 80px;
        }

        .quote {
            font-style: italic;
            font-size: 1.1rem;
            margin-bottom: 10px;
        }

        .quote-author {
            font-size: 0.9rem;
            opacity: 0.8;
        }

        @media (max-width: 768px) {
            .logo {
                font-size: 2.5rem;
            }
            
            .tagline {
                font-size: 1.2rem;
            }
            
            .offer-title {
                font-size: 2rem;
            }
            
            .offer-section {
                padding: 30px 20px;
            }
            
            .price {
                font-size: 2.2rem;
            }
            
            .cta-button {
                padding: 18px 40px;
                font-size: 1.1rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <section class="hero">
            <h1 class="logo">NIVALIS</h1>
            <p class="tagline">Antonio's Digital Clone - Elite Business Strategy</p>
            
            <div class="offer-section">
                <h2 class="offer-title">Founder's Access</h2>
                <p class="offer-subtitle">Transform Your Skills Into High-Ticket Monthly Offers</p>
                
                <div class="features-grid">
                    <div class="feature">
                        <h3>Strategic Consultation</h3>
                        <p>One-on-one guidance to identify your highest-value skills and transform them into profitable offers that clients pay premium prices for.</p>
                    </div>
                    
                    <div class="feature">
                        <h3>Offer Architecture</h3>
                        <p>Complete framework development for recurring monthly retainers, positioning you as the go-to expert in your field.</p>
                    </div>
                    
                    <div class="feature">
                        <h3>Market Positioning</h3>
                        <p>Advanced strategies used by top performing creators to dominate their niche and attract high-ticket clients consistently.</p>
                    </div>
                    
                    <div class="feature">
                        <h3>Execution Roadmap</h3>
                        <p>Step-by-step implementation plans that eliminate guesswork and accelerate your path to recurring revenue.</p>
                    </div>
                </div>
                
                <div class="price">£97 - Lifetime Access</div>
                
                <form action="/create-mvp-checkout-session" method="POST">
                    <button type="submit" class="cta-button">
                        🔥 Get Founder's Access
                    </button>
                </form>
            </div>
        </section>
    </div>
    
    <footer class="footer">
        <div class="container">
            <p class="quote">"The secret of getting ahead is getting started."</p>
            <p class="quote-author">— Mark Twain</p>
        </div>
    </footer>

    <script>
        // Telegram WebApp initialization
        const tg = window.Telegram?.WebApp;
        if (tg) {
            tg.ready();
            tg.expand();
        }
    </script>
</body>
</html>"""
    return html

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
                'price': 'price_1RbiItDhGdG2vys0psbkEGDd',  # £97 price ID
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
    
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Payment Successful - Nivalis</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #0a1628 0%, #1e3a8a 50%, #0a1628 100%);
            color: #ffffff;
            text-align: center;
            padding: 60px 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .success-container {
            max-width: 600px;
            background: rgba(15, 23, 42, 0.9);
            padding: 50px;
            border-radius: 24px;
            border: 1px solid rgba(0, 212, 255, 0.3);
        }
        .success-icon {
            font-size: 4rem;
            margin-bottom: 20px;
        }
        .success-title {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 15px;
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .success-message {
            font-size: 1.2rem;
            margin-bottom: 30px;
            color: #94a3b8;
            line-height: 1.6;
        }
        .onboarding-button {
            display: inline-block;
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            color: white;
            text-decoration: none;
            padding: 20px 40px;
            border-radius: 50px;
            font-weight: 700;
            font-size: 1.1rem;
            margin: 20px 0;
            border: none;
            cursor: pointer;
        }
        .onboarding-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 40px rgba(0, 212, 255, 0.4);
        }
        .instructions {
            background: rgba(30, 41, 59, 0.5);
            padding: 25px;
            border-radius: 16px;
            margin-top: 30px;
            text-align: left;
        }
        .instructions h3 {
            color: #00d4ff;
            margin-bottom: 15px;
        }
        .instructions ol {
            padding-left: 20px;
        }
        .instructions li {
            margin-bottom: 10px;
            color: #94a3b8;
        }
    </style>
</head>
<body>
    <div class="success-container">
        <div class="success-icon">🎉</div>
        <h1 class="success-title">Payment Successful!</h1>
        <p class="success-message">
            Your Founder's Access to Nivalis has been activated. 
            Complete your business profile to receive personalized AI consultation.
        </p>
        
        <button onclick="startOnboarding()" class="onboarding-button">
            🚀 Complete Your Business Profile
        </button>
        
        <div class="instructions">
            <h3>What Happens Next:</h3>
            <ol>
                <li>Complete your <strong>business intelligence profile</strong> (12 strategic questions)</li>
                <li>Receive your <strong>personalized consultation access</strong></li>
                <li>Message @NivalisOrderBot for <strong>unlimited AI strategy sessions</strong></li>
                <li>Get frameworks for <strong>high-ticket offer development</strong></li>
            </ol>
            <p style="color: #00d4ff; margin-top: 20px; font-weight: 600;">
                ⚡ Your responses help Nivalis provide targeted business strategy specific to your situation.
            </p>
        </div>
    </div>

    <script>
        const tg = window.Telegram?.WebApp;
        if (tg) {
            tg.ready();
            tg.expand();
        }

        function startOnboarding() {
            // Store payment confirmation and redirect to onboarding
            window.location.href = '/onboarding';
        }
    </script>
</body>
</html>"""
    return html

@app.route('/cancel')
def cancel():
    """Payment cancelled page"""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Payment Cancelled - Nivalis</title>
    <style>
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #0a1628 0%, #1e3a8a 50%, #0a1628 100%);
            color: #ffffff;
            text-align: center;
            padding: 60px 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .cancel-container {
            max-width: 500px;
            background: rgba(15, 23, 42, 0.9);
            padding: 50px;
            border-radius: 24px;
            border: 1px solid rgba(255, 107, 53, 0.3);
        }
        .cancel-title {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 15px;
            color: #ff6b35;
        }
        .cancel-message {
            font-size: 1.1rem;
            margin-bottom: 30px;
            color: #94a3b8;
            line-height: 1.6;
        }
        .return-link {
            display: inline-block;
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            color: white;
            text-decoration: none;
            padding: 15px 35px;
            border-radius: 50px;
            font-weight: 700;
        }
    </style>
</head>
<body>
    <div class="cancel-container">
        <h1 class="cancel-title">Payment Cancelled</h1>
        <p class="cancel-message">
            No worries! Your payment was cancelled and no charges were made. 
            You can return to secure your Founder's Access whenever you're ready.
        </p>
        <a href="/" class="return-link">Return to Nivalis</a>
    </div>
</body>
</html>"""
    return html

@app.route('/onboarding')
def onboarding():
    """Onboarding page with 12-question business intelligence flow"""
    # Check if user has confirmed payment
    if not session.get('payment_confirmed'):
        return redirect('/')
    
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Business Intelligence Profile - Nivalis</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #0a1628 0%, #1e3a8a 50%, #0a1628 100%);
            color: #ffffff;
            line-height: 1.6;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 50px;
        }
        
        .logo {
            font-size: 2.5rem;
            font-weight: 900;
            letter-spacing: 0.05em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .subtitle {
            font-size: 1.2rem;
            color: #94a3b8;
            margin-bottom: 30px;
        }
        
        .progress-bar {
            width: 100%;
            height: 6px;
            background: rgba(30, 41, 59, 0.8);
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 40px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            border-radius: 10px;
            width: 0%;
            transition: width 0.3s ease;
        }
        
        .question-card {
            background: rgba(15, 23, 42, 0.9);
            border-radius: 24px;
            padding: 40px;
            border: 1px solid rgba(0, 212, 255, 0.2);
            backdrop-filter: blur(10px);
            margin-bottom: 30px;
            display: none;
        }
        
        .question-card.active {
            display: block;
            animation: slideIn 0.5s ease;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .question-number {
            font-size: 0.9rem;
            color: #00d4ff;
            font-weight: 600;
            margin-bottom: 10px;
        }
        
        .question-text {
            font-size: 1.4rem;
            font-weight: 600;
            margin-bottom: 30px;
            color: #ffffff;
        }
        
        .input-group {
            margin-bottom: 30px;
        }
        
        .text-input {
            width: 100%;
            padding: 15px 20px;
            background: rgba(30, 41, 59, 0.8);
            border: 2px solid rgba(0, 212, 255, 0.2);
            border-radius: 12px;
            color: #ffffff;
            font-size: 1rem;
            transition: all 0.3s ease;
        }
        
        .text-input:focus {
            outline: none;
            border-color: #00d4ff;
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
        }
        
        .text-input::placeholder {
            color: #64748b;
        }
        
        .choice-options {
            display: grid;
            gap: 15px;
        }
        
        .choice-option {
            padding: 15px 20px;
            background: rgba(30, 41, 59, 0.6);
            border: 2px solid rgba(0, 212, 255, 0.2);
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
            color: #ffffff;
        }
        
        .choice-option:hover {
            border-color: #00d4ff;
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0, 212, 255, 0.2);
        }
        
        .choice-option.selected {
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            border-color: #00d4ff;
            color: #ffffff;
        }
        
        .multiple-choice {
            display: grid;
            gap: 10px;
        }
        
        .checkbox-option {
            display: flex;
            align-items: center;
            padding: 12px 15px;
            background: rgba(30, 41, 59, 0.6);
            border: 2px solid rgba(0, 212, 255, 0.2);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .checkbox-option:hover {
            border-color: #00d4ff;
        }
        
        .checkbox-option.selected {
            background: rgba(0, 212, 255, 0.2);
            border-color: #00d4ff;
        }
        
        .checkbox {
            width: 18px;
            height: 18px;
            border: 2px solid #64748b;
            border-radius: 4px;
            margin-right: 12px;
            position: relative;
        }
        
        .checkbox-option.selected .checkbox {
            background: #00d4ff;
            border-color: #00d4ff;
        }
        
        .checkbox-option.selected .checkbox::after {
            content: '✓';
            position: absolute;
            top: -2px;
            left: 2px;
            color: #ffffff;
            font-weight: bold;
            font-size: 12px;
        }
        
        .buttons {
            display: flex;
            gap: 20px;
            justify-content: space-between;
            margin-top: 40px;
        }
        
        .btn {
            padding: 15px 30px;
            border-radius: 50px;
            font-weight: 700;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            border: none;
            min-width: 120px;
        }
        
        .btn-secondary {
            background: rgba(30, 41, 59, 0.8);
            color: #94a3b8;
            border: 2px solid rgba(0, 212, 255, 0.2);
        }
        
        .btn-secondary:hover {
            border-color: #00d4ff;
            color: #ffffff;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            color: #ffffff;
            box-shadow: 0 10px 30px rgba(0, 212, 255, 0.3);
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 40px rgba(0, 212, 255, 0.4);
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none !important;
        }
        
        .completion-card {
            display: none;
            text-align: center;
        }
        
        .completion-card.active {
            display: block;
        }
        
        .completion-icon {
            font-size: 4rem;
            margin-bottom: 20px;
        }
        
        .completion-title {
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 15px;
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .completion-message {
            font-size: 1.1rem;
            color: #94a3b8;
            margin-bottom: 30px;
            line-height: 1.6;
        }
        
        .bot-access-btn {
            display: inline-block;
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            color: white;
            text-decoration: none;
            padding: 20px 40px;
            border-radius: 50px;
            font-weight: 700;
            font-size: 1.2rem;
            transition: all 0.3s ease;
            box-shadow: 0 15px 40px rgba(0, 212, 255, 0.3);
        }
        
        .bot-access-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 20px 50px rgba(0, 212, 255, 0.4);
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 20px 10px;
            }
            
            .question-card {
                padding: 25px;
            }
            
            .buttons {
                flex-direction: column;
            }
            
            .btn {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="logo">NIVALIS</h1>
            <p class="subtitle">Business Intelligence Profile</p>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill" id="progressFill"></div>
        </div>
        
        <div id="questionContainer">
            <!-- Questions will be loaded here -->
        </div>
        
        <div class="question-card completion-card" id="completionCard">
            <div class="completion-icon">🎯</div>
            <h2 class="completion-title">Profile Complete!</h2>
            <p class="completion-message">
                Your business intelligence profile has been created. Nivalis now has the context needed to provide targeted strategic consultation for your specific situation.
            </p>
            <a href="https://t.me/NivalisOrderBot" class="bot-access-btn" target="_blank">
                🚀 Access Nivalis Consultation
            </a>
        </div>
    </div>

    <script>
        const tg = window.Telegram?.WebApp;
        if (tg) {
            tg.ready();
            tg.expand();
        }

        // Onboarding questions data
        const questions = [
            {
                id: 'name',
                question: 'What\'s your full name?',
                type: 'text',
                placeholder: 'Enter your full name'
            },
            {
                id: 'email',
                question: 'What\'s your email address?',
                type: 'email',
                placeholder: 'Enter your email'
            },
            {
                id: 'telegram_username',
                question: 'What\'s your Telegram username? (optional)',
                type: 'text',
                placeholder: 'Without the @ symbol'
            },
            {
                id: 'current_income',
                question: 'What\'s your current monthly income range?',
                type: 'choice',
                options: [
                    '£0 - £1,000',
                    '£1,000 - £5,000',
                    '£5,000 - £10,000',
                    '£10,000 - £25,000',
                    '£25,000 - £50,000',
                    '£50,000+'
                ]
            },
            {
                id: 'income_goal',
                question: 'What\'s your monthly income goal?',
                type: 'choice',
                options: [
                    '£5,000 - £10,000',
                    '£10,000 - £25,000',
                    '£25,000 - £50,000',
                    '£50,000 - £100,000',
                    '£100,000+'
                ]
            },
            {
                id: 'business_experience',
                question: 'What\'s your business experience level?',
                type: 'choice',
                options: [
                    'Complete beginner',
                    'Some experience, no revenue yet',
                    'Making some money (under £1k/month)',
                    'Consistent revenue (£1k-£10k/month)',
                    'Established business (£10k+/month)'
                ]
            },
            {
                id: 'available_capital',
                question: 'How much capital do you have available to invest?',
                type: 'choice',
                options: [
                    '£0 - £500',
                    '£500 - £2,000',
                    '£2,000 - £10,000',
                    '£10,000 - £50,000',
                    '£50,000+'
                ]
            },
            {
                id: 'current_stage',
                question: 'What stage are you at right now?',
                type: 'choice',
                options: [
                    'Looking for business ideas',
                    'Have an idea, need validation',
                    'Validating/testing my concept',
                    'Building my first product/service',
                    'Have product, need customers',
                    'Scaling existing business'
                ]
            },
            {
                id: 'time_commitment',
                question: 'How many hours per week can you dedicate to your business?',
                type: 'choice',
                options: [
                    '5-10 hours (part-time)',
                    '10-20 hours (serious side hustle)',
                    '20-40 hours (almost full-time)',
                    '40+ hours (full-time commitment)'
                ]
            },
            {
                id: 'biggest_challenge',
                question: 'What\'s your biggest challenge right now?',
                type: 'choice',
                options: [
                    'Finding the right business idea',
                    'Understanding my target market',
                    'Creating a compelling offer',
                    'Marketing and lead generation',
                    'Converting leads to sales',
                    'Scaling and systemizing',
                    'Creating content'
                ]
            },
            {
                id: 'skills_expertise',
                question: 'What skills or expertise do you have? (Select all that apply)',
                type: 'multiple_choice',
                options: [
                    'Marketing/Advertising',
                    'Sales',
                    'Technical/Programming',
                    'Design/Creative',
                    'Writing/Content',
                    'Consulting/Coaching',
                    'Finance/Accounting',
                    'Operations/Project Management',
                    'Industry-specific knowledge',
                    'Other'
                ]
            },
            {
                id: 'urgency_level',
                question: 'How urgent is your need to increase income?',
                type: 'choice',
                options: [
                    'Not urgent, just exploring',
                    'Would be nice within 6-12 months',
                    'Important within 3-6 months',
                    'Critical within 1-3 months',
                    'Extremely urgent (financial pressure)'
                ]
            }
        ];

        let currentQuestion = 0;
        let answers = {};

        function updateProgress() {
            const progress = ((currentQuestion) / questions.length) * 100;
            document.getElementById('progressFill').style.width = progress + '%';
        }

        function renderQuestion(index) {
            const question = questions[index];
            const container = document.getElementById('questionContainer');
            
            let inputHtml = '';
            
            if (question.type === 'text' || question.type === 'email') {
                inputHtml = `
                    <div class="input-group">
                        <input type="${question.type}" 
                               class="text-input" 
                               id="answer_${question.id}"
                               placeholder="${question.placeholder}"
                               value="${answers[question.id] || ''}"
                               onchange="saveAnswer('${question.id}', this.value)">
                    </div>
                `;
            } else if (question.type === 'choice') {
                inputHtml = `
                    <div class="choice-options">
                        ${question.options.map(option => `
                            <div class="choice-option ${answers[question.id] === option ? 'selected' : ''}"
                                 onclick="selectChoice('${question.id}', '${option}')">
                                ${option}
                            </div>
                        `).join('')}
                    </div>
                `;
            } else if (question.type === 'multiple_choice') {
                const selectedAnswers = answers[question.id] || [];
                inputHtml = `
                    <div class="multiple-choice">
                        ${question.options.map(option => `
                            <div class="checkbox-option ${selectedAnswers.includes(option) ? 'selected' : ''}"
                                 onclick="toggleMultipleChoice('${question.id}', '${option}')">
                                <div class="checkbox"></div>
                                ${option}
                            </div>
                        `).join('')}
                    </div>
                `;
            }
            
            container.innerHTML = `
                <div class="question-card active">
                    <div class="question-number">Question ${index + 1} of ${questions.length}</div>
                    <h2 class="question-text">${question.question}</h2>
                    ${inputHtml}
                    <div class="buttons">
                        <button class="btn btn-secondary" onclick="previousQuestion()" ${index === 0 ? 'style="visibility: hidden;"' : ''}>
                            Previous
                        </button>
                        <button class="btn btn-primary" onclick="nextQuestion()" id="nextBtn">
                            ${index === questions.length - 1 ? 'Complete Profile' : 'Next'}
                        </button>
                    </div>
                </div>
            `;
            
            updateProgress();
        }

        function saveAnswer(questionId, value) {
            answers[questionId] = value;
        }

        function selectChoice(questionId, option) {
            answers[questionId] = option;
            renderQuestion(currentQuestion);
        }

        function toggleMultipleChoice(questionId, option) {
            if (!answers[questionId]) answers[questionId] = [];
            
            const index = answers[questionId].indexOf(option);
            if (index > -1) {
                answers[questionId].splice(index, 1);
            } else {
                answers[questionId].push(option);
            }
            
            renderQuestion(currentQuestion);
        }

        function nextQuestion() {
            if (currentQuestion === questions.length - 1) {
                completeOnboarding();
            } else {
                currentQuestion++;
                renderQuestion(currentQuestion);
            }
        }

        function previousQuestion() {
            if (currentQuestion > 0) {
                currentQuestion--;
                renderQuestion(currentQuestion);
            }
        }

        async function completeOnboarding() {
            try {
                const response = await fetch('/api/complete-onboarding', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        answers: answers,
                        payment_session: sessionStorage.getItem('payment_session')
                    })
                });

                if (response.ok) {
                    showCompletion();
                } else {
                    alert('Error saving profile. Please try again.');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error saving profile. Please try again.');
            }
        }

        function showCompletion() {
            document.getElementById('questionContainer').style.display = 'none';
            document.getElementById('completionCard').classList.add('active');
            document.getElementById('progressFill').style.width = '100%';
        }

        // Initialize first question
        renderQuestion(0);
    </script>
</body>
</html>"""
    return html

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
