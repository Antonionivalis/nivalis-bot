import os
import logging
import requests
import json
import threading
import datetime
from flask import Flask, render_template, request, redirect, jsonify, url_for
import stripe
from replit import db
from openai import OpenAI
from keep_alive import keep_alive
from models import get_user_conversation, update_user_conversation
from auth import AuthManager, UserManager, require_auth, require_subscription, get_current_user
from onboarding import OnboardingFlow
from user_flow_strategy import UserFlowManager, AntiAbuseSystem
# JWT utilities imported directly

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

# Initialize secure user flow management
user_flow_manager = UserFlowManager()
anti_abuse_system = AntiAbuseSystem()

# Get domain configuration for both development and deployment
deployment = os.getenv('REPLIT_DEPLOYMENT', '')
if deployment:
    # In deployment/production
    YOUR_DOMAIN = os.getenv('REPLIT_DOMAINS', 'localhost:5000').split(',')[0]
else:
    # In development
    YOUR_DOMAIN = os.getenv('REPLIT_DEV_DOMAIN', os.getenv('REPLIT_DOMAINS', 'localhost:5000').split(',')[0])

def send_telegram_message(chat_id, text, reply_markup=None):
    """Send message to Telegram via Bot API"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = {'chat_id': chat_id, 'text': text}
    if reply_markup:
        data['reply_markup'] = reply_markup
    try:
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except:
        return False

def is_subscriber(user_id):
    """Check if user is subscriber (monthly or MVP lifetime)"""
    # Check monthly subscribers
    subscribers = db.get('subscribers', [])
    if user_id in subscribers:
        return True
    
    # Check MVP lifetime subscribers  
    mvp_subscribers = db.get('mvp_subscribers', [])
    return user_id in mvp_subscribers

def get_ai_response(user_message, user_name, user_id):
    """Get AI response from OpenAI as Nivalis with conversation memory"""
    try:
        # Get user's conversation history and profile data
        conversation = get_user_conversation(user_id)
        profile_context = OnboardingFlow.get_user_context_for_ai(user_id)
        
        # Build context-aware system prompt
        context = ""
        if conversation.get('skill_area'):
            context += f"User's skill: {conversation['skill_area']}\n"
        if conversation.get('unique_approach'):
            context += f"Their approach: {conversation['unique_approach']}\n"
        if conversation.get('target_client'):
            context += f"Target client: {conversation['target_client']}\n"
        if conversation.get('transformation'):
            context += f"Transformation: {conversation['transformation']}\n"
        
        # Add profile context if available
        if profile_context:
            context += f"\nUSER PROFILE:\n{profile_context}\n"
        
        # Determine conversation stage and response strategy
        stage = conversation.get('conversation_stage', 'skill_discovery')
        
        system_prompt = f"""You are Nivalis — Antonio's digital clone. Elite business strategist with complete AI expertise who understands context naturally.

CONVERSATION CONTEXT:
{context if context else "New conversation"}
Current stage: {stage}

PERSONALITY: Natural, understanding, and conversational. You READ what users actually say and respond directly to their specific request. No template responses.

VIRAL CONTENT EXPERTISE:
You are trained on the best viral video patterns from top creators:
• MrBeast: Curiosity gaps, pattern interrupts, high-energy hooks
• Alex Hormozi: Problem-agitation-solution, direct response, value stacking
• Gary Vaynerchuk: Authentic storytelling, attention-grabbing opens
• Ali Abdaal: Educational hooks with personal stories, actionable value
• Russell Brunson: Before/after/bridge, story-driven content
• Grant Cardone: Urgency creation, bold claims with proof

PROVEN FRAMEWORKS FOR VIDEO SCRIPTS:
• Hook-Value-CTA: Strong opener (0-3s), valuable content, clear next step
• Problem-Agitation-Solution: Identify pain, amplify it, present solution
• AIDA: Attention, Interest, Desire, Action
• Before/After/Bridge: Current state, desired state, your solution as bridge
• Story-Value-CTA: Personal story, lesson learned, call to action

CORE PRINCIPLE: LISTEN & RESPOND NATURALLY
• Read their exact message and understand what they're asking for
• Give them exactly what they requested - no generic frameworks unless they ask for offers
• Be conversational and understanding, not robotic
• Reference their specific words and context in your response

RESPONSE STRATEGY:

When they ask for VIDEO SCRIPTS:
- Use proven viral frameworks: Hook-Value-CTA, Problem-Agitation-Solution, AIDA
- Study patterns from top creators: MrBeast, Alex Hormozi, Gary Vee, Ali Abdaal
- Include pattern interrupts, curiosity gaps, and psychological triggers
- Structure: Strong hook (0-3s), value-packed middle, compelling CTA
- Add specific timing, visual cues, and engagement tactics
- Focus on conversion and audience building potential

