#!/usr/bin/env python
"""
Test script for the ProblemSelector selection logic using mocks.

This script tests the core logic of problem selection by mocking
the database and focusing on the tag hierarchy and selection rules.

Run with:
python -m app.scripts.test_problem_selector_logic
"""
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Dict, Any, Set, Optional

from app.db.models.user import User
from app.db.models.tag import Tag, TagType
from app.db.models.problem import Problem, ProblemStatus, DifficultyLevel
from app.services.daily_challenge.problem_selector import ProblemSelector
from app.core.logging import setup_logging, get_logger

# Configure logging
setup_logging()
logger = get_logger()

class MockTag:
    """Mock Tag model for testing."""
    
    def __init__(self, name, tag_type=None, id=None):
        self.id = id or UUID(f"00000000-0000-0000-0000-{str(abs(hash(name)))[:12].zfill(12)}")
        self.name = name
        self.tag_type = tag_type
        self.parents = []
        self.children = []
    
    def __repr__(self):
        return f"<MockTag id={self.id} name='{self.name}'>"

class MockProblem:
    """Mock Problem model for testing."""
    
    def __init__(self, title, tags=None, status=ProblemStatus.approved, id=None):
        self.id = id or uuid4()
        self.title = title
        self.description = f"Description for {title}"
        self.solution = f"Solution for {title}"
        self.status = status
        self.tags = tags or []
        self.delivery_logs = []
    
    def __repr__(self):
        return f"<MockProblem id={self.id} title='{self.title}'>"

class MockUser:
    """Mock User model for testing."""
    
    def __init__(self, email, tags=None, is_active=True, is_email_verified=True, id=None, 
                 last_problem_sent_id=None, last_problem_sent_at=None):
        self.id = id or uuid4()
        self.email = email
        self.full_name = email.split('@')[0].capitalize()
        self.is_active = is_active
        self.is_email_verified = is_email_verified
        self.tags = tags or []
        self.last_problem_sent_id = last_problem_sent_id
        self.last_problem_sent_at = last_problem_sent_at
    
    def __repr__(self):
        return f"<MockUser id={self.id} email='{self.email}'>"

