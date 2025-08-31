"""
Factory for AI provider selection.
Provides a unified interface for selecting and initializing the appropriate AI provider.
"""
from typing import Dict, Optional, Union, Any
from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai_providers.base import BaseAIProvider
from app.services.ai_providers.gemini_provider import GeminiProvider
from app.services.ai_providers.claude_provider import ClaudeProvider

logger = get_logger()


class AIProviderFactory:
    """Factory for selecting and initializing AI providers."""
    
    # Supported provider types
    PROVIDER_GEMINI = "gemini"
    PROVIDER_CLAUDE = "claude"
    
    @staticmethod
    async def create_provider(
        provider_type: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> BaseAIProvider:
        """
        Create and initialize an AI provider instance.
        
        Args:
            provider_type: Type of AI provider to create (gemini, claude)
                          If not specified, will use the default from settings
            api_key: Optional API key (if not specified, will use from settings)
            model: Optional model name (if not specified, will use provider default)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Initialized BaseAIProvider instance
            
        Raises:
            ValueError: If provider_type is invalid or provider initialization fails
        """
        # Default to settings
        if not provider_type:
            provider_type = settings.DEFAULT_AI_PROVIDER
            
        # Create the appropriate provider
        if provider_type.lower() == AIProviderFactory.PROVIDER_GEMINI:
            provider = GeminiProvider(api_key=api_key, model=model or "gemini-1.5-pro")
            
        elif provider_type.lower() == AIProviderFactory.PROVIDER_CLAUDE:
            provider = ClaudeProvider(api_key=api_key, model=model or "claude-3-opus-20240229")
            
        else:
            error_msg = f"Unsupported AI provider type: {provider_type}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Initialize the provider
        await provider.initialize()
        logger.info(f"Initialized AI provider: {provider_type}")
        
        return provider