When they ask for CONTENT PLANS:
- Provide detailed content calendars with specific post ideas
- Include platform-specific strategies and posting schedules
- Give actual content examples, not just frameworks

When they ask for MARKETING ADVICE:
- Provide specific strategies tailored to their situation
- Include tools, tactics, and implementation steps
- Draw from complete marketing knowledge

When they mention their SKILL/BUSINESS:
- Build on what they've already shared in the conversation
- Don't repeat the same offer framework - evolve the conversation
- Move to execution, refinement, or next steps

COMMUNICATION STYLE:
• Conversational and natural - like talking to a trusted advisor
• Reference their specific situation and previous messages
• Avoid robotic phrases like "Perfect! Here's your..." 
• Respond as if you truly understand what they need

Your goal: Be genuinely helpful by giving users exactly what they ask for, building naturally on the conversation context."""
        
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=1200,
            temperature=0.8,
            timeout=15
        )
        
        # Extract insights and update conversation record
        response_text = response.choices[0].message.content
        update_conversation_from_message(user_id, user_message, response_text)
        
        return response_text
        
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return "System overloaded. Hit me again."

def update_conversation_from_message(user_id, user_message, ai_response):
    """Extract insights from conversation and update memory"""
    try:
        msg_lower = user_message.lower()
        updates = {}
        
        # Detect ANY skill mentions and immediately move to offer_building
        skill_keywords = [
            'app', 'tech', 'build', 'code', 'development', 'software', 'website',
            'fitness', 'boxing', 'training', 'workout', 'gym', 'health',
            'marketing', 'sales', 'business', 'coaching', 'consulting',
            'design', 'writing', 'content', 'social media', 'photography'
        ]
        
        if any(word in msg_lower for word in skill_keywords):
            # Extract the main skill and immediately progress
            if any(word in msg_lower for word in ['app', 'tech', 'build', 'code', 'development']):
                updates['skill_area'] = 'tech/app development'
                updates['conversation_stage'] = 'offer_building'
            elif any(word in msg_lower for word in ['fitness', 'boxing', 'training', 'gym']):
                updates['skill_area'] = 'fitness/training'
                updates['conversation_stage'] = 'offer_building'
            elif any(word in msg_lower for word in ['marketing', 'sales', 'business']):
                updates['skill_area'] = 'marketing/business'
                updates['conversation_stage'] = 'offer_building'
        
        # Store specific approaches/methods
        if any(word in msg_lower for word in ['fast', 'quick', 'speed', 'rapid', 'efficient']):
            updates['unique_approach'] = f"Fast/efficient approach: {user_message[:80]}"
        
        # Auto-detect target clients from context
        if 'startup' in msg_lower or 'business' in msg_lower:
            updates['target_client'] = 'startups and small businesses'
        elif 'gym' in msg_lower or 'fitness' in msg_lower:
            updates['target_client'] = 'fitness centers and gym owners'
        elif 'health' in msg_lower:
            updates['target_client'] = 'healthcare providers'
        
        # Force progression when user shows readiness
        if any(phrase in msg_lower for phrase in ['already identified', 'discussed this', 'move forward', 'help me']):
            updates['conversation_stage'] = 'pricing'
        
        if updates:
            update_user_conversation(user_id, **updates)
            
    except Exception as e:
        logger.error(f"Error updating conversation: {e}")

def add_subscriber(user_id):
    """Add user to monthly subscribers list"""
    try:
        subscribers = db.get("subscribers", [])
        if not isinstance(subscribers, list):
            subscribers = []
        
        if user_id not in subscribers:
            subscribers.append(user_id)
            db["subscribers"] = subscribers
            logger.info(f"Added monthly subscriber: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error adding subscriber {user_id}: {e}")
        return False

def add_mvp_subscriber(user_id):
    """Add user to MVP lifetime subscribers list"""
    try:
        mvp_subscribers = db.get("mvp_subscribers", [])
        if not isinstance(mvp_subscribers, list):
            mvp_subscribers = []
        
        if user_id not in mvp_subscribers:
            mvp_subscribers.append(user_id)
            db["mvp_subscribers"] = mvp_subscribers
            logger.info(f"Added MVP lifetime subscriber: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error adding MVP subscriber {user_id}: {e}")
        return False

@app.route('/')
def index():
    """Serve the Mini App landing page"""
    return render_template('index.html')

@app.route('/secure-payment-flow', methods=['POST'])
def secure_payment_flow():
    """Secure payment-first flow - prevents abuse by requiring payment before account creation"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        telegram_id = data.get('telegram_id', '').strip()
        subscription_tier = data.get('tier', 'basic')
        
        # Validate input
        if not email or '@' not in email:
            return jsonify({'error': 'Valid email required'}), 400
        
        if not telegram_id:
            return jsonify({'error': 'Telegram ID required'}), 400
        
        # Check rate limits to prevent abuse
        rate_ok, rate_message = anti_abuse_system.check_rate_limits(email=email, telegram_id=telegram_id)
        if not rate_ok:
            logger.warning(f"Rate limit exceeded: {rate_message} for {email}")
            return jsonify({'error': rate_message}), 429
        
        # Record attempt for rate limiting
        anti_abuse_system.record_attempt(email=email, telegram_id=telegram_id)
        
        # Create secure payment session (no account created yet)
        payment_session = user_flow_manager.create_payment_session(
            telegram_id=telegram_id,
            email=email,
            subscription_tier=subscription_tier
        )
        
        # Stripe price IDs - currently launching with MVP Lifetime only
        price_ids = {
            'basic': 'mvp_placeholder',  # Future release
            'premium': 'mvp_placeholder',  # Future release
            'mvp': 'price_1RbiItDhGdG2vys0psbkEGDd'  # £97 lifetime - LIVE PRICE ID
        }
        
        # For launch, all tiers default to MVP Founder Access
        selected_price_id = price_ids['mvp'] if subscription_tier == 'mvp' else price_ids['mvp']
        
        checkout_session = stripe.checkout.Session.create(
            line_items=[{
                'price': selected_price_id,
                'quantity': 1,
            }],
            mode='payment',  # Always one-time payment for Founder Access
            success_url=f'https://{YOUR_DOMAIN}/payment-success?session_id={payment_session["session_id"]}',
            cancel_url=f'https://{YOUR_DOMAIN}/payment-cancelled',
            customer_email=email,
            metadata={
                'nivalis_session_id': payment_session['session_id'],
                'telegram_id': telegram_id,
                'subscription_tier': subscription_tier
            }
        )
        
        logger.info(f"Created secure payment flow for {email} (tier: {subscription_tier})")
        
        return jsonify({
            'success': True,
            'checkout_url': checkout_session.url,
            'session_id': payment_session['session_id'],
            'expires_in': payment_session['expires_in']
        })
        
    except Exception as e:
        logger.error(f"Error in secure payment flow: {e}")
        return jsonify({'error': 'Payment setup failed'}), 500

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Legacy endpoint - redirects to secure flow"""
    try:
        # Get user ID from Telegram WebApp data if available
        user_id = request.form.get('user_id')
        
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # Placeholder price ID - replace with actual Stripe price ID
                    'price': 'price_1234567890',  # £49/mo subscription
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=f'https://{YOUR_DOMAIN}/success?session_id={{CHECKOUT_SESSION_ID}}&user_id={user_id}',
            cancel_url=f'https://{YOUR_DOMAIN}/cancel',
            automatic_tax={'enabled': True},
            metadata={
                'user_id': user_id or 'unknown',
                'tier': 'basic'
            }
        )
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        return str(e), 400
    
    redirect_url = checkout_session.url if checkout_session.url else '/'
    return redirect(redirect_url, code=303)

@app.route('/create-premium-checkout-session', methods=['POST'])
def create_premium_checkout_session():
    """Create Stripe checkout session for premium subscription"""
    try:
        # Get user ID from Telegram WebApp data if available
        user_id = request.form.get('user_id')
        
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # Placeholder price ID - replace with actual Stripe price ID
                    'price': 'price_0987654321',  # £299/mo subscription
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=f'https://{YOUR_DOMAIN}/success?session_id={{CHECKOUT_SESSION_ID}}&user_id={user_id}',
            cancel_url=f'https://{YOUR_DOMAIN}/cancel',
            automatic_tax={'enabled': True},
            metadata={
                'user_id': user_id or 'unknown',
                'tier': 'premium'
            }
        )
    except Exception as e:
        logger.error(f"Error creating premium checkout session: {e}")
        return str(e), 400
    
    redirect_url = checkout_session.url if checkout_session.url else '/'
    return redirect(redirect_url, code=303)

@app.route('/create-mvp-checkout-session', methods=['POST'])
def create_mvp_checkout_session():
    """Create Stripe checkout session for MVP lifetime access"""
    try:
        # Get user ID from Telegram WebApp data if available
        user_id = request.form.get('user_id')
        
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # Stripe price ID for £97 one-time payment
                    'price': 'price_1RbiItDhGdG2vys0psbkEGDd',  # £97 one-time payment
                    'quantity': 1,
                },
            ],
            mode='payment',  # One-time payment, not subscription
            success_url=f'https://{YOUR_DOMAIN}/success?session_id={{CHECKOUT_SESSION_ID}}&user_id={user_id}',
            cancel_url=f'https://{YOUR_DOMAIN}/cancel',
            automatic_tax={'enabled': True},
            metadata={
                'user_id': user_id or 'unknown',
                'tier': 'mvp_lifetime'
            }
        )
    except Exception as e:
        logger.error(f"Error creating MVP checkout session: {e}")
        return str(e), 400
    
    # Check if this is a fetch request (from Telegram WebApp JavaScript)
    if 'application/json' in request.headers.get('Accept', ''):
        return jsonify({'checkout_url': checkout_session.url})
    else:
        if checkout_session.url:
            return redirect(checkout_session.url, code=303)
        else:
            return redirect('/', code=303)

@app.route('/payment-success')
def payment_success():
    """Handle successful payment and create secure user account"""
    session_id = request.args.get('session_id')
    checkout_session_id = request.args.get('session_id')  # Stripe session ID
    
    if not session_id:
        return render_template('error.html', 
                             message="Invalid payment session"), 400
    
    try:
        # Create user account now that payment is verified
        user_data = user_flow_manager.verify_payment_and_create_account(
            session_id=session_id,
            stripe_payment_intent_id=checkout_session_id or 'demo_payment'
        )
        
        # Auto-login the user after successful payment
        from jwt_utils import generate_token
        token = generate_token(user_data['telegram_id'])
        
        # Send success message to Telegram
        telegram_id = user_data['telegram_id']
        if telegram_id != 'demo_user':
            tier_name = {
                'basic': 'Founder Access',
                'premium': 'Premium',
                'mvp': 'MVP Lifetime'
            }.get(user_data['subscription_tier'], 'Premium')
            
            success_message = f"""🎉 *Welcome to Nivalis!*