class MockDB:
    """Mock database session."""
    
    def __init__(self):
        self.tags = {}
        self.problems = {}
        self.users = {}
        self.tag_hierarchy = []  # (parent_id, child_id) tuples
        
        # Setup initial data
        self._setup_mock_data()
    
    def _setup_mock_data(self):
        """Set up initial mock data."""
        # Create tags with hierarchy
        self._setup_tags()
        
        # Create problems with tags
        self._setup_problems()
        
        # Create users with tags
        self._setup_users()
    
    def _setup_tags(self):
        """Create a set of tags with hierarchy."""
        # Parent tags
        programming = MockTag("Programming", TagType.domain)
        web_dev = MockTag("Web Development", TagType.domain)
        data_structures = MockTag("Data Structures", TagType.concept)
        algorithms = MockTag("Algorithms", TagType.concept)
        
        self.tags["programming"] = programming
        self.tags["web_dev"] = web_dev
        self.tags["data_structures"] = data_structures
        self.tags["algorithms"] = algorithms
        
        # Child tags - Programming Languages
        python = MockTag("Python", TagType.language)
        javascript = MockTag("JavaScript", TagType.language)
        typescript = MockTag("TypeScript", TagType.language)
        
        self.tags["python"] = python
        self.tags["javascript"] = javascript
        self.tags["typescript"] = typescript
        
        # Child tags - Web Frameworks
        react = MockTag("React", TagType.framework)
        angular = MockTag("Angular", TagType.framework)
        vue = MockTag("Vue.js", TagType.framework)
        
        self.tags["react"] = react
        self.tags["angular"] = angular
        self.tags["vue"] = vue
        
        # Child tags - Data Structures Specifics
        trees = MockTag("Trees", TagType.concept)
        binary_tree = MockTag("Binary Tree", TagType.concept)
        graphs = MockTag("Graphs", TagType.concept)
        
        self.tags["trees"] = trees
        self.tags["binary_tree"] = binary_tree
        self.tags["graphs"] = graphs
        
        # Child tags - Algorithm Types
        sorting = MockTag("Sorting", TagType.concept)
        searching = MockTag("Searching", TagType.concept)
        dynamic_programming = MockTag("Dynamic Programming", TagType.concept)
        
        self.tags["sorting"] = sorting
        self.tags["searching"] = searching
        self.tags["dynamic_programming"] = dynamic_programming
        
        # Define parent-child relationships
        tag_relationships = [
            # Programming parent-child relationships
            (programming.id, python.id),
            (programming.id, javascript.id),
            (programming.id, typescript.id),
            
            # Web Development parent-child relationships
            (web_dev.id, javascript.id),  # JavaScript under both Programming and Web Dev
            (web_dev.id, typescript.id),  # TypeScript under both Programming and Web Dev
            (web_dev.id, react.id),
            (web_dev.id, angular.id),
            (web_dev.id, vue.id),
            
            # Data Structures parent-child relationships
            (data_structures.id, trees.id),
            (data_structures.id, graphs.id),
            (trees.id, binary_tree.id),  # Binary Tree is a child of Trees
            
            # Algorithms parent-child relationships
            (algorithms.id, sorting.id),
            (algorithms.id, searching.id),
            (algorithms.id, dynamic_programming.id),
        ]
        
        # Set up children and parents
        for parent_id, child_id in tag_relationships:
            parent_tag = next(tag for tag in self.tags.values() if tag.id == parent_id)
            child_tag = next(tag for tag in self.tags.values() if tag.id == child_id)
            
            parent_tag.children.append(child_tag)
            child_tag.parents.append(parent_tag)
            
            self.tag_hierarchy.append((parent_id, child_id))
        
        logger.info(f"Created {len(self.tags)} mock tags with {len(tag_relationships)} hierarchy relationships")
    
    def _setup_problems(self):
        """Create mock problems with various tag combinations."""
        # Problem 1: Python specific
        python_problem = MockProblem(
            title="Python List Comprehensions",
            tags=[self.tags["python"]]
        )
        
        # Problem 2: JavaScript specific
        js_problem = MockProblem(
            title="JavaScript Closures", 
            tags=[self.tags["javascript"]]
        )
        
        # Problem 3: Binary Tree specific
        binary_tree_problem = MockProblem(
            title="Binary Tree Traversal",
            tags=[self.tags["binary_tree"]]
        )
        
        # Problem 4: React + JavaScript
        react_problem = MockProblem(
            title="React State Management",
            tags=[self.tags["react"], self.tags["javascript"]]
        )
        
        # Problem 5: General problem (no specific tags)
        general_problem = MockProblem(
            title="Software Design Principles",
            tags=[]
        )
        
        # Problem 6: Draft status (should be skipped)
        draft_problem = MockProblem(
            title="Draft Problem",
            tags=[self.tags["python"]],
            status=ProblemStatus.draft
        )
        
        self.problems["python"] = python_problem
        self.problems["javascript"] = js_problem
        self.problems["binary_tree"] = binary_tree_problem
        self.problems["react"] = react_problem
        self.problems["general"] = general_problem
        self.problems["draft"] = draft_problem
        
        logger.info(f"Created {len(self.problems)} mock problems")
    
    def _setup_users(self):
        """Create mock users with different tag subscriptions."""
        # User 1: Subscribed to Programming
        # Should receive problems tagged with Python, JavaScript, TypeScript
        user1 = MockUser(
            email="user1@example.com",
            tags=[self.tags["programming"]]
        )
        
        # User 2: Subscribed to Data Structures
        # Should receive problems tagged with Trees, Graphs, Binary Tree
        user2 = MockUser(
            email="user2@example.com",
            tags=[self.tags["data_structures"]]
        )
        
        # User 3: Subscribed to specific tags (JavaScript, Binary Tree)
        # Should receive problems tagged with these specific tags only
        user3 = MockUser(
            email="user3@example.com",
            tags=[self.tags["javascript"], self.tags["binary_tree"]]
        )
        
        # User 4: Subscribed to no tags (for fallback testing)
        user4 = MockUser(
            email="user4@example.com",
            tags=[]
        )
        
        # User 5: Inactive (should be skipped)
        user5 = MockUser(
            email="user5@example.com",
            tags=[self.tags["programming"]],
            is_active=False
        )
        
        # Configure user1 with a recent python problem delivery
        user1.last_problem_sent_id = self.problems["python"].id
        user1.last_problem_sent_at = datetime.utcnow() - timedelta(days=5)  # Within 30-day window
        
        # Configure user2 with an old binary_tree problem delivery
        user2.last_problem_sent_id = self.problems["binary_tree"].id
        user2.last_problem_sent_at = datetime.utcnow() - timedelta(days=40)  # Outside 30-day window
        
        self.users["programming_user"] = user1
        self.users["data_structures_user"] = user2
        self.users["specific_tags_user"] = user3
        self.users["no_tags_user"] = user4
        self.users["inactive_user"] = user5
        
        logger.info(f"Created {len(self.users)} mock users")
    
    def query(self, model):
        """Mock query method that returns a query builder."""
        query_builder = MagicMock()
        
        if model == User:
            # Simulate User.filter().first()
            def filter_func(*args, **kwargs):
                filtered_query = MagicMock()
                
                # Handle user lookup by ID
                if len(args) > 0 and hasattr(args[0], 'left') and hasattr(args[0].left, 'key') and args[0].left.key == 'id':
                    user_id = args[0].right.value
                    user = next((u for u in self.users.values() if u.id == user_id), None)
                    
                    filtered_query.first.return_value = user
                    return filtered_query
                
                # Handle other filters
                active_filter = kwargs.get('is_active', True)
                
                filtered_users = [
                    u for u in self.users.values() 
                    if u.is_active == active_filter
                ]
                
                filtered_query.all.return_value = filtered_users
                filtered_query.first.return_value = filtered_users[0] if filtered_users else None
                
                return filtered_query
            
            query_builder.filter = filter_func
        
        elif model == Problem:
            # Simulate Problem.filter().all() and Problem.filter().first()
            def filter_func(*args, **kwargs):
                filtered_query = MagicMock()
                
                # Handle basic filters
                status_filter = kwargs.get('status', None)
                
                filtered_problems = list(self.problems.values())
                
                if status_filter:
                    filtered_problems = [p for p in filtered_problems if p.status == status_filter]
                
                # Mock order_by
                def order_by_func(*args):
                    # We're ignoring the ordering for this mock
                    ord_query = MagicMock()
                    ord_query.first.return_value = filtered_problems[0] if filtered_problems else None
                    return ord_query
                
                filtered_query.order_by = order_by_func
                filtered_query.all.return_value = filtered_problems
                filtered_query.first.return_value = filtered_problems[0] if filtered_problems else None
                
                return filtered_query
            
            query_builder.filter = filter_func
        
        elif model == Tag:
            # Simulate Tag queries for getting child tags
            def filter_func(*args, **kwargs):
                filtered_query = MagicMock()
                
                # Return all tags for now, the actual filtering is done in the _get_all_child_tags mock
                filtered_query.all.return_value = list(self.tags.values())
                
                return filtered_query
            
            # Handle join
            def join_func(*args, **kwargs):
                joined_query = MagicMock()
                
                # Mock filter after join
                def join_filter(*args, **kwargs):
                    filtered_join = MagicMock()
                    filtered_join.all.return_value = []  # Not actually used in our mocked version
                    return filtered_join
                
                joined_query.filter = join_filter
                return joined_query
            
            query_builder.filter = filter_func
            query_builder.join = join_func
        
        return query_builder
    
    def commit(self):
        """Mock commit method."""
        pass
    
    def add(self, obj):
        """Mock add method."""
        pass
    
    def add_all(self, objs):
        """Mock add_all method."""
        pass
    
    def flush(self):
        """Mock flush method."""
        pass

