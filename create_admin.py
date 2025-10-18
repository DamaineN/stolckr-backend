#!/usr/bin/env python3
"""
Admin User Creation Utility
This script allows you to create a new admin user or promote an existing user to admin.
"""
import asyncio
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from motor.motor_asyncio import AsyncIOMotorClient
from api.auth.utils import AuthUtils
from api.database.mongodb_models import UserRole, UserStatus, UserInDB
from datetime import datetime, timezone
from bson import ObjectId
import getpass

async def connect_to_db():
    """Connect to MongoDB"""
    try:
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client["stock_market_app"]
        # Test connection
        await client.admin.command('ping')
        print("✓ Connected to MongoDB")
        return db
    except Exception as e:
        print(f"✗ Failed to connect to MongoDB: {e}")
        sys.exit(1)

async def get_user_by_email(db, email: str):
    """Get user by email"""
    return await db.users.find_one({"email": email})

async def create_admin_user(db):
    """Create a new admin user"""
    print("\n=== Create New Admin User ===")
    
    # Get user details
    email = input("Admin email: ").strip()
    if not email:
        print("Email cannot be empty")
        return
    
    # Check if user already exists
    existing_user = await get_user_by_email(db, email)
    if existing_user:
        print(f"User with email {email} already exists!")
        promote = input("Would you like to promote them to admin instead? (y/N): ").strip().lower()
        if promote == 'y':
            await promote_user_to_admin(db, existing_user)
        return
    
    full_name = input("Full name: ").strip()
    if not full_name:
        print("Full name cannot be empty")
        return
    
    # Get password securely
    while True:
        password = getpass.getpass("Password: ")
        if len(password) < 8:
            print("Password must be at least 8 characters long")
            continue
        
        confirm_password = getpass.getpass("Confirm password: ")
        if password != confirm_password:
            print("Passwords don't match")
            continue
        break
    
    # Validate password strength
    password_validation = AuthUtils.validate_password_strength(password)
    if not password_validation["is_valid"]:
        print(f"Password validation failed: {', '.join(password_validation['errors'])}")
        return
    
    try:
        # Create admin user document
        user_doc = UserInDB(
            email=email,
            full_name=full_name,
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            hashed_password=AuthUtils.get_password_hash(password),
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        ).model_dump(by_alias=True)
        
        # Insert user into database
        result = await db.users.insert_one(user_doc)
        
        print(f"✓ Admin user created successfully!")
        print(f"  Email: {email}")
        print(f"  Full Name: {full_name}")
        print(f"  User ID: {result.inserted_id}")
        print(f"  Role: {UserRole.ADMIN.value}")
        
    except Exception as e:
        print(f"✗ Failed to create admin user: {e}")

async def promote_user_to_admin(db, user_doc=None):
    """Promote an existing user to admin"""
    print("\n=== Promote User to Admin ===")
    
    if not user_doc:
        email = input("Email of user to promote: ").strip()
        if not email:
            print("Email cannot be empty")
            return
        
        user_doc = await get_user_by_email(db, email)
        if not user_doc:
            print(f"User with email {email} not found")
            return
    
    # Check if already admin
    if user_doc.get("role") == UserRole.ADMIN.value:
        print(f"User {user_doc['email']} is already an admin")
        return
    
    # Show user info and confirm
    print(f"\nUser Information:")
    print(f"  Email: {user_doc['email']}")
    print(f"  Full Name: {user_doc['full_name']}")
    print(f"  Current Role: {user_doc.get('role', 'beginner')}")
    print(f"  Status: {user_doc.get('status', 'active')}")
    print(f"  Created: {user_doc['created_at']}")
    
    confirm = input(f"\nPromote this user to admin? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled")
        return
    
    try:
        # Update user to admin
        result = await db.users.update_one(
            {"_id": user_doc["_id"]},
            {
                "$set": {
                    "role": UserRole.ADMIN.value,
                    "status": UserStatus.ACTIVE.value,
                    "is_verified": True,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.modified_count > 0:
            print(f"✓ User {user_doc['email']} promoted to admin successfully!")
        else:
            print(f"✗ Failed to update user role")
            
    except Exception as e:
        print(f"✗ Failed to promote user: {e}")

async def list_admin_users(db):
    """List all admin users"""
    print("\n=== Current Admin Users ===")
    
    try:
        admin_cursor = db.users.find({"role": UserRole.ADMIN.value})
        admin_users = await admin_cursor.to_list(length=None)
        
        if not admin_users:
            print("No admin users found")
            return
        
        for user in admin_users:
            print(f"  • {user['full_name']} ({user['email']}) - ID: {user['_id']}")
            print(f"    Status: {user.get('status', 'active')} | Created: {user['created_at'].strftime('%Y-%m-%d')}")
        
        print(f"\nTotal admin users: {len(admin_users)}")
        
    except Exception as e:
        print(f"✗ Failed to list admin users: {e}")

async def main():
    """Main function"""
    print("Stock Market App - Admin User Management")
    print("=" * 50)
    
    db = await connect_to_db()
    
    while True:
        print("\nOptions:")
        print("1. Create new admin user")
        print("2. Promote existing user to admin")
        print("3. List current admin users")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            await create_admin_user(db)
        elif choice == "2":
            await promote_user_to_admin(db)
        elif choice == "3":
            await list_admin_users(db)
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please select 1-4.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)