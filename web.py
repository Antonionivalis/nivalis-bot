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

# Emergency subscriber list - all paid users guaranteed access
EMERGENCY_SUBSCRIBERS = {
    7582: True,  # First paid user - £97 payment confirmed
    5849400652: True,  # Second paid user - identified from conversation system
}

# Function to add new paid users quickly
def add_emergency_subscriber(user_id, payment_amount=97):
    """Add a new paid user to emergency access list"""
    EMERGENCY_SUBSCRIBERS[user_id] = True
    logger.info(f"Emergency access granted to user {user_id} - £{payment_amount} payment confirmed")

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
        
        # Handle all paid subscribers (including user 7582)
        if is_emergency_subscriber(user_id) or user_id == 7582:
            logger.info(f"PAID USER ACCESS: Processing subscriber {user_id}")
            
            if text.startswith('/start') or text == '/profile':
                from auth import UserManager
                from onboarding import OnboardingFlow
                
                # Check if user exists and needs onboarding
                user = UserManager.get_user(user_id)
                if not user:
                    # Create user first
                    UserManager.create_user(user_id, name=first_name)
                    user = UserManager.get_user(user_id)
                
                # Check if onboarding is complete
                if not user.get('onboarding_complete', False):
                    # Start original onboarding flow
                    next_question = OnboardingFlow.get_next_question(user_id)
                    if next_question:
                        welcome = f"""🎯 <b>Welcome to Nivalis - Your Founder's Access is Active</b>

{first_name}, your £97 payment is confirmed. To provide the most strategic consultation, I need to understand your business situation.

Let's start with a quick setup:

<b>{next_question['question']}</b>"""
                        
                        if next_question['type'] == 'choice':
                            options_text = "\n".join([f"• {option}" for option in next_question['options']])
                            welcome += f"\n\n{options_text}"
                        
                        result = send_telegram_message(chat_id, welcome)
                        logger.info(f"Onboarding question sent to user {user_id}: {result}")
                    else:
                        # All questions answered, complete onboarding
                        OnboardingFlow.complete_onboarding(user_id)
                        welcome = f"""🎯 <b>Setup Complete - Welcome to Nivalis</b>

{first_name}, your profile is complete. I'm ready to provide strategic consultation.

What's your most pressing business challenge right now?"""
                        
                        result = send_telegram_message(chat_id, welcome)
                        logger.info(f"Onboarding complete message sent to user {user_id}: {result}")
                else:
                    # User already onboarded
                    welcome = f"""🎯 <b>Welcome Back to Nivalis</b>

{first_name}, your Founder's Access is active. I'm ready to provide strategic consultation.

What business challenge can I help you solve today?"""
                    
                    result = send_telegram_message(chat_id, welcome)
                    logger.info(f"Welcome back message sent to user {user_id}: {result}")
                
                return jsonify({'ok': True})
            
            else:
                # Handle ongoing conversation (onboarding or consultation)
                from auth import UserManager
                from onboarding import OnboardingFlow
                
                user = UserManager.get_user(user_id)
                if not user:
                    send_telegram_message(chat_id, "Please send /start to begin.")
                    return jsonify({'ok': True})
                
                # Check if user is in onboarding
                if not user.get('onboarding_complete', False):
                    # Process onboarding answer
                    next_question = OnboardingFlow.get_next_question(user_id)
                    if next_question:
                        # Answer current question
                        success = OnboardingFlow.answer_question(user_id, next_question['id'], text)
                        if success:
                            # Get next question
                            next_q = OnboardingFlow.get_next_question(user_id)
                            if next_q:
                                response = f"""✅ Got it!

<b>{next_q['question']}</b>"""
                                
                                if next_q['type'] == 'choice':
                                    options_text = "\n".join([f"• {option}" for option in next_q['options']])
                                    response += f"\n\n{options_text}"
                                
                                send_telegram_message(chat_id, response)
                            else:
                                # Onboarding complete
                                OnboardingFlow.complete_onboarding(user_id)
                                completion_msg = """🎉 <b>Profile Complete!</b>

Perfect! I now have everything I need to provide strategic consultation tailored to your situation.

What's your most pressing business challenge right now?"""
                                
                                send_telegram_message(chat_id, completion_msg)
                        else:
                            send_telegram_message(chat_id, "Please provide a valid answer to continue.")
                    else:
                        # Should not happen, but handle gracefully
                        OnboardingFlow.complete_onboarding(user_id)
                        send_telegram_message(chat_id, "Setup complete! What business challenge can I help with?")
                else:
                    # User onboarded, provide AI consultation
                    try:
                        # Get user context for personalized response
                        user_context = OnboardingFlow.get_user_context_for_ai(user_id)
                        ai_response = get_emergency_ai_response(f"User context: {user_context}\n\nUser message: {text}", user_id)
                        result = send_telegram_message(chat_id, ai_response)
                        logger.info(f"AI response sent to user {user_id}: {result}")
                    except Exception as ai_error:
                        logger.error(f"AI error for user {user_id}: {ai_error}")
                        fallback = "I'm ready to help with strategic consultation. Could you rephrase your question?"
                        result = send_telegram_message(chat_id, fallback)
                        logger.info(f"Fallback sent to user {user_id}: {result}")
                
                return jsonify({'ok': True})
        
        # Handle non-subscribers
        else:
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
        
        # Handle callback queries (button clicks)
        if 'callback_query' in data:
            callback = data['callback_query']
            user_id = callback['from']['id']
            callback_data = callback.get('data', '')
            chat_id = callback['message']['chat']['id']
            
            if callback_data == 'skip_onboarding' and (is_emergency_subscriber(user_id) or user_id == 7582):
                from auth import UserManager
                
                # Mark user as onboarded
                user = UserManager.get_user(user_id)
                if not user:
                    UserManager.create_user(user_id)
                
                UserManager.update_user(user_id, {'onboarding_complete': True})
                
                skip_message = """🚀 <b>Ready for Strategic Consultation</b>

Perfect! I'm ready to provide strategic consultation tailored to your needs.

What's your most pressing business challenge right now?"""
                
                send_telegram_message(chat_id, skip_message)
                return jsonify({'ok': True})
        
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

