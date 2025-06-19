"""
User Onboarding System for Nivalis
Manages multi-step onboarding flow and data collection
"""
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class OnboardingFlow:
    """Manages the onboarding questionnaire flow"""
    
    QUESTIONS = [
        {
            'id': 'name',
            'question': 'What\'s your full name?',
            'type': 'text',
            'required': True,
            'validation': lambda x: len(x.strip()) >= 2
        },
        {
            'id': 'email',
            'question': 'What\'s your email address?',
            'type': 'email',
            'required': True,
            'validation': lambda x: '@' in x and '.' in x.split('@')[1]
        },
        {
            'id': 'telegram_username',
            'question': 'What\'s your Telegram username? (without @)',
            'type': 'text',
            'required': False,
            'validation': lambda x: True
        },
        {
            'id': 'current_income',
            'question': 'What\'s your current monthly income range?',
            'type': 'choice',
            'required': True,
            'options': [
                '£0 - £1,000',
                '£1,000 - £5,000',
                '£5,000 - £10,000',
                '£10,000 - £25,000',
                '£25,000 - £50,000',
                '£50,000+'
            ]
        },
        {
            'id': 'income_goal',
            'question': 'What\'s your monthly income goal?',
            'type': 'choice',
            'required': True,
            'options': [
                '£5,000 - £10,000',
                '£10,000 - £25,000',
                '£25,000 - £50,000',
                '£50,000 - £100,000',
                '£100,000+'
            ]
        },
        {
            'id': 'business_experience',
            'question': 'What\'s your business experience level?',
            'type': 'choice',
            'required': True,
            'options': [
                'Complete beginner',
                'Some experience, no revenue yet',
                'Making some money (under £1k/month)',
                'Consistent revenue (£1k-£10k/month)',
                'Established business (£10k+/month)'
            ]
        },
        {
            'id': 'available_capital',
            'question': 'How much capital do you have available to invest?',
            'type': 'choice',
            'required': True,
            'options': [
                '£0 - £500',
                '£500 - £2,000',
                '£2,000 - £10,000',
                '£10,000 - £50,000',
                '£50,000+'
            ]
        },
        {
            'id': 'current_stage',
            'question': 'What stage are you at right now?',
            'type': 'choice',
            'required': True,
            'options': [
                'Looking for business ideas',
                'Have an idea, need validation',
                'Validating/testing my concept',
                'Building my first product/service',
                'Have product, need customers',
                'Scaling existing business'
            ]
        },
        {
            'id': 'time_commitment',
            'question': 'How many hours per week can you dedicate to your business?',
            'type': 'choice',
            'required': True,
            'options': [
                '5-10 hours (part-time)',
                '10-20 hours (serious side hustle)',
                '20-40 hours (almost full-time)',
                '40+ hours (full-time commitment)'
            ]
        },
        {
            'id': 'biggest_challenge',
            'question': 'What\'s your biggest challenge right now?',
            'type': 'choice',
            'required': True,
            'options': [
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
            'id': 'skills_expertise',
            'question': 'What skills or expertise do you have? (Select all that apply)',
            'type': 'multiple_choice',
            'required': True,
            'options': [
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
            'id': 'urgency_level',
            'question': 'How urgent is your need to increase income?',
            'type': 'choice',
            'required': True,
            'options': [
                'Not urgent, just exploring',
                'Would be nice within 6-12 months',
                'Important within 3-6 months',
                'Critical within 1-3 months',
                'Extremely urgent (financial pressure)'
            ]
        }
    ]
    
    @staticmethod
    def get_next_question(telegram_id):
        """Get the next unanswered question for user"""
        from auth import UserManager
        user = UserManager.get_user(telegram_id)
        if not user:
            return None
        
        answered = user.get('onboarding_progress', {})
        
        for question in OnboardingFlow.QUESTIONS:
            if question['id'] not in answered:
                # Return a clean copy without validation function for JSON serialization
                clean_question = {k: v for k, v in question.items() if k != 'validation'}
                return clean_question
        
        return None  # All questions answered
    
    @staticmethod
    def answer_question(telegram_id, question_id, answer):
        """Store answer to onboarding question"""
        from auth import UserManager
        user = UserManager.get_user(telegram_id)
        if not user:
            return False
        
        # Get current progress
        progress = user.get('onboarding_progress', {})
        
        # Find the question
        question = next((q for q in OnboardingFlow.QUESTIONS if q['id'] == question_id), None)
        if not question:
            return False
        
        # Validate answer
        if question['required'] and not answer:
            return False
        
        if answer and 'validation' in question:
            if not question['validation'](answer):
                return False
        
        # Store answer
        progress[question_id] = {
            'answer': answer,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Update user
        from auth import UserManager
        UserManager.update_user(telegram_id, {'onboarding_progress': progress})
        
        # Check if onboarding is complete
        if len(progress) == len(OnboardingFlow.QUESTIONS):
            OnboardingFlow.complete_onboarding(telegram_id)
        
        return True
    
    @staticmethod
    def complete_onboarding(telegram_id):
        """Mark onboarding as complete and generate profile"""
        from auth import UserManager
        user = UserManager.get_user(telegram_id)
        if not user:
            return False
        
        progress = user.get('onboarding_progress', {})
        
        # Extract answers into structured data
        onboarding_data = {}
        for question in OnboardingFlow.QUESTIONS:
            if question['id'] in progress:
                onboarding_data[question['id']] = progress[question['id']]['answer']
        
        # Generate user profile summary
        profile_summary = OnboardingFlow.generate_profile_summary(onboarding_data)
        
        # Update user record
        updates = {
            'onboarding_completed': True,
            'onboarding_data': onboarding_data,
            'profile_summary': profile_summary,
            'name': onboarding_data.get('name', ''),
            'email': onboarding_data.get('email', '')
        }
        
        UserManager.update_user(telegram_id, updates)
        logger.info(f"Completed onboarding for user {telegram_id}")
        
        # Send capabilities message immediately
        OnboardingFlow.send_capabilities_message(telegram_id)
        
        return True
    
    @staticmethod
    def send_capabilities_message(telegram_id):
        """Send capabilities overview message after onboarding completion"""
        import os
        import requests
        from auth import UserManager
        
        user = UserManager.get_user(telegram_id)
        if not user:
            return
        
        user_name = user.get('profile_summary', {}).get('basic_info', {}).get('name', 'Agent')
        first_name = user_name.split()[0] if user_name != 'Agent' else 'Agent'
        
        capabilities_message = f"""Intelligence processed, {first_name}. Your profile is locked and loaded.

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
        
        # Send message via Telegram API
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if bot_token:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': telegram_id,
                'text': capabilities_message,
                'parse_mode': 'Markdown'
            }
            try:
                requests.post(url, json=payload)
                
                # Mark greeting as sent in conversation
                from models import update_user_conversation
                update_user_conversation(telegram_id, first_completion_greeting_sent=True)
            except Exception as e:
                logger.error(f"Error sending capabilities message: {e}")
    
    @staticmethod
    def generate_profile_summary(data):
        """Generate AI-friendly profile summary"""
        summary = {
            'basic_info': {
                'name': data.get('name', ''),
                'email': data.get('email', ''),
                'telegram_username': data.get('telegram_username', '')
            },
            'financial_profile': {
                'current_income': data.get('current_income', ''),
                'income_goal': data.get('income_goal', ''),
                'available_capital': data.get('available_capital', '')
            },
            'business_profile': {
                'experience_level': data.get('business_experience', ''),
                'current_stage': data.get('current_stage', ''),
                'time_commitment': data.get('time_commitment', ''),
                'biggest_challenge': data.get('biggest_challenge', ''),
                'urgency_level': data.get('urgency_level', '')
            },
            'skills_and_expertise': data.get('skills_expertise', [])
        }
        
        return summary
    
    @staticmethod
    def get_onboarding_progress(telegram_id):
        """Get onboarding progress percentage"""
        from auth import UserManager
        user = UserManager.get_user(telegram_id)
        if not user:
            return 0
        
        progress = user.get('onboarding_progress', {})
        total_questions = len(OnboardingFlow.QUESTIONS)
        answered_questions = len(progress)
        
        return int((answered_questions / total_questions) * 100)
    
    @staticmethod
    def get_user_context_for_ai(telegram_id):
        """Get formatted user context for AI responses"""
        from auth import UserManager
        user = UserManager.get_user(telegram_id)
        if not user or not user.get('onboarding_completed'):
            return "New user - no profile data available yet."
        
        profile = user.get('profile_summary', {})
        
        context = f"""
USER PROFILE CONTEXT:
- Name: {profile.get('basic_info', {}).get('name', 'Unknown')}
- Current Income: {profile.get('financial_profile', {}).get('current_income', 'Unknown')}
- Income Goal: {profile.get('financial_profile', {}).get('income_goal', 'Unknown')}
- Experience Level: {profile.get('business_profile', {}).get('experience_level', 'Unknown')}
- Current Stage: {profile.get('business_profile', {}).get('current_stage', 'Unknown')}
- Available Capital: {profile.get('financial_profile', {}).get('available_capital', 'Unknown')}
- Time Commitment: {profile.get('business_profile', {}).get('time_commitment', 'Unknown')}
- Biggest Challenge: {profile.get('business_profile', {}).get('biggest_challenge', 'Unknown')}
- Urgency Level: {profile.get('business_profile', {}).get('urgency_level', 'Unknown')}
- Skills: {', '.join(profile.get('skills_and_expertise', []))}

This user's responses should be tailored to their specific situation, experience level, and goals.
"""
        return context.strip()