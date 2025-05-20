import json
import os
import logging
from werkzeug.security import generate_password_hash
from datetime import datetime
from database_setup import InMemoryDB, DB_PATH

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def import_from_local_storage_json(local_storage_file):
    """Import user data from a local storage JSON file into the database"""
    try:
        # Read the local storage data
        with open(local_storage_file, 'r') as f:
            local_data = json.load(f)
        
        # Initialize the database
        db = InMemoryDB(DB_PATH)
        
        # Get the users data from local storage
        if 'users' in local_data:
            users = local_data['users']
            logger.info(f"Found {len(users)} users in local storage")
            
            imported_count = 0
            for user in users:
                # Make sure the user has all required fields
                if all(field in user for field in ['firstName', 'lastName', 'email', 'password']):
                    # Hash the password if it's not already hashed
                    if not user['password'].startswith('pbkdf2:'):
                        user['password'] = generate_password_hash(user['password'])
                    
                    # Ensure registration date is in ISO format
                    if 'registrationDate' not in user:
                        user['registrationDate'] = datetime.now().isoformat()
                    
                    # Try to add the user to the database
                    success, message = db.add_user(user)
                    if success:
                        imported_count += 1
                        logger.info(f"Imported user: {user['email']}")
                    else:
                        logger.warning(f"Failed to import user {user['email']}: {message}")
            
            logger.info(f"Successfully imported {imported_count} users out of {len(users)}")
            return imported_count
        else:
            logger.warning("No 'users' key found in local storage data")
            return 0
    except Exception as e:
        logger.error(f"Error importing from local storage: {e}")
        return 0

def import_current_user_from_local_storage(local_storage_file):
    """Import the current user from local storage into the database"""
    try:
        # Read the local storage data
        with open(local_storage_file, 'r') as f:
            local_data = json.load(f)
        
        # Initialize the database
        db = InMemoryDB(DB_PATH)
        
        # Get the current user data from local storage
        if 'currentUser' in local_data:
            user = local_data['currentUser']
            logger.info(f"Found current user in local storage: {user.get('email')}")
            
            # Make sure the user has all required fields
            if all(field in user for field in ['firstName', 'lastName', 'email', 'password']):
                # Hash the password if it's not already hashed
                if not user['password'].startswith('pbkdf2:'):
                    user['password'] = generate_password_hash(user['password'])
                
                # Ensure registration date is in ISO format
                if 'registrationDate' not in user:
                    user['registrationDate'] = datetime.now().isoformat()
                
                # Try to add the user to the database
                success, message = db.add_user(user)
                if success:
                    logger.info(f"Imported current user: {user['email']}")
                    return True
                else:
                    logger.warning(f"Failed to import current user {user['email']}: {message}")
                    return False
            else:
                logger.warning("Current user is missing required fields")
                return False
        else:
            logger.warning("No 'currentUser' key found in local storage data")
            return False
    except Exception as e:
        logger.error(f"Error importing current user from local storage: {e}")
        return False

if __name__ == "__main__":
    # Set the path to your local storage JSON file
    local_storage_file = input("Enter path to localStorage JSON file (or press Enter for default 'local_storage.json'): ")
    if not local_storage_file:
        local_storage_file = "local_storage.json"
    
    if not os.path.exists(local_storage_file):
        logger.error(f"File not found: {local_storage_file}")
        print("Please export your browser's localStorage to a JSON file first.")
        print("Instructions:")
        print("1. Open your browser's developer tools (F12)")
        print("2. Go to the Application tab (Chrome) or Storage tab (Firefox)")
        print("3. Find 'Local Storage' in the left panel and select your website")
        print("4. Right-click and select 'Export' or manually copy the data to a JSON file")
    else:
        # Try to import users
        users_imported = import_from_local_storage_json(local_storage_file)
        
        # Try to import current user if no users were imported
        if users_imported == 0:
            if import_current_user_from_local_storage(local_storage_file):
                print("Successfully imported current user from local storage")
            else:
                print("Failed to import current user from local storage")
        else:
            print(f"Successfully imported {users_imported} users from local storage")
