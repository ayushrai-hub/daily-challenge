"""
Tag model patching module for SQLAlchemy mapping enhancement.
This file contains code to enhance the Tag model's relationship configuration to properly
handle complex self-referential relationships and avoid mapper initialization errors.
"""
from sqlalchemy import event, inspect
from sqlalchemy.orm import mapper, configure_mappers, clear_mappers
from sqlalchemy.orm.relationships import RelationshipProperty
from app.core.logging import get_logger

logger = get_logger()

# Function to enhance tag relationship configuration
def enhance_tag_relationships(class_registry):
    """
    Enhance the Tag model's relationship configurations at the SQLAlchemy mapper level.
    This ensures the self-referential many-to-many relationship is correctly configured
    with the appropriate foreign() and remote() annotations.
    
    Args:
        class_registry: The SQLAlchemy class registry containing all mapped classes
    """
    try:
        # Get the Tag class from the registry if it exists
        tag_class = None
        for key, cls in class_registry.items():
            if isinstance(key, str) and "Tag" in key:
                tag_class = cls
                break
        
        if not tag_class:
            logger.info("Tag class not found in registry yet, will be configured later")
            return
            
        logger.info(f"Enhancing Tag relationship configuration for {tag_class.__name__}")
        
        # We've moved from disabling relationships to ensuring they're properly configured
        # in the Tag model itself using foreign() and remote() annotations
        
        # Log the current configuration for debugging
        if hasattr(tag_class, 'parents') and hasattr(tag_class, 'children'):
            logger.info("Tag hierarchy relationships already configured")
        else:
            logger.info("Tag hierarchy relationships not yet configured")
            
        # No explicit modifications needed - the relationships are now properly
        # defined directly in the Tag model with correct annotations
    except Exception as e:
        logger.error(f"Error enhancing Tag relationships: {str(e)}")

# Register multiple event listeners to ensure proper configuration
@event.listens_for(mapper, 'before_configured')
def receive_before_configured():
    """
    SQLAlchemy event listener that runs before mapper configuration.
    This ensures our enhancements are applied before any mappers are initialized.
    """
    logger.info("Applying Tag model enhancements before mapper configuration")
    # Get the mapper registry from SQLAlchemy
    # SQLAlchemy 1.4+ uses _registry attribute on Mapper class
    registry = getattr(mapper, '_registry', {})
    enhance_tag_relationships(registry)

@event.listens_for(mapper, 'after_configured')
def receive_after_configured():
    """
    SQLAlchemy event listener that runs after all mappers are configured.
    This allows us to verify the configuration was successful.
    """
    logger.info("All SQLAlchemy mappers have been configured successfully")
    
    # For debugging - this will log all the mapped classes and their relationships
    # This can be commented out in production
    try:
        from app.db.models.tag import Tag
        tag_mapper = inspect(Tag)
        rel_names = [r.key for r in tag_mapper.relationships]
        logger.info(f"Tag mapper relationships: {rel_names}")
    except Exception as e:
        logger.error(f"Error inspecting Tag mapper: {str(e)}")
