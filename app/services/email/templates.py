"""
Email templates for the application.

These templates are used by the EmailService to send consistent, well-formatted emails.
"""

__all__ = [
    "get_welcome_email_template",
    "get_subscription_update_template",
    "get_verification_email_template",
    "get_daily_challenge_email_template",
    "get_challenge_solution_email_template",
    "get_password_reset_template",
]

def get_welcome_email_template(user_name: str) -> str:
    """
    Generate the welcome email HTML content.
    
    Args:
        user_name: The name of the user
        
    Returns:
        str: HTML content for the welcome email
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .footer {{ text-align: center; padding: 20px; font-size: 0.9em; color: #777; }}
            .button {{
                display: inline-block;
                padding: 10px 20px;
                margin: 20px 0;
                background-color: #4CAF50;
                color: white;
                text-decoration: none;
                border-radius: 4px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to Daily Challenge!</h1>
            </div>
            <div class="content">
                <p>Hello {user_name},</p>
                <p>Thank you for registering with Daily Challenge. We're excited to have you on board!</p>
                <p>Start exploring challenges and improve your skills with our daily coding problems.</p>
                <p>If you have any questions, feel free to reach out to our support team.</p>
                <p>Happy Coding!<br>The Daily Challenge Team</p>
            </div>
            <div class="footer">
                <p>© 2025 Daily Challenge. All rights reserved.</p>
                <p>If you didn't create an account, please ignore this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

def get_subscription_update_template(user_name: str, status: str, tags: list[str]) -> str:
    """
    Generate the subscription update email HTML content.
    
    Args:
        user_name: The name of the user
        status: The new subscription status
        tags: List of subscribed tags
        
    Returns:
        str: HTML content for the subscription update email
    """
    tags_display = ", ".join(tags) if tags else "No tags selected"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .footer {{ text-align: center; padding: 20px; font-size: 0.9em; color: #777; }}
            .status {{ 
                display: inline-block;
                padding: 5px 10px;
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
                text-transform: capitalize;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Subscription Update</h1>
            </div>
            <div class="content">
                <p>Hello {user_name},</p>
                <p>Your subscription has been updated:</p>
                <p>Status: <span class="status">{status}</span></p>
                <p>Your selected tags: {tags_display}</p>
                <p>Thank you for using Daily Challenge!</p>
            </div>
            <div class="footer">
                <p>© 2025 Daily Challenge. All rights reserved.</p>
                <p>If you didn't make this change, please contact our support team immediately.</p>
            </div>
        </div>
    </body>
    </html>
    """