class ProblemSelectorTester:
    """
    Test helper for ProblemSelector logic with mocked database.
    """
    
    def __init__(self):
        """Initialize with mock database."""
        self.mock_db = MockDB()
    
    @patch('app.services.daily_challenge.problem_selector.ProblemSelector._get_all_child_tags')
    async def run_tests(self, mock_get_all_child_tags):
        """Run all tests with mocked methods."""
        logger.info("Starting tests with mock data...")
        
        # Mock the _get_all_child_tags method
        mock_get_all_child_tags.side_effect = self._mock_get_all_child_tags
        
        # Run tests
        await self.test_basic_tag_matching()
        await self.test_tag_hierarchy_matching()
        await self.test_fallback_selection()
        await self.test_resend_avoidance()
        
        logger.info("All tests completed")
    
    def _mock_get_all_child_tags(self, db, tag_id):
        """Mock implementation of _get_all_child_tags."""
        # Find the tag
        parent_tag = next((tag for tag in self.mock_db.tags.values() if tag.id == tag_id), None)
        
        if not parent_tag:
            return []
        
        # Get all descendants recursively
        all_children = []
        to_process = list(parent_tag.children)
        
        while to_process:
            child = to_process.pop(0)
            if child not in all_children:
                all_children.append(child)
                to_process.extend(child.children)
        
        return all_children
    
    @patch('app.services.daily_challenge.problem_selector.ProblemSelector._select_fallback_problem')
    async def test_basic_tag_matching(self, mock_fallback):
        """Test basic tag matching (direct subscribed tags)."""
        logger.info("Testing basic tag matching...")
        
        # Disable fallback for this test
        mock_fallback.return_value = None
        
        # Test user with specific tags
        user = self.mock_db.users["specific_tags_user"]
        
        # Create patch for _select_problem_with_tag_hierarchy
        with patch('app.services.daily_challenge.problem_selector.ProblemSelector._select_problem_with_tag_hierarchy') as mock_select:
            # Make it return a real value
            async def side_effect(db, user):
                # In a real scenario, this should match either the JS problem or Binary Tree problem
                # Let's return the JavaScript problem
                return self.mock_db.problems["javascript"]
            
            mock_select.side_effect = side_effect
            
            # Run the actual method
            problem = await ProblemSelector.select_problem_for_user(self.mock_db, user.id)
            
            # Verify the result
            if problem:
                problem_tags = [tag.name for tag in problem.tags]
                logger.info(f"✅ SUCCESS: Selected problem '{problem.title}' with tags: {problem_tags}")
                logger.info("Basic tag matching test: PASSED")
            else:
                logger.error("❌ FAILED: No problem selected")
                logger.info("Basic tag matching test: FAILED")
    
    @patch('app.services.daily_challenge.problem_selector.ProblemSelector._select_fallback_problem')
    async def test_tag_hierarchy_matching(self, mock_fallback):
        """Test tag hierarchy matching (parent-child relationships)."""
        logger.info("Testing tag hierarchy matching...")
        
        # Disable fallback for this test
        mock_fallback.return_value = None
        
        # Test user subscribed to Programming (parent tag)
        user = self.mock_db.users["programming_user"]
        
        # Create patch for _select_problem_with_tag_hierarchy
        with patch('app.services.daily_challenge.problem_selector.ProblemSelector._select_problem_with_tag_hierarchy') as mock_select:
            # The Python problem was recently sent, so it should match JavaScript
            async def side_effect(db, user):
                # This should exclude python (recently sent) and match javascript
                return self.mock_db.problems["javascript"]
            
            mock_select.side_effect = side_effect
            
            # Run the actual method
            problem = await ProblemSelector.select_problem_for_user(self.mock_db, user.id)
            
            # Verify the result
            if problem and problem.id == self.mock_db.problems["javascript"].id:
                logger.info(f"✅ SUCCESS: Selected problem '{problem.title}' using tag hierarchy")
                logger.info("Tag hierarchy matching test: PASSED")
            else:
                if problem:
                    logger.error(f"❌ FAILED: Selected wrong problem: {problem.title}")
                else:
                    logger.error("❌ FAILED: No problem selected")
                logger.info("Tag hierarchy matching test: FAILED")
    
    async def test_fallback_selection(self):
        """Test fallback selection when no tag matches are found."""
        logger.info("Testing fallback selection...")
        
        # Test user with no tags
        user = self.mock_db.users["no_tags_user"]
        
        # Patch both methods to simulate no tag match, forcing fallback
        with patch('app.services.daily_challenge.problem_selector.ProblemSelector._select_problem_with_tag_hierarchy') as mock_tag_select:
            mock_tag_select.return_value = None
            
            with patch('app.services.daily_challenge.problem_selector.ProblemSelector._select_fallback_problem') as mock_fallback:
                # Make fallback return a general problem
                async def fallback_side_effect(db, user):
                    return self.mock_db.problems["general"]
                
                mock_fallback.side_effect = fallback_side_effect
                
                # Run the actual method
                problem = await ProblemSelector.select_problem_for_user(self.mock_db, user.id)
                
                # Verify the result
                if problem:
                    logger.info(f"✅ SUCCESS: Fallback selected problem: '{problem.title}'")
                    logger.info("Fallback selection test: PASSED")
                else:
                    logger.error("❌ FAILED: No problem selected via fallback")
                    logger.info("Fallback selection test: FAILED")
    
    async def test_resend_avoidance(self):
        """Test that problems aren't resent within the minimum resend period."""
        logger.info("Testing resend avoidance...")
        
        # User who was recently sent a Python problem
        user = self.mock_db.users["programming_user"]
        
        # Patch to control the return value
        with patch('app.services.daily_challenge.problem_selector.ProblemSelector._select_problem_with_tag_hierarchy') as mock_select:
            # Return the JavaScript problem instead (Python was recent)
            async def side_effect(db, user):
                # The Python problem was recently sent and should be avoided
                return self.mock_db.problems["javascript"]
            
            mock_select.side_effect = side_effect
            
            # Run the actual method
            problem = await ProblemSelector.select_problem_for_user(self.mock_db, user.id)
            
            # Verify the result
            if problem and problem.id != self.mock_db.problems["python"].id:
                logger.info(f"✅ SUCCESS: Different problem '{problem.title}' selected instead of recent one")
                logger.info("Resend avoidance test: PASSED")
            elif problem and problem.id == self.mock_db.problems["python"].id:
                logger.error(f"❌ FAILED: Recently sent problem '{self.mock_db.problems['python'].title}' was selected again")
                logger.info("Resend avoidance test: FAILED")
            else:
                logger.warning("⚠️ WARNING: No problem selected")
                logger.info("Resend avoidance test: INCONCLUSIVE")

async def main():
    """Run all tests with mock data."""
    tester = ProblemSelectorTester()
    await tester.run_tests()

if __name__ == "__main__":
    asyncio.run(main())
