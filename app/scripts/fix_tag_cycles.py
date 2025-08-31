#!/usr/bin/env python
"""
Script to detect and fix cyclic dependencies in the tag hierarchy.
This utility will identify any existing cycles in the tag hierarchy
and provide options to fix them.
"""
import sys
import os
import uuid
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from typing import List, Set, Dict, Tuple, Optional
from app.db.session import engine, SessionLocal
from app.db.models.tag import Tag
from app.db.models.tag_hierarchy import TagHierarchy
from app.repositories.tag import TagRepository

def get_db():
    """Get a database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def find_all_cycles(db: Session) -> List[List[uuid.UUID]]:
    """
    Find all cycles in the tag hierarchy
    
    Args:
        db: Database session
        
    Returns:
        List of cycles, where each cycle is a list of tag IDs forming a loop
    """
    tag_repo = TagRepository(db)
    cycles = []
    
    # Get all tag hierarchy relationships
    relationships = db.query(TagHierarchy).all()
    
    # For each relationship, check if it creates a cycle
    for relationship in relationships:
        parent_id = relationship.parent_tag_id
        child_id = relationship.child_tag_id
        
        # Temporarily remove this relationship to test if it's part of a cycle
        db.query(TagHierarchy).filter(
            TagHierarchy.parent_tag_id == parent_id,
            TagHierarchy.child_tag_id == child_id
        ).delete()
        
        # Check if adding it back would create a cycle
        if tag_repo.would_create_cycle(parent_id, child_id):
            cycle_path = tag_repo.find_cycle_path(parent_id, child_id)
            if cycle_path:
                cycles.append(cycle_path)
        
        # Restore the relationship (we're not committing the deletion)
        db.rollback()
    
    return cycles

def print_cycle_details(db: Session, cycles: List[List[uuid.UUID]]):
    """
    Print detailed information about detected cycles
    
    Args:
        db: Database session
        cycles: List of cycles to print
    """
    if not cycles:
        print("No cycles found in the tag hierarchy. Everything looks good!")
        return
    
    print(f"Found {len(cycles)} cycle(s) in the tag hierarchy:")
    
    for i, cycle in enumerate(cycles, 1):
        print(f"\nCycle #{i}:")
        
        # Print cycle path with tag names
        path_names = []
        for tag_id in cycle:
            tag = db.query(Tag).filter(Tag.id == tag_id).first()
            path_names.append(f"{tag.name} (ID: {tag_id})" if tag else f"Unknown (ID: {tag_id})")
        
        print(" → ".join(path_names))
        
        # Print suggested fix
        if len(cycle) >= 2:
            # The last two elements in the cycle form the problematic relationship
            last_id = cycle[-1]
            second_last_id = cycle[-2]
            
            last_tag = db.query(Tag).filter(Tag.id == last_id).first()
            second_last_tag = db.query(Tag).filter(Tag.id == second_last_id).first()
            
            if last_tag and second_last_tag:
                print("\nSuggested fix:")
                print(f"Remove the relationship: {last_tag.name} → {second_last_tag.name}")
                print(f"Relationship IDs: parent_id={last_id}, child_id={second_last_id}")

def fix_cycle(db: Session, parent_id: uuid.UUID, child_id: uuid.UUID) -> bool:
    """
    Fix a cycle by removing a specific relationship
    
    Args:
        db: Database session
        parent_id: Parent tag ID in the relationship to remove
        child_id: Child tag ID in the relationship to remove
        
    Returns:
        True if the relationship was removed, False otherwise
    """
    try:
        # Find the relationship
        relationship = db.query(TagHierarchy).filter(
            TagHierarchy.parent_tag_id == parent_id,
            TagHierarchy.child_tag_id == child_id
        ).first()
        
        if not relationship:
            print(f"Relationship not found: parent_id={parent_id}, child_id={child_id}")
            return False
        
        # Get tags for better reporting
        parent_tag = db.query(Tag).filter(Tag.id == parent_id).first()
        child_tag = db.query(Tag).filter(Tag.id == child_id).first()
        
        parent_name = parent_tag.name if parent_tag else "Unknown"
        child_name = child_tag.name if child_tag else "Unknown"
        
        # Remove the relationship
        db.delete(relationship)
        db.commit()
        
        print(f"Successfully removed relationship: {parent_name} → {child_name}")
        return True
    
    except Exception as e:
        db.rollback()
        print(f"Error fixing cycle: {str(e)}")
        return False

def interactive_fix(db: Session):
    """
    Interactive mode to detect and fix cycles
    
    Args:
        db: Database session
    """
    while True:
        cycles = find_all_cycles(db)
        print_cycle_details(db, cycles)
        
        if not cycles:
            print("\nAll cycles have been fixed!")
            break
        
        print("\nChoose an action:")
        print("1. Fix the first cycle")
        print("2. Fix a specific cycle")
        print("3. Fix all cycles automatically")
        print("4. Exit without further fixes")
        
        choice = input("Enter your choice (1-4): ")
        
        if choice == "1" and cycles:
            cycle = cycles[0]
            if len(cycle) >= 2:
                fix_cycle(db, cycle[-1], cycle[-2])
        
        elif choice == "2" and cycles:
            cycle_num = input(f"Enter cycle number to fix (1-{len(cycles)}): ")
            try:
                idx = int(cycle_num) - 1
                if 0 <= idx < len(cycles):
                    cycle = cycles[idx]
                    if len(cycle) >= 2:
                        fix_cycle(db, cycle[-1], cycle[-2])
                else:
                    print("Invalid cycle number")
            except ValueError:
                print("Invalid input. Please enter a number.")
        
        elif choice == "3" and cycles:
            for cycle in cycles:
                if len(cycle) >= 2:
                    if fix_cycle(db, cycle[-1], cycle[-2]):
                        print("Fixed cycle:", " → ".join([str(tag_id) for tag_id in cycle]))
        
        elif choice == "4":
            print("Exiting without further fixes")
            break
        
        else:
            print("Invalid choice or no cycles to fix")

def main():
    """Main entry point for the script"""
    print("===== Tag Hierarchy Cycle Detection and Fix Utility =====")
    
    # Get a database session
    db = next(get_db())
    
    try:
        print("\nChecking for cycles in the tag hierarchy...")
        cycles = find_all_cycles(db)
        
        if not cycles:
            print("No cycles found in the tag hierarchy. Everything looks good!")
            return
        
        print_cycle_details(db, cycles)
        
        # Ask if user wants to fix cycles
        fix_choice = input("\nDo you want to fix these cycles? (y/n): ")
        
        if fix_choice.lower() == "y":
            fix_method = input("Choose fix method (interactive/auto): ")
            
            if fix_method.lower() == "interactive":
                interactive_fix(db)
            elif fix_method.lower() == "auto":
                for cycle in cycles:
                    if len(cycle) >= 2:
                        if fix_cycle(db, cycle[-1], cycle[-2]):
                            print("Fixed cycle:", " → ".join([str(tag_id) for tag_id in cycle]))
            else:
                print("Invalid fix method. Exiting without fixes.")
    
    finally:
        db.close()

if __name__ == "__main__":
    main()