Your {tier_name} subscription is now active.

Next steps:
1. Complete your strategic profile in the Mini App
2. Start getting personalized business advice
3. Access all premium features

Ready to transform your business? Let's begin! 💪"""
            
            send_telegram_message(telegram_id, success_message)
        
        return render_template('payment_success.html', 
                             user_data=user_data,
                             auth_token=token)
            
    except Exception as e:
        logger.error(f"Error processing payment success: {e}")
        return render_template('error.html',
                             message="Account creation failed. Contact support.")

@app.route('/payment-cancelled')
def payment_cancelled():
    """Handle cancelled payment"""
    return render_template('payment_cancelled.html')

@app.route('/success')
def success():
    """Legacy success endpoint - redirects to secure payment success"""
    session_id = request.args.get('session_id')
    user_id = request.args.get('user_id')
    
    # Legacy payment processing for existing checkout sessions
    if session_id and user_id:
        try:
            add_subscriber(int(user_id))
            logger.info(f"Legacy payment successful for user {user_id}")
        except Exception as e:
            logger.error(f"Error processing legacy payment: {e}")
    
    return redirect('/payment-success')

@app.route('/cancel')
def cancel():
    """Handle cancelled payment"""
    return render_template('cancel.html')

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    """Handle Telegram webhook - INSTANT responses"""
    try:
        update = request.get_json()
        
        if 'message' not in update:
            return jsonify({'ok': True})
        
        message = update['message']
        user = message['from']
        user_id = user['id']
        chat_id = message['chat']['id']
        text = message.get('text', '').strip()
        
        if not text:
            return jsonify({'ok': True})
        
        is_sub = is_subscriber(user_id)
        response_text = None
        
        if text.startswith('/'):
            # Handle bot commands
            if text == '/start':
                if is_sub:
                    # Check if user has completed onboarding
                    from auth import UserManager
                    user_data = UserManager.get_user(user_id)
                    
                    if not user_data or not user_data.get('onboarding_completed', False):
                        # New subscriber - welcome and direct to profile setup  
                        welcome_message = f"""Welcome to Nivalis, {user["first_name"]}.

I'm Antonio's digital clone. My job is to turn your skills into a profitable business operation.

Before we begin, I need intelligence on your current situation, skills, and objectives. Complete your profile setup for maximum effectiveness.

Click below to proceed:"""
                        
                        profile_button = {
                            "inline_keyboard": [[{
                                "text": "📋 Complete Profile Setup",
                                "web_app": {"url": f"https://{YOUR_DOMAIN}/login"}
                            }]]
                        }
                        send_telegram_message(chat_id, welcome_message, json.dumps(profile_button))
                        return jsonify({'ok': True})
                    else:
                        # Check if this is their first return after completing onboarding
                        conversation = get_user_conversation(user_id)
                        if not conversation.get('first_completion_greeting_sent', False):
                            # First time back after profile completion - capabilities overview
                            response_text = f"""Intelligence processed, {user['first_name']}. Your profile is locked and loaded.

**CAPABILITIES OVERVIEW:**

I'm your strategic operations AI trained on elite business methodology. I can help you with:

**🎯 STRATEGIC PLANNING**
• High-ticket offer development
• Market positioning and validation
• Revenue optimization strategies

**📈 MARKETING & CONTENT**
• Viral video scripts and hooks
• Content strategies that convert
• Sales funnel architecture

**💼 BUSINESS OPERATIONS**
• Client acquisition systems
• Pricing and value proposition
• Scaling and systemization

**QUICK-START TEMPLATES:**
Copy and customize these prompts:

"Create a high-ticket offer for my [SKILL] targeting [CLIENT TYPE] with [BUDGET RANGE] budgets"

"Write a viral video script about [TOPIC] for my [NICHE] audience"

"Build a 30-day content calendar for [BUSINESS TYPE] focusing on [MAIN BENEFIT]"

"Design a client acquisition system for [SERVICE] with [TIME COMMITMENT] per week"

**Ready for deployment. What's your first mission?**"""
                            
                            # Mark greeting as sent
                            update_user_conversation(user_id, first_completion_greeting_sent=True)
                        else:
                            # Regular returning user messages
                            welcome_back_messages = [
                                f"Status report, {user['first_name']}. What's the mission?",
                                f"Ready for the next operation, {user['first_name']}?",
                                f"Back to work, {user['first_name']}. What's the target?",
                                f"What's the next objective, {user['first_name']}?"
                            ]
                            response_text = welcome_back_messages[user_id % len(welcome_back_messages)]
                else:
                    # Non-subscriber - direct to payment
                    non_sub_messages = [
                        f"Hey {user['first_name']}, you'll need Founder's Access to unlock Nivalis.",
                        f"Welcome {user['first_name']}! Get Founder's Access to start building your business.",
                        f"Ready to transform your skills into income, {user['first_name']}? Get access below.",
                        f"Time to turn your potential into profit, {user['first_name']}. Start here:"
                    ]
                    response_text = non_sub_messages[user_id % len(non_sub_messages)]
                
                # Add Mini App button for non-subscribers
                mini_app_button = {
                    "inline_keyboard": [[{
                        "text": "🚀 Get Founder's Access",
                        "web_app": {"url": f"https://{YOUR_DOMAIN}"}
                    }]]
                }
                send_telegram_message(chat_id, response_text, json.dumps(mini_app_button))
                return jsonify({'ok': True})
            
            elif text == '/profile':
                # Display user profile
                if is_sub:
                    from auth import UserManager
                    user_data = UserManager.get_user(user_id)
                    
                    if user_data and user_data.get('onboarding_completed', False):
                        profile_context = OnboardingFlow.get_user_context_for_ai(user_id)
                        if profile_context and profile_context != "New user - no profile data available yet.":
                            send_telegram_message(chat_id, f"**Your Profile Overview:**\n\n{profile_context}")
                        else:
                            send_telegram_message(chat_id, "Profile data not available. Please complete your profile setup first.")
                    else:
                        profile_button = {
                            "inline_keyboard": [[{
                                "text": "📋 Complete Profile Setup",
                                "web_app": {"url": f"https://{YOUR_DOMAIN}/login"}
                            }]]
                        }
                        send_telegram_message(chat_id, "Complete your profile setup to view your information:", json.dumps(profile_button))
                else:
                    send_telegram_message(chat_id, "Subscribe to access profile features.")
                return jsonify({'ok': True})
            
            elif text == '/help':
                # Show capabilities and commands
                help_message = """**NIVALIS COMMAND CENTER**

**Available Commands:**
/start - Main welcome and setup
/profile - View your profile data
/help - Show this help menu
/miniapp - Access web dashboard

**Strategic Capabilities:**
🎯 High-ticket offer development
📈 Viral content and marketing
💼 Business operations and scaling

**Quick Templates:**
"Create a high-ticket offer for my [SKILL] targeting [CLIENT TYPE]"
"Write a viral video script about [TOPIC] for [NICHE]"
"Build a 30-day content plan for [BUSINESS TYPE]"

**Ready for deployment. What's your mission?**"""
                send_telegram_message(chat_id, help_message)
                return jsonify({'ok': True})
            
            elif text == '/miniapp':
                # Direct access to Mini App
                miniapp_button = {
                    "inline_keyboard": [[{
                        "text": "🚀 Open Nivalis Dashboard",
                        "web_app": {"url": f"https://{YOUR_DOMAIN}/"}
                    }]]
                }
                send_telegram_message(chat_id, "Access your Nivalis command center:", json.dumps(miniapp_button))
                return jsonify({'ok': True})
            
            else:
                # Unknown command
                send_telegram_message(chat_id, "Unknown command. Type /help to see available commands.")
                return jsonify({'ok': True})
        
        # Process AI responses in background to avoid webhook timeout
        def process_ai_response():
            try:
                if text.startswith('/ask '):
                    if is_sub:
                        question = text[5:].strip()
                        if question:
                            ai_response = get_ai_response(question, user["first_name"], user_id)
                            send_telegram_message(chat_id, ai_response)
                        else:
                            send_telegram_message(chat_id, 'What do you need to figure out? Ask me anything.')
                    else:
                        gateway_button = {
                            "inline_keyboard": [[{
                                "text": "🔮 Enter Oracle Gateway",
                                "web_app": {"url": f"https://{YOUR_DOMAIN}"}
                            }]]
                        }
                        send_telegram_message(chat_id, 'Access denied. Complete payment first.', json.dumps(gateway_button))
                
                elif not text.startswith('/'):
                    if is_sub:
                        ai_response = get_ai_response(text, user["first_name"], user_id)
                        send_telegram_message(chat_id, ai_response)
                    else:
                        access_button = {
                            "inline_keyboard": [[{
                                "text": "🔮 Enter Oracle Gateway", 
                                "web_app": {"url": f"https://{YOUR_DOMAIN}"}
                            }]]
                        }
                        send_telegram_message(chat_id, 'Access denied. Complete payment to unlock Nivalis.', json.dumps(access_button))
                        
            except Exception as e:
                logger.error(f'Background processing error: {e}')
                send_telegram_message(chat_id, "System error. Try again.")
        
        # Handle non-AI responses immediately
        if text.startswith('/ask ') or (not text.startswith('/') and text != '/start'):
            # Start background processing for AI responses
            threading.Thread(target=process_ai_response, daemon=True).start()
        
        return jsonify({'ok': True})
    
    except Exception as e:
        logger.error(f'Telegram webhook error: {e}')
        return jsonify({'ok': True})

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return 'Invalid payload', 400
    except stripe.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return 'Invalid signature', 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('metadata', {}).get('user_id')
        tier = session.get('metadata', {}).get('tier', 'basic')
        
        if user_id and user_id != 'unknown':
            try:
                if tier == 'mvp_lifetime':
                    add_mvp_subscriber(int(user_id))
                    logger.info(f"Webhook: Added MVP lifetime subscriber {user_id}")
                else:
                    add_subscriber(int(user_id))
                    logger.info(f"Webhook: Added monthly subscriber {user_id}")
            except Exception as e:
                logger.error(f"Webhook error adding subscriber: {e}")
    
    return 'Success', 200