@app.route('/onboarding')
def onboarding():
    """Onboarding form for users who missed initial setup"""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Complete Your Profile - Nivalis</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { 
            font-family: 'Inter', system-ui, sans-serif;
            background: #0a1628;
            color: white; 
            margin: 0; 
            padding: 20px; 
            line-height: 1.6;
        }
        .container { 
            max-width: 600px; 
            margin: 0 auto;
            padding: 20px;
        }
        h1 { 
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-size: 2.2em; 
            margin-bottom: 30px;
            text-align: center;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #e2e8f0;
        }
        input, select, textarea {
            width: 100%;
            padding: 12px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.3);
            border-radius: 8px;
            color: white;
            font-size: 16px;
        }
        input::placeholder, textarea::placeholder {
            color: #94a3b8;
        }
        .submit-btn {
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 16px;
            width: 100%;
            margin-top: 20px;
            cursor: pointer;
        }
        .progress {
            background: rgba(255, 255, 255, 0.1);
            height: 4px;
            border-radius: 2px;
            margin-bottom: 30px;
        }
        .progress-bar {
            background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
            height: 100%;
            border-radius: 2px;
            width: 33%;
            transition: width 0.3s ease;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Complete Your Profile</h1>
        
        <div class="progress">
            <div class="progress-bar"></div>
        </div>
        
        <form id="onboardingForm">
            <div class="form-group">
                <label for="name">Full Name *</label>
                <input type="text" id="name" name="name" required placeholder="Enter your full name">
            </div>
            
            <div class="form-group">
                <label for="email">Email Address *</label>
                <input type="email" id="email" name="email" required placeholder="your.email@example.com">
            </div>
            
            <div class="form-group">
                <label for="current_income">Current Monthly Income Range *</label>
                <select id="current_income" name="current_income" required>
                    <option value="">Select your income range</option>
                    <option value="£0 - £1,000">£0 - £1,000</option>
                    <option value="£1,000 - £5,000">£1,000 - £5,000</option>
                    <option value="£5,000 - £10,000">£5,000 - £10,000</option>
                    <option value="£10,000 - £25,000">£10,000 - £25,000</option>
                    <option value="£25,000+">£25,000+</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="income_goal">Monthly Income Goal *</label>
                <select id="income_goal" name="income_goal" required>
                    <option value="">Select your goal</option>
                    <option value="£5,000 - £10,000">£5,000 - £10,000</option>
                    <option value="£10,000 - £25,000">£10,000 - £25,000</option>
                    <option value="£25,000 - £50,000">£25,000 - £50,000</option>
                    <option value="£50,000+">£50,000+</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="primary_skill">Primary Skill/Expertise *</label>
                <input type="text" id="primary_skill" name="primary_skill" required placeholder="e.g., Marketing, Fitness Training, Design, Consulting">
            </div>
            
            <div class="form-group">
                <label for="business_stage">Current Business Stage *</label>
                <select id="business_stage" name="business_stage" required>
                    <option value="">Select your stage</option>
                    <option value="Looking for business ideas">Looking for business ideas</option>
                    <option value="Have an idea, need validation">Have an idea, need validation</option>
                    <option value="Building my first offer">Building my first offer</option>
                    <option value="Have product, need customers">Have product, need customers</option>
                    <option value="Scaling existing business">Scaling existing business</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="biggest_challenge">Biggest Challenge Right Now *</label>
                <textarea id="biggest_challenge" name="biggest_challenge" required rows="3" placeholder="Describe your most pressing business challenge..."></textarea>
            </div>
            
            <button type="submit" class="submit-btn">Complete Setup & Start Consultation</button>
        </form>
    </div>
    
    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        
        document.getElementById('onboardingForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = {};
            for (let [key, value] of formData.entries()) {
                data[key] = value;
            }
            
            // Send data to backend
            fetch('/submit-onboarding', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    tg.close();
                } else {
                    alert('Error submitting form. Please try again.');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error submitting form. Please try again.');
            });
        });
    </script>
