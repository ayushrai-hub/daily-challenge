"""
Tests for the email service functionality.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.email.email_service import EmailService
from app.core.config import settings

# Ensure resend is patched correctly
import resend


class TestEmailService:
    """Test cases for the EmailService class."""

    @pytest.mark.asyncio
    @patch('resend.Emails.send')
    async def test_send_email_success(self, mock_send):
        """Test sending an email successfully."""
        # Setup
        mock_send.return_value = {"id": "test_email_id"}

        # Test
        response = await EmailService.send_email(
            to="user@example.com",
            subject="Test Email",
            html="<p>Test content</p>",
            force_send=True  # Force send to bypass validation in tests
        )

        # Assert
        assert response["id"] == "test_email_id"
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        params = kwargs.get('params', {})
        assert "user@example.com" in params['to']
        assert params['subject'] == "Test Email"
        assert params['html'] == "<p>Test content</p>"

    @pytest.mark.asyncio
    @patch('resend.Emails.send')
    async def test_send_email_failure(self, mock_send):
        """Test handling of email sending failure."""
        # Setup
        mock_send.side_effect = Exception("Test error")

        # Test & Assert
        with pytest.raises(Exception) as exc_info:
            await EmailService.send_email(
                to="user@example.com",
                subject="Test Email",
                html="<p>Test content</p>",
                force_send=True  # Force send to bypass validation in tests
            )
        assert "Test error" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('app.services.email.email_service.EmailService.send_email')
    async def test_send_welcome_email(self, mock_send):
        """Test sending a welcome email."""
        # Setup
        mock_send.return_value = {"id": "welcome_email_id"}

        # Test
        response = await EmailService.send_welcome_email(
            to="newuser@example.com",
            user_name="New User",
            force_send=True  # Force send to bypass validation in tests
        )

        # Assert
        assert response["id"] == "welcome_email_id"
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        assert "newuser@example.com" in call_kwargs.get('to', '')
        assert "Welcome" in call_kwargs.get('subject', '')
        assert "New User" in call_kwargs.get('html', '')

    @pytest.mark.asyncio
    @patch('app.services.email.email_service.EmailService.send_email')
    async def test_send_subscription_update(self, mock_send):
        """Test sending a subscription update email."""
        # Setup
        mock_send.return_value = {"id": "subscription_email_id"}

        # Test
        response = await EmailService.send_subscription_update(
            to="user@example.com",
            user_name="Test User",
            status="active",
            tags=["python", "javascript"],
            force_send=True  # Force send to bypass validation in tests
        )

        # Assert
        assert response["id"] == "subscription_email_id"
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        assert "user@example.com" in call_kwargs.get('to', '')
        assert "Subscription" in call_kwargs.get('subject', '')
        assert "Test User" in call_kwargs.get('html', '')
        assert "python" in call_kwargs.get('html', '')
        assert "javascript" in call_kwargs.get('html', '')