def get_verification_email_template(user_name: str, verification_link: str, token: str) -> str:
    """
    Generate the email verification HTML content.
    
    Args:
        user_name: The name of the user
        verification_link: The link to verify email
        token: The verification token
        
    Returns:
        str: HTML content for the email verification email
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .footer {{ text-align: center; padding: 20px; font-size: 0.9em; color: #777; }}
            .button {{
                display: inline-block;
                padding: 10px 20px;
                margin: 20px 0;
                background-color: #4CAF50;
                color: white;
                text-decoration: none;
                border-radius: 4px;
            }}
            .verification-token {{
                display: inline-block;
                padding: 10px;
                margin: 10px 0;
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-family: monospace;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Email Verification</h1>
            </div>
            <div class="content">
                <p>Hello {user_name},</p>
                <p>Thank you for registering with Daily Challenge. Please verify your email address to activate your account.</p>
                <p>Click the button below to verify your email:</p>
                <p><a href="{verification_link}" class="button">Verify Email</a></p>
                <p>If the button doesn't work, copy and paste the following link into your browser:</p>
                <p>{verification_link}</p>
                <p>Or use this verification token:</p>
                <p><span class="verification-token">{token}</span></p>
                <p>This verification link will expire in 24 hours.</p>
                <p>Happy Coding!<br>The Daily Challenge Team</p>
            </div>
            <div class="footer">
                <p>© 2025 Daily Challenge. All rights reserved.</p>
                <p>If you didn't create an account, please ignore this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

def get_daily_challenge_email_template(user_name: str, problem: str) -> str:
    """
    Generate the daily challenge email HTML content.

    Args:
        user_name: The name of the user
        problem: The challenge/problem statement

    Returns:
        str: HTML content for the daily challenge email
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .footer {{ text-align: center; padding: 20px; font-size: 0.9em; color: #777; }}
            .problem-block {{ 
                padding: 15px; 
                margin: 15px 0; 
                background-color: #e7f3fe; 
                border-left: 5px solid #2196F3; 
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Today's Coding Challenge</h1>
            </div>
            <div class="content">
                <p>Hello {user_name},</p>
                <p>Here is your daily challenge!</p>
                <div class="problem-block">
                    <strong>Challenge:</strong>
                    <pre style="white-space: pre-wrap; word-break: break-word;">{problem}</pre>
                </div>
                <p>The solution to this challenge will be sent to you in 24 hours.</p>
                <p>Good luck and happy coding!</p>
            </div>
            <div class="footer">
                <p> 2025 Daily Challenge. All rights reserved.</p>
                <p>If you didn't subscribe to these emails, you can manage your preferences in your account.</p>
            </div>
        </div>
    </body>
    </html>
    """

def get_challenge_solution_email_template(user_name: str, problem: str, solution: str, problem_title: str) -> str:
    """
    Generate the challenge solution email HTML content.

    Args:
        user_name: The name of the user
        problem: The challenge/problem statement
        solution: The solution or explanation
        problem_title: The title of the problem

    Returns:
        str: HTML content for the solution email
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .footer {{ text-align: center; padding: 20px; font-size: 0.9em; color: #777; }}
            .problem-block {{ 
                padding: 15px; 
                margin: 15px 0; 
                background-color: #e7f3fe; 
                border-left: 5px solid #2196F3; 
            }}
            .solution-block {{ 
                padding: 15px; 
                margin: 15px 0; 
                background-color: #e8f5e9; 
                border-left: 5px solid #4CAF50; 
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Solution: {problem_title}</h1>
            </div>
            <div class="content">
                <p>Hello {user_name},</p>
                <p>Here's the solution to yesterday's coding challenge:</p>
                <div class="problem-block">
                    <strong>Challenge:</strong>
                    <pre style="white-space: pre-wrap; word-break: break-word;">{problem}</pre>
                </div>
                <div class="solution-block">
                    <strong>Solution:</strong>
                    <pre style="white-space: pre-wrap; word-break: break-word;">{solution}</pre>
                </div>
                <p>We hope you found this challenge valuable!</p>
            </div>
            <div class="footer">
                <p>© 2025 Daily Challenge. All rights reserved.</p>
                <p>If you didn't subscribe to these emails, you can manage your preferences in your account.</p>
            </div>
        </div>
    </body>
    </html>
    """

def get_password_reset_template(user_name: str, reset_link: str, token: str) -> str:
    """
    Generate the password reset email HTML content.
    
    Args:
        user_name: The name of the user
        reset_link: The link to reset password
        token: The reset token
        
    Returns:
        str: HTML content for the password reset email
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4A6572; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .footer {{ text-align: center; padding: 20px; font-size: 0.9em; color: #777; }}
            .button {{
                display: inline-block;
                padding: 10px 20px;
                margin: 20px 0;
                background-color: #4A6572;
                color: white;
                text-decoration: none;
                border-radius: 4px;
            }}
            .reset-token {{
                display: inline-block;
                padding: 10px;
                margin: 10px 0;
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-family: monospace;
            }}
            .warning {{
                color: #e65100;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>
            <div class="content">
                <p>Hello {user_name},</p>
                <p>We received a request to reset your password for Daily Challenge. If you didn't make this request, please ignore this email.</p>
                <p>Click the button below to reset your password:</p>
                <p><a href="{reset_link}" class="button">Reset Password</a></p>
                <p>If the button doesn't work, copy and paste the following link into your browser:</p>
                <p>{reset_link}</p>
                <p>Or use this reset token:</p>
                <p><span class="reset-token">{token}</span></p>
                <p class="warning">This link will expire in 1 hour for security reasons.</p>
                <p>If you did not request a password reset, please ignore this email or contact support if you have concerns.</p>
                <p>Regards,<br>The Daily Challenge Team</p>
            </div>
            <div class="footer">
                <p>© 2025 Daily Challenge. All rights reserved.</p>
                <p>This is an automated message, please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
