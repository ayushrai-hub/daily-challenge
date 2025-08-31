#!/usr/bin/env python
"""
Verify the verification_tokens table schema in the test database.
This script will connect to the test database and check that the
verification_tokens table exists with the correct structure.
"""
import sys
from sqlalchemy import inspect, MetaData, Table, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Use test database URL
DATABASE_URL = "postgresql://dcq_test_user:dcq_test_pass@localhost:5434/dcq_test_db"

def verify_verification_tokens_table():
    """Verify the verification_tokens table exists with the correct schema."""
    print("\n===== Verification Tokens Table Verification =====\n")
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        print(f"Connected to database: {DATABASE_URL}")
        
        # Get inspector
        inspector = inspect(engine)
        
        # Check if verification_tokens table exists
        if 'verification_tokens' not in inspector.get_table_names():
            print("❌ Table 'verification_tokens' does not exist!")
            return False
        
        print("✅ Table 'verification_tokens' exists")
        
        # Get columns in the table
        columns = inspector.get_columns('verification_tokens')
        column_names = [col['name'] for col in columns]
        expected_columns = [
            'id', 'created_at', 'updated_at', 'user_id', 'token', 
            'is_used', 'expires_at', 'token_type'
        ]
        
        # Check if all expected columns exist
        for col in expected_columns:
            if col in column_names:
                print(f"✅ Column '{col}' exists")
            else:
                print(f"❌ Column '{col}' is missing!")
                return False
        
        # Get foreign keys
        fks = inspector.get_foreign_keys('verification_tokens')
        if not fks:
            print("❌ No foreign keys found. Expected foreign key to users table!")
            return False
        
        user_fk_found = False
        for fk in fks:
            if fk.get('referred_table') == 'users' and 'user_id' in fk.get('constrained_columns', []):
                user_fk_found = True
                print(f"✅ Foreign key to users table exists")
        
        if not user_fk_found:
            print("❌ Foreign key to users table not found!")
            return False
        
        # Check for indexes
        indexes = inspector.get_indexes('verification_tokens')
        token_index_found = False
        for idx in indexes:
            if 'token' in idx['column_names']:
                token_index_found = True
                print(f"✅ Index on 'token' column exists")
        
        if not token_index_found:
            print("⚠️ Warning: No index on 'token' column found.")
        
        print("\n===== Verification Results =====")
        print("✅ The verification_tokens table is properly configured")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during verification: {str(e)}")
        return False

if __name__ == "__main__":
    success = verify_verification_tokens_table()
    sys.exit(0 if success else 1)
