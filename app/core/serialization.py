"""
Core serialization utilities to configure Pydantic serialization consistently across the application.
"""
from uuid import UUID
from datetime import datetime
from pydantic import TypeAdapter
from pydantic.json_schema import JsonSchemaValue
from typing import Annotated, Any, Dict, Type


# Define type adapters for common types that need custom serialization
uuid_serializer = TypeAdapter(UUID)
uuid_serializer.json_schema = lambda *args, **kwargs: {"type": "string", "format": "uuid"}


def register_serializers():
    """
    Register type adapters globally to handle common serialization needs.
    Call this function during application startup.
    """
    # This is a hook for any future global serializer registration
    pass


# Annotated type for UUID with consistent serialization
UUIDSTR = Annotated[UUID, uuid_serializer]