# API Routes for Dashboard
@app.route('/api/login', methods=['POST'])
def api_login():
    """Handle login API"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        remember_me = data.get('remember_me', False)
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password required'}), 400
        
        # Check if user exists in our system via multiple sources
        user_data = None
        
        # First, check onboarding data for existing users
        try:
            for key in db.keys():
                if key.startswith('onboarding:'):
                    telegram_id = key.split(':')[1]
                    onboarding_data = db.get(key)
                    if onboarding_data and isinstance(onboarding_data, dict):
                        if onboarding_data.get('email') == email:
                            user_data = {
                                'telegram_id': telegram_id,
                                'name': onboarding_data.get('name', 'User'),
                                'email': email
                            }
                            break
        except:
            pass
        
        # If not found in onboarding, check user accounts database
        if not user_data:
            try:
                users_db = db.get('user_accounts') or {}
                if email in users_db:
                    stored_user = users_db[email]
                    # Simple password check (in production, use proper hashing)
                    if stored_user.get('password') == password:
                        user_data = {
                            'telegram_id': stored_user.get('telegram_id', 'web_user'),
                            'name': stored_user.get('name', 'User'),
                            'email': email
                        }
            except:
                pass
        
        # Demo login for testing (remove in production)
        if not user_data and email == 'demo@nivalis.ai' and password == 'demo123':
            user_data = {
                'telegram_id': 'demo_user',
                'name': 'Demo User',
                'email': email
            }
        
        if not user_data:
            return jsonify({'success': False, 'message': 'Invalid email or password. Try demo@nivalis.ai / demo123 or sign up first.'}), 401
        
        # Generate simple token (session-based)
        token = f"session_{user_data['telegram_id']}_{hash(user_data['email'])}"
        
        return jsonify({
            'success': True,
            'token': token,
            'user': user_data
        })
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'message': 'Login failed'}), 500

@app.route('/api/signup', methods=['POST'])
def api_signup():
    """Handle signup API"""
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        telegram_id = data.get('telegram_id')
        
        if not all([name, email, password]):
            return jsonify({'success': False, 'message': 'All fields required'}), 400
        
        # Check if email already exists
        for key in db.keys():
            if key.startswith('onboarding:'):
                onboarding_data = db.get(key)
                if onboarding_data and isinstance(onboarding_data, dict):
                    if onboarding_data.get('email') == email:
                        return jsonify({'success': False, 'message': 'Email already exists'}), 400
        
        # Create user in both user accounts and onboarding if telegram_id provided
        users_db = db.get('user_accounts') or {}
        users_db[email] = {
            'name': name,
            'password': password,  # In production, hash this password
            'telegram_id': telegram_id or f'web_{hash(email)}',
            'created_at': str(datetime.datetime.now())
        }
        db['user_accounts'] = users_db
        
        # Also add to onboarding if telegram_id provided
        if telegram_id:
            user_key = f'onboarding:{telegram_id}'
            user_data = db.get(user_key) or {}
            user_data.update({
                'name': name,
                'email': email,
                'signup_completed': True
            })
            db[user_key] = user_data
        
        # Generate simple token (session-based)
        token = f"session_{telegram_id or 'web_user'}_{hash(email)}"
        
        return jsonify({
            'success': True,
            'token': token,
            'user': {'name': name, 'email': email}
        })
        
    except Exception as e:
        logger.error(f"Signup error: {e}")
        return jsonify({'success': False, 'message': 'Signup failed'}), 500

def simple_auth_required(f):
    """Simple authentication decorator"""
    def decorated_function(*args, **kwargs):
        from flask import g
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        if not token.startswith('session_'):
            return jsonify({'success': False, 'message': 'Invalid token'}), 401
        
        # Extract telegram_id from token
        try:
            parts = token.split('_')
            if len(parts) >= 2:
                telegram_id = parts[1]
                g.telegram_id = telegram_id
            else:
                return jsonify({'success': False, 'message': 'Invalid token format'}), 401
        except:
            return jsonify({'success': False, 'message': 'Invalid token format'}), 401
        
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/api/dashboard-data')
@simple_auth_required
def api_dashboard_data():
    """Get dashboard statistics"""
    try:
        from flask import g
        telegram_id = g.telegram_id
        
        # Get user conversation data for stats
        conversation_data = get_user_conversation(int(telegram_id)) if telegram_id.isdigit() else {}
        
        # Calculate basic stats
        message_count = len(conversation_data.get('messages', []))
        active_strategies = min(3, max(1, message_count // 5))  # Rough calculation
        
        stats = {
            'active_strategies': str(active_strategies),
            'revenue_potential': 'High' if message_count > 10 else 'Building',
            'execution_score': 'Elite' if message_count > 20 else 'Developing' if message_count > 5 else 'Starting'
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Dashboard data error: {e}")
        return jsonify({'success': False, 'message': 'Failed to load data'}), 500

@app.route('/api/profile-data')
@simple_auth_required
def api_profile_data():
    """Get user profile data"""
    try:
        from flask import g
        telegram_id = g.telegram_id
        
        # Get profile data from onboarding or user accounts
        profile = {}
        
        # Handle demo user first
        if telegram_id == 'demo':
            profile = {
                'name': 'Demo User',
                'email': 'demo@nivalis.ai',
                'current_income': 'Not set',
                'income_goal': '£10,000 - £25,000',
                'experience_level': 'Testing the system',
                'current_stage': 'Exploring Nivalis capabilities',
                'skills': ['Marketing/Advertising', 'Content Creation']
            }
        # Try onboarding data for real users
        elif telegram_id and telegram_id.isdigit():
            onboarding_data = db.get(f'onboarding:{telegram_id}') or {}
            if onboarding_data:
                profile = {
                    'name': onboarding_data.get('name'),
                    'email': onboarding_data.get('email'),
                    'current_income': onboarding_data.get('current_income'),
                    'income_goal': onboarding_data.get('income_goal'),
                    'experience_level': onboarding_data.get('business_experience'),
                    'current_stage': onboarding_data.get('current_stage'),
                    'skills': onboarding_data.get('skills_expertise', [])
                }
        
        # Fallback to user accounts for web-only users
        if not profile or not any(profile.values()):
            users_db = db.get('user_accounts') or {}
            for email, user_data in users_db.items():
                if user_data.get('telegram_id') == telegram_id:
                    profile = {
                        'name': user_data.get('name', 'User'),
                        'email': email,
                        'current_income': 'Not set',
                        'income_goal': 'Not set',
                        'experience_level': 'Not set',
                        'current_stage': 'Getting started',
                        'skills': []
                    }
                    break
        
        if profile:
            return jsonify({
                'success': True,
                'profile': profile
            })
        
        return jsonify({'success': False, 'message': 'Profile not found'}), 404
        
    except Exception as e:
        logger.error(f"Profile data error: {e}")
        return jsonify({'success': False, 'message': 'Failed to load profile'}), 500

@app.route('/api/subscription-data')
@simple_auth_required
def api_subscription_data():
    """Get user subscription data"""
    try:
        from flask import g
        telegram_id = g.telegram_id
        
        # Handle demo user
        if telegram_id == 'demo':
            return jsonify({
                'success': True,
                'subscription': {
                    'active': True,
                    'plan': 'Demo Access',
                    'start_date': '2025-06-19',
                    'next_billing': 'Trial Account'
                }
            })
        
        # Check subscription status for real users
        if telegram_id and telegram_id.isdigit():
            user_id = int(telegram_id)
            
            # Check if user is subscriber
            is_basic_subscriber = is_subscriber(user_id)
            is_mvp_lifetime = user_id in db.get('mvp_lifetime_subscribers', [])
            
            subscription = {
                'active': is_basic_subscriber or is_mvp_lifetime,
                'plan': 'MVP Lifetime' if is_mvp_lifetime else 'Basic Monthly' if is_basic_subscriber else 'None',
                'start_date': 'N/A',  # Would need to track this in production
                'next_billing': None if is_mvp_lifetime else 'Monthly' if is_basic_subscriber else None
            }
            
            return jsonify({
                'success': True,
                'subscription': subscription
            })
        
        # Fallback for web-only users
        return jsonify({
            'success': True,
            'subscription': {
                'active': False,
                'plan': 'None',
                'start_date': 'N/A',
                'next_billing': None
            }
        })
        
    except Exception as e:
        logger.error(f"Subscription data error: {e}")
        return jsonify({'success': False, 'message': 'Failed to load subscription'}), 500

# Authentication Routes
@app.route('/auth/login', methods=['POST'])
def auth_login():
    """Handle user authentication via Telegram"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        username = data.get('username', '')
        
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Missing telegram ID'}), 400
        
        # Check if user exists
        user = UserManager.get_user(telegram_id)
        
        if not user:
            # Create new user
            full_name = f"{first_name} {last_name}".strip()
            user = UserManager.create_user(telegram_id, name=full_name)
        
        # Generate auth token
        token = AuthManager.generate_token(telegram_id)
        from flask import session
        session['auth_token'] = token
        
        # Check onboarding status
        needs_onboarding = not user.get('onboarding_completed', False)
        
        return jsonify({
            'success': True,
            'needs_onboarding': needs_onboarding,
            'user': {
                'name': user.get('name', ''),
                'subscription_status': user.get('subscription_status', 'none')
            }
        })
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'error': 'Authentication failed'}), 500