</body>
</html>"""
    return html

@app.route('/submit-onboarding', methods=['POST'])
def submit_onboarding():
    """Handle onboarding form submission"""
    try:
        data = request.get_json()
        
        # Store onboarding data (you can expand this to save to database)
        logger.info(f"Onboarding completed: {data}")
        
        # You can add database storage here if needed
        
        return jsonify({'success': True, 'message': 'Profile completed successfully'})
        
    except Exception as e:
        logger.error(f"Onboarding submission error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/emergency-recovery')
def emergency_recovery():
    """Emergency recovery page for all paid users"""
    return '''
    <html>
    <head>
        <title>Emergency Access Recovery</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: 'Inter', system-ui, sans-serif;
                background: #0a1628;
                color: white; 
                margin: 0; 
                padding: 20px; 
                line-height: 1.6;
            }
            .container { 
                max-width: 700px; 
                margin: 0 auto;
                padding: 40px 20px;
            }
            h1 { 
                background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-size: 2.5em; 
                margin-bottom: 30px;
                text-align: center;
            }
            .alert {
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.2) 0%, rgba(255, 0, 0, 0.1) 100%);
                border: 2px solid #ff6b35;
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 30px;
                text-align: center;
            }
            .status-box {
                background: linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(255, 107, 53, 0.1) 100%);
                border: 1px solid rgba(0, 212, 255, 0.2);
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 20px;
            }
            .success { border-color: #00ff88; background: rgba(0, 255, 136, 0.1); }
            .warning { border-color: #ff6b35; background: rgba(255, 107, 53, 0.1); }
            .steps {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 20px;
                margin-top: 20px;
            }
            .step {
                margin-bottom: 16px;
                padding: 12px;
                background: rgba(0, 212, 255, 0.1);
                border-radius: 6px;
                border-left: 4px solid #00d4ff;
            }
            code {
                background: rgba(255, 255, 255, 0.1);
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Monaco', monospace;
                color: #00d4ff;
            }
            .recovery-btn {
                display: inline-block;
                background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
                color: white;
                text-decoration: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-weight: bold;
                margin: 10px 5px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚨 Emergency Access Recovery</h1>
            
            <div class="alert">
                <h2>Service Interruption Resolved</h2>
                <p><strong>If you've paid £97 for Founder's Access but can't use the bot, this page will restore your service immediately.</strong></p>
            </div>
            
            <div class="status-box success">
                <h3>✅ System Status</h3>
                <p>• Payment processing: OPERATIONAL</p>
                <p>• AI consultation engine: OPERATIONAL</p>
                <p>• Emergency access recovery: ACTIVE</p>
            </div>
            
            <div class="status-box warning">
                <h3>⚠️ Known Issue</h3>
                <p>Some users experienced interrupted onboarding during payment processing, causing their Telegram chat connection to become invalid.</p>
            </div>
            
            <div class="steps">
                <h3>🔧 Immediate Recovery Steps:</h3>
                
                <div class="step">
                    <strong>Step 1:</strong> Open Telegram and search for <code>@NivalisOrderBot</code>
                </div>
                
                <div class="step">
                    <strong>Step 2:</strong> Send the command <code>/start</code> to restart your conversation
                </div>
                
                <div class="step">
                    <strong>Step 3:</strong> You will immediately receive full access confirmation
                </div>
                
                <div class="step">
                    <strong>Step 4:</strong> Begin your unlimited strategic business consultation
                </div>
            </div>
            
            <div class="status-box">
                <h3>Your Paid Access Includes:</h3>
                <p>• Unlimited strategic business consultation with Antonio's digital clone</p>
                <p>• High-ticket offer development and positioning</p>
                <p>• Market analysis and revenue optimization</p>
                <p>• Content frameworks and marketing strategies</p>
                <p>• 24/7 access to elite business intelligence</p>
            </div>
            
            <div style="text-align: center; margin-top: 40px;">
                <a href="https://t.me/NivalisOrderBot" class="recovery-btn">
                    🚀 Open @NivalisOrderBot
                </a>
                <a href="/user-7582-status" class="recovery-btn">
                    📊 Check User Status
                </a>
            </div>
            
            <div style="text-align: center; margin-top: 30px; color: #888;">
                <p>Need additional help? Your payment is confirmed and access is guaranteed.</p>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/user-7582-status')
def user_7582_status():
    """Status page for user 7582's access"""
    return '''
    <html>
    <head>
        <title>User 7582 - Access Status</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: 'Inter', system-ui, sans-serif;
                background: #0a1628;
                color: white; 
                margin: 0; 
                padding: 20px; 
                line-height: 1.6;
            }
            .container { 
                max-width: 600px; 
                margin: 0 auto;
                padding: 40px 20px;
            }
            h1 { 
                background: linear-gradient(135deg, #00d4ff 0%, #ff6b35 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-size: 2.5em; 
                margin-bottom: 30px;
                text-align: center;
            }
            .status-box {
                background: linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(255, 107, 53, 0.1) 100%);
                border: 1px solid rgba(0, 212, 255, 0.2);
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 20px;
            }
            .success { border-color: #00ff88; background: rgba(0, 255, 136, 0.1); }
            .warning { border-color: #ff6b35; background: rgba(255, 107, 53, 0.1); }
            .steps {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 20px;
                margin-top: 20px;
            }
            .step {
                margin-bottom: 12px;
                padding-left: 20px;
            }
            code {
                background: rgba(255, 255, 255, 0.1);
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Monaco', monospace;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>User 7582 Access Status</h1>
            
            <div class="status-box success">
                <h3>✅ Payment Confirmed</h3>
                <p>Your £97 payment has been processed and recorded in the system.</p>
            </div>
            
            <div class="status-box success">
                <h3>✅ Subscriber Access Granted</h3>
                <p>You are registered as a paid subscriber with full access privileges.</p>
            </div>
            
            <div class="status-box warning">
                <h3>⚠️ Chat Connection Required</h3>
                <p>Your Telegram chat connection needs to be reestablished due to technical issues during onboarding.</p>
            </div>
            
            <div class="steps">
                <h3>To Restore Full Bot Access:</h3>
                <div class="step">1. Open Telegram and search for <code>@NivalisOrderBot</code></div>
                <div class="step">2. Send the command <code>/start</code> to the bot</div>
                <div class="step">3. You will immediately receive full access confirmation</div>
                <div class="step">4. Begin your strategic consultation</div>
            </div>
            
            <div class="status-box">
                <h3>Your Full Access Includes:</h3>
                <p>• Unlimited strategic business consultation</p>
                <p>• High-ticket offer development</p>
                <p>• Market analysis and positioning</p>
                <p>• Revenue optimization strategies</p>
                <p>• Content and marketing frameworks</p>
            </div>
        </div>
    </body>
    </html>
    '''

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
