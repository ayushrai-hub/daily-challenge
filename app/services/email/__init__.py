"""
Email service module for handling all email-related operations.
"""

from .email_service import EmailService, WebhookService
from .templates import get_welcome_email_template, get_subscription_update_template

__all__ = [
    "EmailService",
    "WebhookService",
    "get_welcome_email_template",
    "get_subscription_update_template"
]
