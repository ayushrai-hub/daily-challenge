#!/usr/bin/env python
"""Script to check recently created problems."""
from app.db.session import get_sync_db
from app.db.models.problem import Problem
import json

def check_recent_problems():
    """Display information about the most recently created problems."""
    db = next(get_sync_db())
    problems = db.query(Problem).order_by(Problem.created_at.desc()).limit(4).all()
    
    print('\nRecently created problems:')
    for i, p in enumerate(problems):
        print(f'\n{i+1}. {p.title}')
        print(f'   Created: {p.created_at}')
        print(f'   Tags: {[tag.name for tag in p.tags]}')
        
        # Print the metadata in a readable way
        if p.problem_metadata and 'tag_data' in p.problem_metadata:
            print("   Metadata tags:")
            tag_data = p.problem_metadata.get('tag_data', {})
            
            print(f"      Raw tags: {tag_data.get('raw_tags', [])}")
            print(f"      Safe tags: {tag_data.get('safe_tags', [])}")
            print(f"      Pending tags: {tag_data.get('pending_tags', [])}")
            print(f"      Normalized tags: {tag_data.get('normalized_tags', [])}")
        else:
            print("   No metadata found")
    
    db.close()

if __name__ == '__main__':
    check_recent_problems()
