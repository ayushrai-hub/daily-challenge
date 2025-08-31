"""
Celery tasks for AI-based content processing and problem generation.
"""
import asyncio
from typing import Dict, List, Any, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from celery import shared_task
from app.core.logging import get_logger
from app.core.config import settings
from app.services.ai_providers.factory import AIProviderFactory
from app.db.models.problem import Problem, DifficultyLevel, VettingTier, ProblemStatus
from app.db.models.tag import Tag
from app.db.session import async_session
from app.repositories.problem_repository import create_problem_with_tags
from app.repositories.tag import TagRepository
from app.services.tag_normalizer import TagNormalizer
from app.tasks.content_processing.pipeline.content_sources import fetch_combined_content
from datetime import datetime

logger = get_logger()


@shared_task(name="generate_problems_with_ai", queue="content")
def generate_problems_with_ai(
    source_data: Optional[Dict[str, Any]] = None,
    source_tasks: Optional[Dict[str, Any]] = None,
    ai_provider: str = "gemini",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    num_problems: int = 3,
    temperature: float = 0.7
) -> Dict[str, Any]:
    """
    Generate coding problems using AI based on source data.
    
    Args:
        source_data: Dictionary with source content (if already fetched)
        source_tasks: Dictionary with source task parameters (for fetching new content)
        ai_provider: AI provider to use (gemini, claude)
        model: Model name to use (provider-specific)
        api_key: API key for the AI provider
        num_problems: Number of problems to generate
        temperature: Controls randomness (0.0 to 1.0)
        
    Returns:
        Dictionary with generated problems and metadata
    """
    logger.info(f"Generating problems with AI provider: {ai_provider}")
    
    # Fetch source content if not provided
    if not source_data and source_tasks:
        try:
            source_data = fetch_combined_content.apply_async(
                kwargs={
                    "github_params": source_tasks.get("github_params"),
                    "stackoverflow_params": source_tasks.get("stackoverflow_params"),
                    "github_api_key": source_tasks.get("github_api_key"),
                    "stackoverflow_api_key": source_tasks.get("stackoverflow_api_key")
                }
            ).get()
        except Exception as e:
            logger.error(f"Error fetching source content: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to fetch source content: {str(e)}",
                "problems": []
            }
    
    # If we still don't have source data, return an error
    if not source_data:
        return {
            "success": False,
            "error": "No source data provided or fetched",
            "problems": []
        }
    
    # Create formatted input for the AI
    github_content = source_data.get("github", {}).get("extracted_content", "No GitHub content available")
    stackoverflow_content = source_data.get("stackoverflow", {}).get("extracted_content", "No Stack Overflow content available")
    
    ai_input = {
        "github": github_content,
        "stackoverflow": stackoverflow_content
    }
    
    # Run async code in sync context
    async def _generate_problems():
        try:
            # Get the appropriate AI provider
            provider = await AIProviderFactory.create_provider(
                provider_type=ai_provider,
                api_key=api_key,
                model=model
            )
            
            # Generate problems
            problems = await provider.generate_problems(
                source_data=ai_input,
                num_problems=num_problems,
                temperature=temperature
            )
            
            # Validate each problem
            validated_problems = []
            for problem in problems:
                validation = await provider.validate_problem(problem)
                validated_problems.append(validation)
            
            return {
                "success": True,
                "problems": problems,
                "validations": validated_problems
            }
        except Exception as e:
            logger.error(f"Error generating problems with AI: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "problems": []
            }
    
    # Execute the async function
    return asyncio.run(_generate_problems())


