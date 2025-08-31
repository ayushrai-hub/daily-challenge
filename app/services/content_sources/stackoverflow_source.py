"""
Stack Overflow content source implementation.
Fetches questions, answers, and discussions from Stack Overflow.
"""
import httpx
import html
from typing import Dict, List, Any, Optional, Union
from app.core.config import settings
from app.core.logging import get_logger
from app.services.content_sources.base import BaseContentSource, ContentSourceError

logger = get_logger()


class StackOverflowSource(BaseContentSource):
    """Stack Overflow content source implementation."""
    
    def __init__(self, app_key: Optional[str] = None):
        """
        Initialize the Stack Overflow source connector.
        
        Args:
            app_key: Stack Overflow App Key/Client ID from Stack Apps (defaults to settings)
                    This is NOT a traditional API key but the key obtained 
                    when registering an application on Stack Apps.
        """
        self.app_key = app_key or settings.STACKOVERFLOW_APP_KEY
        self.base_url = "https://api.stackexchange.com/2.3"
        self.client = None
        self.is_initialized = False
        self.tag_frequency = {}  # Track tag frequency for diversity scoring
    
    async def initialize(self) -> None:
        """Initialize the Stack Overflow API client."""
        if self.is_initialized:
            return
            
        try:
            # Initialize httpx client for API calls
            self.client = httpx.AsyncClient(
                timeout=30.0,
            )
            self.is_initialized = True
            logger.info("Stack Overflow content source initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Stack Overflow source: {str(e)}")
            raise ContentSourceError(f"Stack Overflow initialization failed: {str(e)}")
    
    async def fetch_content(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch content from Stack Overflow based on query parameters.
        
        Args:
            query_params: Dictionary with parameters such as:
                - tags: List of tags to filter by
                - q: Search query
                - content_type: Type of content to fetch (questions, answers)
                - sort: Sort order (activity, votes, creation, relevance)
                - max_items: Maximum number of items to fetch (default 10)
                
        Returns:
            Dictionary with raw content from Stack Overflow
        """
        if not self.is_initialized:
            await self.initialize()
            
        tags = query_params.get("tags", [])
        query = query_params.get("q", "")
        content_type = query_params.get("content_type", "questions")
        sort = query_params.get("sort", "votes")
        max_items = min(query_params.get("max_items", 10), 100)  # API limit is 100
        
        if not tags and not query:
            raise ContentSourceError("Either tags or query must be provided")
            
        results = {
            "query": query,
            "tags": tags,
            "content_type": content_type,
            "items": []
        }
        
        try:
            # Base API parameters
            params = {
                "site": "stackoverflow",
                "order": "desc",
                "sort": sort,
                "filter": "withbody",  # Include the body content
            }
            
            if self.app_key:
                params["key"] = self.app_key  # 'key' is the parameter name for the app_key in Stack API
                
            if query:
                params["q"] = query
            
            # Hybrid approach for tags in questions mode
            if tags and content_type == "questions":
                # First try AND operation (combining tags with semicolons)
                and_results = await self._fetch_combined_tags_questions(tags, params.copy(), max_items)
                
                # Then do the OR operation (separate calls per tag) 
                or_results = await self._fetch_separate_tags_questions(tags, params.copy(), max_items)
                
                # Merge results, prioritizing AND results but ensuring diversity
                seen_question_ids = set()
                all_questions = []
                
                # First add AND results (higher relevance)
                for question in and_results:
                    question_id = question.get("question_id")
                    if question_id and question_id not in seen_question_ids:
                        seen_question_ids.add(question_id)
                        all_questions.append(question)
                
                # Then add OR results that aren't duplicates
                for question in or_results:
                    question_id = question.get("question_id")
                    if question_id and question_id not in seen_question_ids:
                        seen_question_ids.add(question_id)
                        all_questions.append(question)
                        
                        # Stop if we've reached twice the max_items (we'll score and filter later)
                        if len(all_questions) >= max_items * 2:
                            break
                seen_question_ids = set()  # Track IDs to avoid duplicates
                all_questions = []
                
                # Calculate items per tag - distribute evenly but ensure we get some results
                per_tag_pagesize = max(1, min(max_items, 30))  # At most 30 per tag to avoid excessive API calls
                
                # Make a separate API call for each tag
                for tag in tags:
                    tag_params = params.copy()
                    tag_params["tagged"] = tag  # Single tag
                    tag_params["pagesize"] = per_tag_pagesize
                    
                    # Add parameters specific to questions endpoint
                    tag_params["filter"] = "!-*jbN-o8P3E5"  # Include body, answers, comments
                    
                    logger.info(f"Fetching Stack Overflow content for tag: {tag}")
                    
                    try:
                        # Make the API request for this specific tag
                        response = await self.client.get(f"{self.base_url}/questions", params=tag_params)
                        response.raise_for_status()
                        
                        data = response.json()
                        
                        # Add unique questions to our collection
                        for question in data.get("items", []):
                            question_id = question.get("question_id")
                            if question_id and question_id not in seen_question_ids:
                                seen_question_ids.add(question_id)
                                all_questions.append(question)
                                
                                # Stop if we've reached the max_items limit
                                if len(all_questions) >= max_items:
                                    break
                    except Exception as e:
                        logger.warning(f"Error fetching tag {tag}: {str(e)}")
                        # Continue with other tags even if one fails
                
                # Score and sort the merged questions from both AND and OR operations
                logger.info(f"Scoring {len(all_questions)} unique questions from both AND and OR operations")
                
                # Calculate relevance score for each question
                scored_questions = []
                for question in all_questions:
                    # Base score starts with the question score (upvotes)
                    score = question.get("score", 0) * 1.5  # Weight upvotes moderately
                    
                    # Boost questions with accepted answers
                    if any(answer.get("is_accepted", False) for answer in question.get("answers", [])):
                        score += 80  # Significant boost for accepted answers
                    
                    # Boost questions with code samples (approximated by code tags in body)
                    body = question.get("body", "")
                    if "<code>" in body:
                        score += 50  # Boost for having code examples
                        # More code blocks = better examples
                        code_block_count = body.count("<code>")
                        score += min(code_block_count * 10, 50)  # Cap at +50
                    
                    # Boost for answer count (more answers = more perspectives)
                    answer_count = question.get("answer_count", 0)
                    score += min(answer_count * 8, 40)  # Cap at +40
                    
                    # Boost for view count (popular = likely useful)
                    view_count = question.get("view_count", 0)
                    score += min(view_count // 100, 30)  # Cap at +30
                    
                    # Check for tag matches in the question tags
                    question_tags = question.get("tags", [])
                    
                    # ENHANCED: Massively boost exact tag matches from requested tags
                    # to ensure we prioritize technology-specific content
                    tag_match_count = 0
                    for tag in tags:
                        if tag.lower() in [qt.lower() for qt in question_tags]:
                            tag_match_count += 1
                            # Higher boost for exact tag matches
                            score += 150  # Substantial boost for tag relevance
                    
                    # NEW: Boost for technology-specific tags to avoid generic algorithm questions
                    tech_specific_tags = ["javascript", "react", "node.js", "php", "python", "ruby", "java", 
                                          "c#", "swift", "kotlin", "go", "rust", "typescript", "angular", 
                                          "vue", "django", "flask", "laravel", "spring", "express"]
                    
                    for tech_tag in tech_specific_tags:
                        if tech_tag.lower() in [qt.lower() for qt in question_tags]:
                            score += 70  # Boost for technical specificity
                    
                    # NEW: Boost questions containing practical implementations
                    practical_keywords = ["implementation", "example", "create", "build", "develop", 
                                         "optimize", "solve", "approach", "design pattern"]
                    title = question.get("title", "").lower()
                    for keyword in practical_keywords:
                        if keyword in title or keyword in body.lower():
                            score += 40  # Boost for practical applications
                            break
                    
                    # NEW: Diversity boost based on tag uniqueness
                    # If a tag is rare in our collection, boost its score
                    for tag in question_tags:
                        if tag.lower() not in [t.lower() for t in self.tag_frequency.keys()]:
                            self.tag_frequency[tag] = 1
                            score += 50  # Boost for diversity
                        else:
                            self.tag_frequency[tag] += 1
                            # Slightly penalize very frequent tags to encourage diversity
                            if self.tag_frequency[tag] > 3:
                                score -= 10 * min(self.tag_frequency[tag] - 3, 5)  # Cap penalty at -50
                    
                    # Penalize extremely long questions slightly to favor concise examples
                    body_length = len(body)
                    if body_length > 10000:
                        score -= 20
                        
                    # NEW: Boost recent/updated content
                    if question.get("last_activity_date"):
                        # If activity within last 2 years, boost it
                        import time
                        current_time = int(time.time())
                        two_years_ago = current_time - (2 * 365 * 24 * 60 * 60)
                        if question.get("last_activity_date", 0) > two_years_ago:
                            score += 40  # Boost for recently active content
                    
                    scored_questions.append((score, question))
                
                # Sort by score descending
                scored_questions.sort(reverse=True, key=lambda x: x[0])
                
                # Log scores for visibility
                logger.info(f"Top question scores: {[score for score, _ in scored_questions[:5]]}")
                
                # Take top scoring questions up to max_items
                all_questions = [question for _, question in scored_questions[:max_items]]
                
                # Process questions
                for question in all_questions:
                    # Unescape HTML entities in text fields
                    title = html.unescape(question.get("title", ""))
                    body = html.unescape(question.get("body", ""))
                    
                    item = {
                        "type": "question",
                        "id": question.get("question_id"),
                        "title": title,
                        "body": body,
                        "tags": question.get("tags", []),
                        "score": question.get("score", 0),
                        "view_count": question.get("view_count", 0),
                        "answer_count": question.get("answer_count", 0),
                        "is_answered": question.get("is_answered", False),
                        "creation_date": question.get("creation_date"),
                        "link": question.get("link"),
                        "answers": []
                    }
                    
                    # Get answers if available
                    for answer in question.get("answers", []):
                        answer_body = html.unescape(answer.get("body", ""))
                        item["answers"].append({
                            "id": answer.get("answer_id"),
                            "body": answer_body,
                            "score": answer.get("score", 0),
                            "is_accepted": answer.get("is_accepted", False),
                            "creation_date": answer.get("creation_date")
                        })
                        
                    results["items"].append(item)
            
            # Handle case with query only (no tags) or content types other than questions
            elif content_type == "questions":
                # Determine API endpoint
                endpoint = f"{self.base_url}/questions"
                params["pagesize"] = max_items
                # Add additional parameters for questions
                params["filter"] = "!-*jbN-o8P3E5"  # Include body, answers, comments
                
                # Make the API request
                response = await self.client.get(endpoint, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                # Process items based on content type
                for question in data.get("items", []):
                    # Unescape HTML entities in text fields
                    title = html.unescape(question.get("title", ""))
                    body = html.unescape(question.get("body", ""))
                    
                    item = {
                        "type": "question",
                        "id": question.get("question_id"),
                        "title": title,
                        "body": body,
                        "tags": question.get("tags", []),
                        "score": question.get("score", 0),
                        "view_count": question.get("view_count", 0),
                        "answer_count": question.get("answer_count", 0),
                        "is_answered": question.get("is_answered", False),
                        "creation_date": question.get("creation_date"),
                        "link": question.get("link"),
                        "answers": []
                    }
                    
                    # Get answers if available
                    for answer in question.get("answers", []):
                        answer_body = html.unescape(answer.get("body", ""))
                        item["answers"].append({
                            "id": answer.get("answer_id"),
                            "body": answer_body,
                            "score": answer.get("score", 0),
                            "is_accepted": answer.get("is_accepted", False),
                            "creation_date": answer.get("creation_date")
                        })
                        
                    results["items"].append(item)
            elif content_type == "answers":
                # OR functionality for tags in answers mode
                if tags:
                    seen_answer_ids = set()  # Track IDs to avoid duplicates
                    all_answers = []
                    
                    # Calculate items per tag - distribute evenly but ensure we get some results
                    per_tag_pagesize = max(1, min(max_items, 30))  # At most 30 per tag to avoid excessive API calls
                    
                    # Make a separate API call for each tag to get questions first
                    for tag in tags:
                        tag_params = params.copy()
                        tag_params["tagged"] = tag  # Single tag
                        tag_params["pagesize"] = per_tag_pagesize
                        tag_params["filter"] = "!9Z(-wzu0T"  # Just get question IDs
                        
                        logger.info(f"Fetching Stack Overflow questions for tag: {tag}")
                        
                        try:
                            # First get questions for this tag
                            question_response = await self.client.get(
                                f"{self.base_url}/questions",
                                params=tag_params
                            )
                            question_response.raise_for_status()
                            
                            question_data = question_response.json()
                            question_ids = [q["question_id"] for q in question_data.get("items", [])]
                            
                            if question_ids:
                                # Now get answers for these questions
                                answer_params = params.copy()
                                answer_params["filter"] = "!9Z(-wzftf"  # Include body in answers
                                
                                answer_response = await self.client.get(
                                    f"{self.base_url}/questions/{';'.join(map(str, question_ids))}/answers", 
                                    params=answer_params
                                )
                                answer_response.raise_for_status()
                                
                                answer_data = answer_response.json()
                                
                                # Add unique answers to our collection
                                for answer in answer_data.get("items", []):
                                    answer_id = answer.get("answer_id")
                                    if answer_id and answer_id not in seen_answer_ids:
                                        seen_answer_ids.add(answer_id)
                                        all_answers.append(answer)
                                        
                                        # Stop if we've reached the max_items limit
                                        if len(all_answers) >= max_items:
                                            break
                        except Exception as e:
                            logger.warning(f"Error fetching answers for tag {tag}: {str(e)}")
                            # Continue with other tags even if one fails
                    
                    # Score and sort the collected answers
                    logger.info(f"Scoring {len(all_answers)} unique answers from {len(tags)} tags")
                    
                    # Calculate relevance score for each answer
                    scored_answers = []
                    for answer in all_answers:
                        # Base score starts with the answer score (upvotes)
                        score = answer.get("score", 0) * 2  # Weight upvotes highly
                        
                        # Boost answers with high-scoring questions
                        question_id = answer.get("question_id")
                        question_response = await self.client.get(
                            f"{self.base_url}/questions/{question_id}",
                            params={"filter": "!-*jbN-o8P3E5"}  # Include body, answers, comments
                        )
                        question_response.raise_for_status()
                        question_data = question_response.json()
                        question = question_data.get("items", [{}])[0]
                        score += question.get("score", 0)  # Boost for question score
                        
                        # Boost answers with code samples (approximated by code tags in body)
                        body = answer.get("body", "")
                        if "<code>" in body:
                            score += 50  # Boost for having code examples
                            # More code blocks = better examples
                            code_block_count = body.count("<code>")
                            score += min(code_block_count * 10, 50)  # Cap at +50
                        
                        # Boost for answer count (more answers = more perspectives)
                        answer_count = question.get("answer_count", 0)
                        score += min(answer_count * 10, 50)  # Cap at +50
                        
                        # Boost for view count (popular = likely useful)
                        view_count = question.get("view_count", 0)
                        score += min(view_count // 100, 30)  # Cap at +30
                        
                        # Check for tag matches in the question tags
                        question_tags = question.get("tags", [])
                        for tag in tags:
                            if tag.lower() in [qt.lower() for qt in question_tags]:
                                score += 40  # Boost for each matching tag
                        
                        # Penalize extremely long answers slightly to favor concise examples
                        body_length = len(body)
                        if body_length > 10000:
                            score -= 20
                        
                        scored_answers.append((score, answer))
                    
                    # Sort by score descending
                    scored_answers.sort(reverse=True, key=lambda x: x[0])
                    
                    # Log scores for visibility
                    logger.info(f"Top answer scores: {[score for score, _ in scored_answers[:5]]}")
                    
                    # Take top scoring answers up to max_items
                    all_answers = [answer for _, answer in scored_answers[:max_items]]
                    
                    # Process answers
                    for answer in all_answers:
                        body = html.unescape(answer.get("body", ""))
                        
                        item = {
                            "type": "answer",
                            "id": answer.get("answer_id"),
                            "question_id": answer.get("question_id"),
                            "body": body,
                            "score": answer.get("score", 0),
                            "is_accepted": answer.get("is_accepted", False),
                            "creation_date": answer.get("creation_date")
                        }
                        
                        results["items"].append(item)
                else:
                    # Handle case with query but no tags for answers
                    # We first need to get question IDs
                    question_params = params.copy()
                    question_params["pagesize"] = max_items
                    question_params["filter"] = "!9Z(-wzu0T"  # Just get question IDs
                    
                    question_response = await self.client.get(
                        f"{self.base_url}/questions", 
                        params=question_params
                    )
                    question_response.raise_for_status()
                    
                    question_data = question_response.json()
                    question_ids = [q["question_id"] for q in question_data.get("items", [])]
                    
                    if not question_ids:
                        return results
                        
                    # Now get answers for these questions
                    endpoint = f"{self.base_url}/questions/{';'.join(map(str, question_ids))}/answers"
                    params["pagesize"] = max_items
                    params["filter"] = "!9Z(-wzftf"  # Include body in answers
                    
                    response = await self.client.get(endpoint, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    # Process answers
                    for answer in data.get("items", []):                        
                        body = html.unescape(answer.get("body", ""))
                    
                    results["items"].append({
                        "type": "answer",
                        "id": answer.get("answer_id"),
                        "question_id": answer.get("question_id"),
                        "body": body,
                        "score": answer.get("score", 0),
                        "is_accepted": answer.get("is_accepted", False),
                        "creation_date": answer.get("creation_date"),
                        "link": answer.get("link")
                    })
                    
            logger.info(f"Successfully fetched {len(results['items'])} {content_type} from Stack Overflow")
            return results
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Stack Overflow API error: {e.response.status_code} - {e.response.text}")
            raise ContentSourceError(f"Stack Overflow API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Failed to fetch Stack Overflow content: {str(e)}")
            raise ContentSourceError(f"Stack Overflow content fetch failed: {str(e)}")
    
    async def process_content(self, raw_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw Stack Overflow content into a normalized format optimized for AI comprehension.
        Extracts key semantic information and structures content for better problem generation.
        
        Args:
            raw_content: Raw content from the fetch_content method
            
        Returns:
            Processed content with extracted text and metadata
        """
        content_type = raw_content.get("content_type", "")
        items = raw_content.get("items", [])
        tags = raw_content.get("tags", [])
        query = raw_content.get("query", "")
        
        search_context = tags or query
        tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
        
        processed_result = {
            "source": "stackoverflow",
            "content_type": content_type,
            "search_context": search_context,
            "extracted_content": "",
            "metadata": {
                "item_count": len(items),
                "content_summary": f"Stack Overflow {content_type} for {tags_str or query}",
                "tags": tags
            }
        }
        
        # Add an overview summary at the beginning for context
        extracted_text = [
            f"# Stack Overflow Content Overview\n"
            f"## Search Context: {tags_str or query}\n"
            f"## Number of Items: {len(items)}\n"
            f"## Content Type: {content_type}\n"
            f"\nThe following are high-quality programming examples from Stack Overflow related to {tags_str or query}.\n"
            f"Each section represents a question with its accepted or highest-voted answers.\n\n"
        ]
        
        # Process items with enhanced structure and code extraction
        for item in items:
            if content_type == "questions" and item.get("type") == "question":
                # Extract all code blocks from question for reference
                body = item.get("body", "")
                code_blocks = self._extract_code_blocks(body)
                code_block_summary = ""
                if code_blocks:
                    code_block_summary = (f"\n### Question contains {len(code_blocks)} code block(s)\n"
                                         f"Most relevant code examples:\n```\n"
                                         f"{code_blocks[0] if code_blocks else ''}\n```\n")
                
                # Structure question with semantic sections
                question_text = (
                    f"---\n"
                    f"## QUESTION: {item['title']}\n"
                    f"* Tags: {', '.join(item['tags'])}\n"
                    f"* Score: {item['score']}\n"
                    f"* View Count: {item.get('view_count', 'N/A')}\n"
                    f"* Answer Count: {item.get('answer_count', 0)}\n"
                    f"* Link: {item.get('link', '')}\n\n"
                    f"### Question Content:\n"
                    f"{self._clean_html(body)}\n"
                    f"{code_block_summary}\n"
                )
                
                # Find the accepted answer and highest scored answers
                answers = sorted(
                    item.get("answers", []),
                    key=lambda a: (not a.get("is_accepted"), -a.get("score", 0))
                )
                
                # Process up to 3 top answers (accepted + 2 highest scored)
                top_answers = answers[:3] if len(answers) > 3 else answers
                
                for i, answer in enumerate(top_answers):
                    answer_body = answer.get("body", "")
                    answer_code_blocks = self._extract_code_blocks(answer_body)
                    
                    # Mark accepted answers prominently
                    acceptance = "✓ ACCEPTED SOLUTION" if answer.get("is_accepted") else f"Answer #{i+1}"
                    
                    # Include code blocks separately for clarity
                    code_summary = ""
                    if answer_code_blocks:
                        code_summary = f"\n#### Answer Code Examples:\n```\n{answer_code_blocks[0]}\n```\n"
                        if len(answer_code_blocks) > 1:
                            code_summary += f"\n```\n{answer_code_blocks[1]}\n```\n"
                    
                    answer_text = (
                        f"### {acceptance} (Score: {answer['score']})\n"
                        f"{self._clean_html(answer_body)}\n"
                        f"{code_summary}\n"
                    )
                    question_text += answer_text
                
                # Add a summary section at the end of each question
                has_accepted = any(ans.get("is_accepted") for ans in answers)
                summary = (f"\n### Key Points:\n"
                          f"* Question has {len(answers)} answer(s)\n"
                          f"* Contains {'an accepted' if has_accepted else 'no accepted'} answer\n"
                          f"* Top answer score: {answers[0].get('score', 0) if answers else 'N/A'}\n\n")
                
                question_text += summary
                extracted_text.append(question_text)
                
            elif content_type == "answers" and item.get("type") == "answer":
                # Extract code blocks from answer
                answer_body = item.get("body", "")
                code_blocks = self._extract_code_blocks(answer_body)
                
                code_summary = ""
                if code_blocks:
                    code_summary = (f"\n### Code Examples:\n```\n"
                                    f"{code_blocks[0]}\n```\n")
                    if len(code_blocks) > 1:
                        code_summary += f"\n```\n{code_blocks[1]}\n```\n"
                
                # Structure answer with semantic sections
                answer_text = (
                    f"---\n"
                    f"## ANSWER (ID: {item['id']}, Question ID: {item['question_id']})\n"
                    f"* Score: {item['score']}\n"
                    f"* Accepted: {'Yes ✓' if item['is_accepted'] else 'No'}\n\n"
                    f"### Answer Content:\n"
                    f"{self._clean_html(answer_body)}\n"
                    f"{code_summary}\n"
                )
                extracted_text.append(answer_text)
        
        processed_result["extracted_content"] = "\n".join(extracted_text)
        
        logger.info(f"Processed {len(items)} items from Stack Overflow with enhanced structure")
        return processed_result
        
    def _extract_code_blocks(self, html_content: str) -> List[str]:
        """
        Extract code blocks from HTML content.
        
        Args:
            html_content: Raw HTML content to extract code from
            
        Returns:
            List of extracted code blocks
        """
        import re
        code_blocks = []
        
        # Extract content between <code> tags
        code_pattern = re.compile(r'<code>(.*?)</code>', re.DOTALL)
        matches = code_pattern.findall(html_content)
        
        # Filter out very short code blocks (likely inline code)
        for match in matches:
            match = html.unescape(match)  # Handle HTML entities within code blocks
            if len(match.strip()) > 15:  # Only include substantive code blocks
                code_blocks.append(match.strip())
                
        # Also extract from <pre> tags which often contain larger code blocks
        pre_pattern = re.compile(r'<pre>(.*?)</pre>', re.DOTALL)
        pre_matches = pre_pattern.findall(html_content)
        
        for match in pre_matches:
            # Remove nested <code> tags if present within <pre>
            cleaned_match = re.sub(r'</?code>', '', match)
            cleaned_match = html.unescape(cleaned_match)  # Handle HTML entities
            if len(cleaned_match.strip()) > 15 and cleaned_match.strip() not in code_blocks:
                code_blocks.append(cleaned_match.strip())
                
        return code_blocks
    
    async def _fetch_combined_tags_questions(self, tags: List[str], params: Dict[str, Any], max_items: int) -> List[Dict[str, Any]]:
        """
        Fetch questions using AND logic (all tags must be present) by combining them with semicolons.
        
        Args:
            tags: List of tags to combine with AND logic
            params: Base parameters for API request
            max_items: Maximum number of items to fetch
            
        Returns:
            List of questions matching all specified tags
        """
        if not tags:
            return []
            
        combined_tags = ";".join(tags)  # Combined tags with semicolons = AND operation
        and_params = params.copy()
        and_params["tagged"] = combined_tags
        and_params["pagesize"] = max_items
        and_params["filter"] = "!-*jbN-o8P3E5"  # Include body, answers, comments
        
        logger.info(f"Fetching Stack Overflow content with AND tags: {combined_tags}")
        
        try:
            # Make the API request for combined tags (AND operation)
            response = await self.client.get(f"{self.base_url}/questions", params=and_params)
            response.raise_for_status()
            
            data = response.json()
            questions = data.get("items", [])
            
            logger.info(f"AND operation found {len(questions)} questions matching all tags")
            return questions
        except Exception as e:
            logger.warning(f"Error fetching with combined tags: {str(e)}")
            return []  # Return empty list on error to continue with OR approach
    
    async def _fetch_separate_tags_questions(self, tags: List[str], params: Dict[str, Any], max_items: int) -> List[Dict[str, Any]]:
        """
        Fetch questions using OR logic (any tag may be present) by making separate API calls.
        
        Args:
            tags: List of tags to query separately with OR logic
            params: Base parameters for API request
            max_items: Maximum number of items to fetch
            
        Returns:
            List of questions matching any of the specified tags
        """
        if not tags:
            return []
            
        seen_question_ids = set()  # Track IDs to avoid duplicates
        all_questions = []
        
        # Calculate items per tag - distribute evenly but ensure we get some results
        per_tag_pagesize = max(1, min(max_items, 30))  # At most 30 per tag to avoid excessive API calls
        
        # Make a separate API call for each tag
        for tag in tags:
            tag_params = params.copy()
            tag_params["tagged"] = tag  # Single tag
            tag_params["pagesize"] = per_tag_pagesize
            
            # Add parameters specific to questions endpoint
            tag_params["filter"] = "!-*jbN-o8P3E5"  # Include body, answers, comments
            
            logger.info(f"Fetching Stack Overflow content for tag: {tag}")
            
            try:
                # Make the API request for this specific tag
                response = await self.client.get(f"{self.base_url}/questions", params=tag_params)
                response.raise_for_status()
                
                data = response.json()
                
                # Add unique questions to our collection
                for question in data.get("items", []):
                    question_id = question.get("question_id")
                    if question_id and question_id not in seen_question_ids:
                        seen_question_ids.add(question_id)
                        all_questions.append(question)
                        
                        # Stop if we've reached the max_items limit
                        if len(all_questions) >= max_items:
                            break
            except Exception as e:
                logger.warning(f"Error fetching tag {tag}: {str(e)}")
                # Continue with other tags even if one fails
        
        logger.info(f"OR operation found {len(all_questions)} unique questions from {len(tags)} tags")
        return all_questions
    
    def _clean_html(self, html_content: str) -> str:
        """
        Basic cleaning of HTML content to extract text.
        For production, use a proper HTML parser like BeautifulSoup.
        """
        import re
        
        # For now just do some basic replacements
        text = re.sub(r'<code>(.*?)</code>', r'`\1`', html_content, flags=re.DOTALL)
        text = re.sub(r'<pre>(.*?)</pre>', r'```\n\1\n```', text, flags=re.DOTALL)
        text = re.sub(r'<h\d>(.*?)</h\d>', r'\n## \1\n', text, flags=re.DOTALL)
        text = re.sub(r'<p>(.*?)</p>', r'\n\1\n', text, flags=re.DOTALL)
        text = re.sub(r'<.*?>', ' ', text)  # Remove remaining HTML tags
        text = re.sub(r'\s+', ' ', text)    # Normalize whitespace
        
        # Remove filler words and phrases
        filler_phrases = [
            r'\bI think\b', r'\bIn my opinion\b', r'\bbasically\b', r'\bjust\b', 
            r'\bactually\b', r'\byou know\b', r'\bkind of\b', r'\bsort of\b',
            r'\bto be honest\b', r'\bto tell you the truth\b', r'\bas a matter of fact\b',
            r'\bI mean\b', r'\blike\b', r'\bI guess\b', r'\bor something\b',
            r'\bor whatever\b', r'\bus guys\b', r'\bI believe\b', r'\bliterally\b',
            r'\banyway\b', r'\banyhow\b', r'\bso yeah\b', r'\bas I said\b',
            r'\bI would say\b', r'\bat the end of the day\b'
        ]
        
        for phrase in filler_phrases:
            text = re.sub(phrase, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
