"""
Google Gemini AI provider implementation.
"""
import json
import google.generativeai as genai
from typing import Dict, List, Any, Optional, Union
from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai_providers.base import BaseAIProvider, AIPlatformError

logger = get_logger()


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the Gemini provider.
        
        Args:
            api_key: Gemini API key (defaults to settings)
            model: Gemini model to use (defaults to settings or 'gemini-1.5-pro')
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL or "gemini-1.5-pro"  # Updated to use the newer model version
        self.client = None
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize the Gemini client."""
        if self.is_initialized:
            return
            
        try:
            # Configure the Gemini API
            genai.configure(api_key=self.api_key)
            
            # List available models for reference and validation
            models = genai.list_models()
            available_models = [model.name for model in models]
            logger.info(f"Available Gemini models: {available_models}")
            
            # Ensure model name has the "models/" prefix for API compatibility
            model_name = self.model
            exact_match = f"models/{model_name}" if not model_name.startswith("models/") else model_name
            
            # Check if our model is directly available
            if exact_match in available_models:
                model_name = exact_match
                logger.info(f"Found exact model match: {model_name}")
            else:
                # Try to find a similar model if exact match is not available
                # Look for models that contain our requested model name (without version specifics)
                base_name = self.model.split("-")[0]  # Get base name (e.g., 'gemini' from 'gemini-1.5-pro')
                candidates = [m for m in available_models if base_name in m and 'pro' in m]
                
                if candidates:
                    # Sort to get the latest version (assuming versioning in name)
                    # Prefer models with the closest name to what we requested
                    closest_match = sorted(candidates, key=lambda x: (len(x.split("-")), x), reverse=True)[0]
                    model_name = closest_match
                    logger.info(f"Using closest model match: {model_name} (instead of {exact_match})")
                else:
                    # If all else fails, use the first gemini model available
                    gemini_models = [m for m in available_models if "gemini" in m]
                    if gemini_models:
                        model_name = gemini_models[0]
                        logger.info(f"Falling back to available Gemini model: {model_name}")
                    else:
                        # No gemini models available, raise error
                        raise AIPlatformError(f"No suitable Gemini models found among available models: {available_models}")
            
            logger.info(f"Initializing Gemini with model: {model_name} (from env: {settings.GEMINI_MODEL})")
            self.client = genai.GenerativeModel(model_name)
            self.is_initialized = True
            logger.info(f"Gemini AI provider successfully initialized with model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {str(e)}")
            raise AIPlatformError(f"Gemini initialization failed: {str(e)}")

    
    async def generate_problems(self, 
                               source_data: Dict[str, Any], 
                               num_problems: int = 3,
                               temperature: float = 0.7) -> List[Dict[str, Any]]:
        """Generate coding problems based on source data."""
        if not self.is_initialized:
            await self.initialize()
        
        # Prepare source data sections
        github_data = source_data.get("github", "No GitHub data available")
        stackoverflow_data = source_data.get("stackoverflow", "No Stack Overflow data available")
        
        # Create prompt for problem generation
        prompt = f"""
        Based on the following information from GitHub and Stack Overflow:
        
        ## GitHub Data:
        {github_data}
        
        ## Stack Overflow Data:
        {stackoverflow_data}
        
        Generate {num_problems} unique coding problems. For each problem, provide:
        1. A clear, concise title
        2. A detailed description including background, requirements and constraints
        3. A difficulty level (easy, medium, or hard)
        4. An example input and output
        5. A complete solution in Python
        6. 3-5 relevant tags that categorize the problem (e.g., "arrays", "dynamic-programming", "trees")
        
        Format the response as a JSON array where each object has these fields: 
        "title", "description", "difficulty_level", "solution", "tags"
        
        Make sure each problem is self-contained, clearly stated, and challenging but solvable.
        """
        
        try:
            generation_config = {
                "temperature": temperature,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
            
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
            
            # Make the API call to Gemini
            response = await self.client.generate_content_async(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            logger.debug(f"Gemini response: {response.text}")
            
            # Parse the JSON response
            response_text = response.text
            # Sometimes the model outputs markdown codeblocks, extract the JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
                
            # Parse JSON response
            problems = json.loads(response_text)
            logger.info(f"Successfully generated {len(problems)} problems with Gemini")
            
            # Validate format
            for problem in problems:
                # Ensure all required fields are present
                required_fields = ["title", "description", "difficulty_level", "solution", "tags"]
                for field in required_fields:
                    if field not in problem:
                        problem[field] = ""
                        logger.warning(f"Missing field '{field}' in generated problem")
                        
                # Normalize difficulty level
                if problem["difficulty_level"].lower() not in ["easy", "medium", "hard"]:
                    problem["difficulty_level"] = "medium"
                    logger.warning(f"Normalized invalid difficulty level for problem: {problem['title']}")
                else:
                    problem["difficulty_level"] = problem["difficulty_level"].lower()
            
            return problems
            
        except Exception as e:
            logger.error(f"Failed to generate problems with Gemini: {str(e)}")
            raise AIPlatformError(f"Problem generation failed: {str(e)}")
    
    async def validate_problem(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a generated problem for quality and completeness."""
        if not self.is_initialized:
            await self.initialize()
            
        prompt = f"""
        Evaluate and improve the following coding problem:
        
        Title: {problem.get('title', 'No title')}
        Difficulty: {problem.get('difficulty_level', 'medium')}
        Description: {problem.get('description', 'No description')}
        Solution: {problem.get('solution', 'No solution')}
        Tags: {', '.join(problem.get('tags', []))}
        
        Please evaluate this problem and provide:
        1. A quality assessment (scale 1-10)
        2. Specific improvements to the problem description, if needed
        3. Verification that the solution correctly solves the problem
        4. Any suggested tag corrections
        
        Return the results in this JSON format:
        {{
            "quality_score": (1-10),
            "improved_description": "improved description text", 
            "solution_valid": true/false,
            "improved_tags": ["tag1", "tag2", ...],
            "validation_notes": "explanation of issues or improvements"
        }}
        """
        
        try:
            response = await self.client.generate_content_async(prompt)
            
            # Parse the JSON response
            response_text = response.text
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
                
            validation_results = json.loads(response_text)
            
            # Update the problem with improvements if quality is acceptable
            if validation_results.get("quality_score", 0) >= 7:
                if validation_results.get("improved_description"):
                    problem["description"] = validation_results["improved_description"]
                    
                if validation_results.get("improved_tags"):
                    problem["tags"] = validation_results["improved_tags"]
                    
            return {
                "problem": problem,
                "validation_results": validation_results,
                "passed_validation": validation_results.get("quality_score", 0) >= 6 and 
                                    validation_results.get("solution_valid", False)
            }
            
        except Exception as e:
            logger.error(f"Failed to validate problem with Gemini: {str(e)}")
            raise AIPlatformError(f"Problem validation failed: {str(e)}")
    
    async def generate_test_cases(self, problem: Dict[str, Any], 
                                num_test_cases: int = 5) -> List[Dict[str, Any]]:
        """Generate test cases for a problem."""
        if not self.is_initialized:
            await self.initialize()
            
        prompt = f"""
        Create {num_test_cases} test cases for the following coding problem:
        
        Title: {problem.get('title', 'No title')}
        Description: {problem.get('description', 'No description')}
        
        For each test case, provide:
        1. Input values
        2. Expected output
        3. A brief explanation of what the test case is checking
        
        Format the response as a JSON array of test case objects.
        Each object should have: "input", "expected_output", and "explanation" fields.
        Make sure the test cases cover various scenarios including edge cases.
        """
        
        try:
            response = await self.client.generate_content_async(prompt)
            
            # Parse the JSON response
            response_text = response.text
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
                
            test_cases = json.loads(response_text)
            logger.info(f"Generated {len(test_cases)} test cases for problem: {problem.get('title')}")
            
            return test_cases
            
        except Exception as e:
            logger.error(f"Failed to generate test cases with Gemini: {str(e)}")
            raise AIPlatformError(f"Test case generation failed: {str(e)}")