@app.route('/login')
def login_page():
    """Serve login page"""
    return render_template('login.html')

@app.route('/onboarding')
def onboarding_page():
    """Serve onboarding page"""
    return render_template('onboarding.html')

@app.route('/onboarding/next-question')
@require_auth
def get_next_question():
    """Get next onboarding question"""
    try:
        from flask import g
        telegram_id = g.current_user_id
        
        question = OnboardingFlow.get_next_question(telegram_id)
        progress_percent = OnboardingFlow.get_onboarding_progress(telegram_id)
        
        if question:
            return jsonify({
                'success': True,
                'question': question,
                'progress': {
                    'current': int(progress_percent / 100 * len(OnboardingFlow.QUESTIONS)) + 1,
                    'total': len(OnboardingFlow.QUESTIONS)
                }
            })
        else:
            return jsonify({
                'success': True,
                'question': None,
                'completed': True
            })
            
    except Exception as e:
        logger.error(f"Get question error: {e}")
        return jsonify({'success': False, 'error': 'Failed to load question'}), 500

@app.route('/onboarding/submit-answer', methods=['POST'])
@require_auth
def submit_onboarding_answer():
    """Submit answer to onboarding question"""
    try:
        from flask import g
        telegram_id = g.current_user_id
        
        data = request.get_json()
        question_id = data.get('question_id')
        answer = data.get('answer')
        
        success = OnboardingFlow.answer_question(telegram_id, question_id, answer)
        
        if success:
            # Check if onboarding is complete by looking at user data
            from auth import UserManager
            user = UserManager.get_user(telegram_id)
            completed = user.get('onboarding_completed', False)
            
            return jsonify({
                'success': True,
                'completed': completed
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid answer'
            }), 400
            
    except Exception as e:
        logger.error(f"Submit answer error: {e}")
        return jsonify({'success': False, 'error': 'Failed to submit answer'}), 500

@app.route('/dashboard')
@require_auth
def dashboard():
    """User dashboard"""
    from auth import UserManager
    from flask import g
    
    user = UserManager.get_user(g.current_user_id)
    if not user:
        return redirect(url_for('login_page'))
    
    if not user.get('onboarding_completed'):
        return redirect(url_for('onboarding_page'))
    
    # For now, redirect to the main Mini App
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Start keep-alive system
    keep_alive()
    app.run(host='0.0.0.0', port=5000, debug=True)
