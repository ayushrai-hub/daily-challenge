"""
Script to test the email service functionality.
"""
import sys
import os
import asyncio
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.email import EmailService
from app.core.config import settings

async def test_email_service():
    """Test the email service by sending a test email."""
    print("Testing email service...")
    print(f"Using RESEND_API_KEY: {'*' * 10}{settings.RESEND_API_KEY[-4:] if settings.RESEND_API_KEY else 'None'}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print(f"WEBHOOK_URL: {getattr(settings, 'WEBHOOK_URL', 'Not configured')}")
    
    # Get test email from environment variable or use a default
    test_email = os.getenv("TEST_EMAIL", "aayushjain1475@gmail.com")
    print(f"\nSending test emails to: {test_email}")
    
    try:
        # Test with valid email
        print("\nTesting with valid email...")
        welcome_response = await EmailService.send_welcome_email(
            to=test_email,
            user_name="Test User"
        )
        print(f"Welcome email response: {welcome_response}")
        
        # Test with common valid gmail address
        print("\nTesting with a common email pattern...")
        gmail_response = await EmailService.send_welcome_email(
            to="jane.doe123@gmail.com",
            user_name="Jane Doe"
        )
        print(f"Gmail response: {gmail_response}")
        
        # Test with test domain (should be blocked by default)
        print("\nTesting with test domain (should be blocked)...")
        test_domain_response = await EmailService.send_welcome_email(
            to="test@example.com",
            user_name="Test User"
        )
        print(f"Test domain response: {test_domain_response}")
        
        # Test with obvious test email pattern
        print("\nTesting with obvious test pattern...")
        test_pattern_response = await EmailService.send_welcome_email(
            to="test123@gmail.com",
            user_name="Test User"
        )
        print(f"Test pattern response: {test_pattern_response}")
        
        # Test with extremely long sequence (should be blocked)
        print("\nTesting with extremely long sequence...")
        long_sequence_response = await EmailService.send_welcome_email(
            to="abcdefghijklmnopqrstuvwxyz12345@gmail.com",
            user_name="Test User"
        )
        print(f"Long sequence response: {long_sequence_response}")
        
        # Test with force_send=True (should bypass validation)
        print("\nTesting with force_send=True (should bypass validation)...")
        force_send_response = await EmailService.send_welcome_email(
            to="test@example.com",
            user_name="Test User",
            force_send=True
        )
        print(f"Force send response: {force_send_response}")
        
        # Test subscription update with valid email
        print("\nTesting subscription update with valid email...")
        sub_response = await EmailService.send_subscription_update(
            to=test_email,
            user_name="Test User",
            status="active",
            tags=["python", "javascript"]
        )
        print(f"Subscription update response: {sub_response}")
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        print("\nMake sure you have set a valid RESEND_API_KEY in your .env file.")
        print("You can get an API key from https://resend.com/api-keys")
        return False
    
    return True

def main():
    load_dotenv()
    loop = asyncio.get_event_loop()
    success = loop.run_until_complete(test_email_service())
    loop.close()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