@shared_task(name="save_problems_to_database", queue="content")
def save_problems_to_database(
    problems_data: Dict[str, Any],
    content_source_id: Optional[str] = None,
    auto_approve: bool = False
) -> Dict[str, Any]:
    # Debug point - track entry into function
    logger.info("=== ENTERING save_problems_to_database ===")
    """
    Save generated problems to the database.
    
    This is a synchronous Celery task that properly interacts with the database
    session and handles transaction management.
    Modified implementation to handle session binding issues with Tag objects.
    Uses fresh sessions for each database operation to prevent detached instance errors.
    
    Args:
        problems_data: Dictionary containing generated problems and metadata
        content_source_id: ID of the content source to associate with problems
        auto_approve: Whether to automatically approve problems
        
    Returns:
        Dictionary with results of the save operation
    """
    logger.info("Starting save_problems_to_database task")
    
    # Import dependencies here to avoid circular imports
    from app.repositories.problem_repository import create_problem_with_tags_sync
    from app.db.session import SessionLocal
    from app.repositories.tag import TagRepository
    from app.db.models.tag import Tag, TagType
    from app.db.models.tag_normalization import TagNormalization, TagSource, TagReviewStatus
    from app.services.tag_normalizer import TagNormalizer
    from datetime import datetime
    
    # Extract problems list from response
    problems_list = problems_data.get("problems", [])
    num_problems = len(problems_list)
    logger.info(f"Saving {num_problems} problems to database with auto_approve={auto_approve}")
     
    if not problems_list:
        return {
            "success": False,
            "error": "No problems to save",
            "saved_problem_ids": []
        }
            
    # Set up content source ID if provided
    if not content_source_id:
        content_source_id = problems_data.get("content_source_id")
    
    # Process each problem
    saved_problem_ids = []
    
    # Add missing import for uuid
    import uuid
    
    try:
        for problem_index, problem in enumerate(problems_list):
            logger.info(f"Processing problem {problem_index+1}/{len(problems_list)}")
                
            # Track problem processing with unique ID for log tracking
            problem_id = problem.get("id", str(uuid.uuid4())[:8])
            logger.info(f"=== Processing problem {problem_id} ===")
            
            # Default values
            difficulty_level = problem.get("difficulty_level", "medium")
            status = problem.get("status", "draft")
            
            # Use proper enum value for vetting tier instead of integer
            vetting_tier_value = problem.get("vetting_tier", "tier3_needs_review")
            vetting_tier = VettingTier(vetting_tier_value) if isinstance(vetting_tier_value, str) else VettingTier.tier3_needs_review
            
            raw_tags = problem.get("tags", [])
            logger.info(f"Problem {problem_id} tags: {raw_tags}")
            
            # Create a new session for each problem to avoid session binding issues
            # This ensures each problem has its own transaction and session scope
            # preventing detached object errors across problem processing
            with SessionLocal() as db:
                # Initialize the tag normalizer with safe tag loading
                tag_repo = TagRepository(db)
                normalizer = TagNormalizer(tag_repo)
                    
                # Process tags with proper session binding
                normalized_tags = []
                processed_tag_names = []
                    
                # Track tag processing step by step
                logger.info(f"Starting tag processing for problem {problem_id} with {len(raw_tags)} tags")
                    
                # Add debugging info for tags processing
                logger.info(f"Processing tags: {raw_tags}")
                        
                for i, raw_tag in enumerate(raw_tags):
                    logger.info(f"Processing tag {i+1}/{len(raw_tags)}: '{raw_tag}'")
                    if not raw_tag or not str(raw_tag).strip():
                        logger.info(f"Skipping empty tag: '{raw_tag}'")
                        continue
                        
                    # Clean and normalize the tag name
                    clean_tag = str(raw_tag).strip()
                    
                    # Check if this tag is already in the tag_normalizations table by original name
                    logger.info(f"Searching for existing normalization with original_name='{clean_tag}'")
                    existing_norm = db.query(TagNormalization).filter(
                        TagNormalization.original_name == clean_tag
                    ).first()
                    logger.info(f"Found existing normalization by original name: {existing_norm is not None}")
                    if existing_norm:
                        logger.info(f"Existing norm attributes: ID={existing_norm.id}, original={existing_norm.original_name}, normalized={existing_norm.normalized_name if hasattr(existing_norm, 'normalized_name') else 'MISSING'}")
                
                    # Also check if there's an existing normalization for this tag by normalized name
                    if not existing_norm:
                        # Get normalized version of the tag
                        logger.info(f"Normalizing tag: '{clean_tag}'")
                        normalized_names = normalizer.normalize_tag_names([clean_tag])
                        logger.info(f"Normalization result: {normalized_names}")
                        normalized_name = normalized_names[0] if normalized_names else clean_tag
                        logger.info(f"Selected normalized_name: '{normalized_name}'")
                        
                        # Check if a normalization exists with this normalized name
                        logger.info(f"Checking for existing normalization with normalized_name='{normalized_name}'")
                        try:
                            existing_norm_by_normalized = db.query(TagNormalization).filter(
                                TagNormalization.normalized_name.ilike(normalized_name)
                            ).first()
                            logger.info(f"Found existing normalization by normalized name: {existing_norm_by_normalized is not None}")
                        except Exception as e:
                            logger.error(f"Error querying by normalized name: {str(e)}")
                            existing_norm_by_normalized = None
                        
                        if existing_norm_by_normalized:
                            existing_norm = existing_norm_by_normalized
                            logger.info(f"Using existing normalization from normalized name: {normalized_name}")
                            logger.info(f"Existing norm attributes: ID={existing_norm.id}, original={existing_norm.original_name}, normalized={existing_norm.normalized_name if hasattr(existing_norm, 'normalized_name') else 'MISSING'}")
                    
                    # Only use normalized_name from existing_norm if it exists
                    # This is a defensive check to prevent NoneType errors
                    if 'normalized_name' not in locals() or normalized_name is None:
                        logger.warning(f"normalized_name not defined before existing_norm check for tag '{clean_tag}'")
                        normalized_name = clean_tag
                        logger.info(f"Set default normalized_name='{normalized_name}'")
                        
                    if existing_norm is None:
                        logger.info(f"existing_norm is None, using normalized_name='{normalized_name}'")
                    elif not hasattr(existing_norm, 'normalized_name'):
                        logger.warning(f"existing_norm missing normalized_name attribute for tag '{clean_tag}'")
                    elif existing_norm.normalized_name is None:
                        logger.warning(f"existing_norm.normalized_name is None for tag '{clean_tag}'")
                    elif existing_norm and hasattr(existing_norm, 'normalized_name') and existing_norm.normalized_name:
                        logger.info(f"Using existing_norm.normalized_name='{existing_norm.normalized_name}'")
                        normalized_name = str(existing_norm.normalized_name)
                
                    # If we have an approved normalization, use its approved tag
                    # Add defensive checks to ensure all required attributes exist
                    if (existing_norm and hasattr(existing_norm, 'review_status') and 
                        existing_norm.review_status == TagReviewStatus.approved and 
                        hasattr(existing_norm, 'approved_tag_id') and existing_norm.approved_tag_id):
                        # Get the approved tag from the database to ensure we have the full object
                        approved_tag = db.query(Tag).filter(Tag.id == existing_norm.approved_tag_id).first()
                        if approved_tag:
                            normalized_tags.append(approved_tag.name)
                            processed_tag_names.append(approved_tag.name)
                            logger.info(f"Using approved tag mapping: {clean_tag} -> {approved_tag.name}")
                            continue
                
                    # If we don't have a normalized name yet, get one
                    # Make sure normalized_name is always defined
                    if 'normalized_name' not in locals():
                        normalized_name = clean_tag
                        
                    if not existing_norm:
                        normalized_names = normalizer.normalize_tag_names([clean_tag])
                        normalized_name = normalized_names[0] if normalized_names else clean_tag
                    
                    # Try to find existing tags with this name (case-insensitive)
                    try:
                        existing_tag = tag_repo.get_by_name_case_insensitive(normalized_name)
                    except Exception as e:
                        logger.warning(f"Error finding tag '{normalized_name}': {str(e)}")
                        existing_tag = None
                    
                    # Calculate confidence score based on multiple factors
                    confidence_score = 0.7  # Base confidence
                
                    # Increase confidence if tag already exists with exact match
                    if existing_tag and existing_tag.name == normalized_name:
                        confidence_score = 0.95  # Very high confidence for exact matches
                    # Slightly lower confidence for case-insensitive matches
                    elif existing_tag:
                        confidence_score = 0.9
                    # Adjust confidence based on tag characteristics
                    if len(normalized_name) < 3:  # Very short tags are suspicious
                        confidence_score *= 0.8
                    if any(char.isdigit() for char in normalized_name):  # Tags with numbers might be more specific/accurate
                        confidence_score *= 1.1  # Slight boost
                    
                    # Cap confidence score at 1.0
                    confidence_score = min(confidence_score, 1.0)
                    
                    # If this tag doesn't already exist in the TagNormalization table, add it
                    if not existing_norm:
                        # Create a new entry in the tag_normalizations table
                        tag_norm = TagNormalization(
                            original_name=str(clean_tag),
                            normalized_name=str(normalized_name),
                            review_status=TagReviewStatus.pending,
                            source=TagSource.ai_generated,
                            confidence_score=confidence_score,
                            auto_approved=auto_approve
                        )
                        
                        # If auto-approve is enabled and the tag exists with high confidence, link it automatically
                        # Add defensive checks to safely handle existing_tag properties
                        if auto_approve and existing_tag and confidence_score >= 0.9:
                            # Get the tag ID and name before any potential session operations
                            # This prevents issues with detached objects
                            try:
                                tag_id = existing_tag.id
                                tag_name = existing_tag.name
                            except Exception as e:
                                # Make sure normalized_name is defined before using it in error logging
                                nm_name = normalized_name if 'normalized_name' in locals() else clean_tag
                                logger.warning(f"Error accessing tag attributes for '{nm_name}': {str(e)}")
                                # Fall back to a safe name if we can't get the existing tag properties
                                tag_id = None
                                tag_name = nm_name
                            
                            tag_norm.review_status = TagReviewStatus.approved
                            # Only set approved_tag_id if we have a valid tag_id
                            if tag_id is not None:
                                tag_norm.approved_tag_id = tag_id  # Use the ID instead of the object
                            tag_norm.reviewed_at = datetime.now()
                            normalized_tags.append(tag_name)  # Use the name directly
                            processed_tag_names.append(tag_name)
                            logger.info(f"Auto-approved tag with confidence {confidence_score:.2f}: {clean_tag} -> {tag_name}")
                        else:
                            # Ensure normalized_name is defined before using it
                            nm_name = normalized_name if 'normalized_name' in locals() else clean_tag
                            # Just add the normalized name for now
                            normalized_tags.append(nm_name)
                            processed_tag_names.append(nm_name)
                            logger.info(f"Created pending tag normalization (confidence: {confidence_score:.2f}): {clean_tag} -> {nm_name}")
                        
                        db.add(tag_norm)
                    else:
                        # Update confidence score if it's higher than the existing one
                        if confidence_score > (existing_norm.confidence_score or 0):
                            existing_norm.confidence_score = confidence_score
                            # Safely access normalized_name
                            nm_name = normalized_name if 'normalized_name' in locals() else clean_tag
                            logger.info(f"Updated confidence score for {nm_name} to {confidence_score:.2f}")
                        
                        # For approved normalizations, we've already handled them above
                        # For pending ones, use the normalized name
                        nm_name = normalized_name if 'normalized_name' in locals() else clean_tag
                        if hasattr(existing_norm, 'normalized_name') and existing_norm.normalized_name:
                            nm_name = existing_norm.normalized_name
                            
                        normalized_tags.append(nm_name)
                        processed_tag_names.append(nm_name)
                        logger.info(f"Using pending normalized tag: {clean_tag} -> {nm_name}")
                            
                        # If auto-approve is enabled and we found a matching tag with high confidence, approve it
                        if auto_approve and existing_tag and confidence_score >= 0.9 and not existing_norm.approved_tag_id:
                            # Extract the necessary information before any session operations
                            # Wrap in try/except for safety in case existing_tag is invalid
                            try:
                                tag_id = existing_tag.id
                                tag_name = existing_tag.name
                                
                                # Only proceed with auto-approval if we got valid tag info
                                existing_norm.review_status = TagReviewStatus.approved
                                existing_norm.approved_tag_id = tag_id  # Use the ID instead of the object
                                existing_norm.reviewed_at = datetime.now()
                                existing_norm.auto_approved = True
                                logger.info(f"Auto-approved existing normalization with confidence {confidence_score:.2f}: {clean_tag} -> {tag_name}")
                            except Exception as e:
                                # Safe access to normalized_name
                                nm_name = normalized_name if 'normalized_name' in locals() else clean_tag
                                logger.warning(f"Error accessing tag attributes for auto-approval of '{nm_name}': {str(e)}")
                                # Skip auto-approval if we can't access tag attributes
            
            # Commit the TagNormalization entries separately
            db.commit()
            
            logger.info(f"Final processed tags: {processed_tag_names}")
            
            # IMPORTANT: We're changing our approach to completely separate tag normalization from problem creation
            # Instead of creating tags now, we'll store the raw tag names and handle them separately in the admin process
            
            # We'll only use existing tags that are already in the system and have been approved
            logger.info(f"Checking for existing approved tags among the normalized tags")
            safe_tags = []
            pending_tag_normalizations = []
            tag_metadata = {}  # Store metadata about each tag for later admin processing
            
            # Prepare a list of tags that already exist and are approved in the system
            for tag_name in normalized_tags:
                if not tag_name or not tag_name.strip():
                    continue
                    
                # Store information about this tag for metadata
                tag_metadata[tag_name] = {
                    "original_name": tag_name,
                    "normalized_name": tag_name,  # We're now preserving original case
                    "status": "pending"
                }

                # Just check if tag exists - don't try to create
                # IMPORTANT: Only store tag names, not Tag objects, to avoid session binding issues
                try:
                    # Check if tag exists by name only
                    tag_exists = tag_repo.name_exists_case_insensitive(tag_name)
                    if tag_exists:
                        # Get the canonical name to ensure consistent casing
                        canonical_name = tag_repo.get_canonical_name(tag_name)
                        logger.info(f"Found existing safe tag: {canonical_name}")
                        safe_tags.append(canonical_name or tag_name) # Use original if canonical not found
                    else:
                        logger.info(f"Tag '{tag_name}' doesn't exist yet, will be added to pending normalizations")
                        pending_tag_normalizations.append(tag_name)
                except Exception as e:
                    logger.error(f"Error checking tag '{tag_name}': {str(e)}")
                    pending_tag_normalizations.append(tag_name)
            
            logger.info(f"Using {len(safe_tags)} existing tags and storing {len(pending_tag_normalizations)} pending tags as metadata")
            
            # Update the tag metadata with additional information for admin approval process
            tag_metadata.update({
                "normalized_tags": normalized_tags,  # All normalized tags from AI processing
                "raw_tags": problem.get("tags", []),  # Original raw tags from source
                "pending_tags": pending_tag_normalizations,  # Tags that need admin approval
                "safe_tags": safe_tags,  # Tags that already exist in the system
            })
            
            # Serialize the metadata to JSON if needed
            import json
            
            # Prepare problem data with only safe tags and store the rest as metadata
            problem_data = {
                "title": problem.get("title", "Untitled Problem"),
                "description": problem.get("description", ""),
                "solution": problem.get("solution", ""),
                "hints": problem.get("hints", []),
                "difficulty_level": difficulty_level,
                "status": status,
                "vetting_tier": vetting_tier,
                "content_source_id": content_source_id,
                "approved_at": datetime.now() if auto_approve else None,
                "tags": safe_tags,  # Only use tags that already exist in the system
                "problem_metadata": {"tag_data": tag_metadata}  # Store all tag information for later processing
            }
            
            try:
                # Save problem to database using sync version
                # This happens in the context of its own session
                problem_id = create_problem_with_tags_sync(
                    db=db,
                    problem_data=problem_data
                )
                
                saved_problem_ids.append(str(problem_id))
                logger.info(f"Saved problem {problem_id}: {problem.get('title')}")
                
                # Explicit commit to ensure changes are persisted before session closes
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Error saving problem {problem.get('title')}: {str(e)}", exc_info=True)
        
        return {
            "success": True,
            "saved_problem_ids": saved_problem_ids,
            "saved_count": len(saved_problem_ids)
        }
    except Exception as e:
        logger.error(f"Error saving problems to database: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "saved_problem_ids": saved_problem_ids,
            "saved_count": len(saved_problem_ids)
        }


