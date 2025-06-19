# Nivalis Bot - Production Deployment

## Quick Deploy to Render.com

1. Upload all these files to a new GitHub repository
2. Connect the repository to Render
3. Set environment variables:
   - DATABASE_URL
   - TELEGRAM_BOT_TOKEN  
   - STRIPE_SECRET_KEY
   - OPENAI_API_KEY
   - SESSION_SECRET

4. Deploy with:
   - Build: `pip install -r pyproject.toml`
   - Start: `gunicorn --bind 0.0.0.0:$PORT web:app`

## Files Included
- web.py - Main Flask application
- All authentication and onboarding modules
- Templates and static files
- Production configuration files
