import sqlite3
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define the path for the database file in the project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'user.db')

def create_connection():
    """ Create a database connection to the SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # This allows accessing columns by name
        logger.info(f"SQLite version: {sqlite3.sqlite_version}")
        logger.info(f"Successfully connected to database at {DB_PATH}")
    except sqlite3.Error as e:
        logger.error(e)
    return conn

def create_tables():
    """ Create all necessary tables in the database """
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                phone TEXT NOT NULL,
                birthdate TEXT,
                membership_type TEXT NOT NULL,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create interactions table for tracking user activity
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                interaction_type TEXT NOT NULL,
                interaction_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            conn.commit()
            logger.info("Database tables created successfully")
        except sqlite3.Error as e:
            logger.error(f"Error creating database tables: {e}")
        finally:
            conn.close()
            logger.info("Database connection closed")
    else:
        logger.error("Cannot create database connection")

# Initialize the database on import
create_tables()

# Main execution
if __name__ == '__main__':
    # Check if the database file already exists
    db_exists = os.path.exists(DB_PATH)
    
    # Create tables
    create_tables()
    
    # Log database status
    conn = create_connection()
    if conn is not None:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        logger.info(f"Current number of users in database: {user_count}")
        
        # If this is an existing database with JSON users, we could import them here
        # Check if users_db.json exists and has users
        json_db_path = os.path.join(BASE_DIR, 'users_db.json')
        if os.path.exists(json_db_path):
            import json
            from werkzeug.security import generate_password_hash
            
            try:
                with open(json_db_path, 'r') as f:
                    users = json.load(f)
                
                if users:
                    logger.info(f"Found {len(users)} users in JSON database, attempting to import...")
                    imported = 0
                    
                    for user in users:
                        try:
                            cursor.execute('''
                            INSERT INTO users (first_name, last_name, email, password, phone, birthdate, membership_type, registration_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                user.get('firstName'),
                                user.get('lastName'),
                                user.get('email'),
                                user.get('password'),
                                user.get('phone'),
                                user.get('birthdate'),
                                user.get('membershipType'),
                                user.get('registrationDate')
                            ))
                            imported += 1
                        except sqlite3.IntegrityError:
                            # User likely already exists
                            logger.warning(f"User {user.get('email')} already exists in the database")
                    
                    conn.commit()
                    logger.info(f"Successfully imported {imported} users from JSON database")
            except Exception as e:
                logger.error(f"Error importing users from JSON database: {e}")
        
        conn.close()
        
        if not db_exists:
            logger.info("New database created. You can now run the Flask application with 'python app.py'")
        else:
            logger.info("Connected to existing database. No changes were made to existing data.")
    else:
        logger.error("Error! Cannot create the database connection.")