@shared_task(name="complete_content_pipeline", queue="content")
def complete_content_pipeline(
    github_params: Optional[Dict[str, Any]] = None,
    stackoverflow_params: Optional[Dict[str, Any]] = None,
    ai_provider: str = "gemini",
    num_problems: int = 3,
    auto_approve: bool = False,
    content_source_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run the complete content pipeline: fetch source data, generate problems, save to database.
    This version uses direct function calls instead of chaining tasks with .get()
    
    Args:
        github_params: GitHub query parameters
        stackoverflow_params: Stack Overflow query parameters
        ai_provider: AI provider to use (gemini, claude)
        num_problems: Number of problems to generate
        auto_approve: Whether to automatically approve problems
        content_source_id: ID of the content source (if available)
        
    Returns:
        Dictionary with pipeline results
    """
    logger.info(f"Starting complete content pipeline with {ai_provider}")
    
    # IMPORTANT: Pre-process any tags in the stackoverflow_params to ensure they exist safely
    # This prevents unique constraint violations when these tags are later used
    if stackoverflow_params and "tags" in stackoverflow_params and stackoverflow_params["tags"]:
        # Import necessary repositories/services here to avoid circular imports
        from app.db.session import get_sync_db
        from app.repositories.tag import TagRepository
        
        try:
            # Get a synchronous database session
            db = next(get_sync_db())
            tag_repo = TagRepository(db)
            
            # Process each tag to ensure it exists using our case-insensitive methods
            processed_tags = []
            for tag_name in stackoverflow_params["tags"]:
                logger.info(f"Pre-processing StackOverflow tag: {tag_name}")
                try:
                    # IMPORTANT: Just check for existence and get the canonical name
                    # DO NOT get or create the Tag object - we only want the name
                    if tag_repo.name_exists_case_insensitive(tag_name):
                        # Get the canonical name to ensure consistent casing
                        canonical_name = tag_repo.get_canonical_name(tag_name)
                        processed_tags.append(canonical_name or tag_name)  # Use original if canonical not found
                        logger.info(f"Processed tag '{tag_name}' to canonical name '{canonical_name}'")
                    else:
                        # Just use the original name if it doesn't exist
                        processed_tags.append(tag_name)
                        logger.info(f"Tag '{tag_name}' doesn't exist yet, using original name")
                except Exception as e:
                    logger.error(f"Error pre-processing tag '{tag_name}': {str(e)}")
                    processed_tags.append(tag_name)  # Fall back to original name if error
            
            # Replace the tags in stackoverflow_params with the processed versions
            stackoverflow_params["tags"] = processed_tags
            db.commit()
            logger.info(f"Successfully pre-processed StackOverflow tags: {processed_tags}")
        except Exception as e:
            logger.error(f"Error during tag pre-processing: {str(e)}")
            # Continue with original tags if there's an error
    
    # Step 1: Fetch source content directly without using task.get()
    from app.tasks.content_processing.pipeline.content_sources import fetch_combined_content as fetch_content_direct
    source_data = fetch_content_direct(
        github_params=github_params,
        stackoverflow_params=stackoverflow_params
    )
    
    if not source_data or any("error" in source.get('error', '') for source in source_data.values() if isinstance(source, dict)):
        return {
            "success": False,
            "error": "Failed to fetch source content",
            "source_data": source_data,
            "problems_generated": 0,
            "problems_saved": 0
        }
    
    # Step 2: Generate problems with AI directly
    problems_data = generate_problems_with_ai(
        source_data=source_data,
        ai_provider=ai_provider,
        num_problems=num_problems
    )
    
    if not problems_data.get("success", False):
        return {
            "success": False,
            "error": f"Failed to generate problems: {problems_data.get('error')}",
            "source_data_success": True,
            "problems_generated": 0,
            "problems_saved": 0
        }
    
    # Step 3: Save problems to database directly
    save_result = save_problems_to_database(
        problems_data=problems_data,
        content_source_id=content_source_id,
        auto_approve=auto_approve
    )
    
    return {
        "success": save_result.get("success", False),
        "error": save_result.get("error"),
        "source_data_success": True,
        "problems_generated": len(problems_data.get("problems", [])),
        "problems_saved": len(save_result.get("saved_problem_ids", [])),
        "saved_problem_ids": save_result.get("saved_problem_ids", [])
    }
