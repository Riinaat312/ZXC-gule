from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask App
app = Flask(__name__, static_folder='.', static_url_path='')

# Define the path for the database file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'user.db')

def get_db_connection():
    """Establish a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

@app.route('/')
def home():
    """Serve the main.html page."""
    return send_from_directory(BASE_DIR, 'main.html')

@app.route('/<path:filename>')
def serve_files(filename):
    """Serve static files like HTML, CSS, JS, images."""
    return send_from_directory(BASE_DIR, filename)

@app.route('/register', methods=['POST'])
def register():
    """Handle user registration data submission."""
    logger.debug("Received registration request")
    try:
        data = request.get_json()
        logger.debug(f"Registration data received: {data}")
        
        # Extract user information from the JSON request
        first_name = data.get('firstName')
        last_name = data.get('lastName')
        email = data.get('email')
        password = data.get('password')
        phone = data.get('phone')
        birthdate = data.get('birthdate')
        membership_type = data.get('membershipType', 'none')  # Default to 'none' if not provided
        
        # Validate required fields
        if not all([first_name, last_name, email, password, phone]):
            logger.warning("Missing required fields in registration data")
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Hash the password for security
        hashed_password = generate_password_hash(password)
        
        # Database operations should be within try/except to handle errors
        conn = None
        try:
            # Connect to database and insert the new user
            conn = get_db_connection()
            cursor = conn.cursor()
            
            logger.debug("Inserting user into database")
            cursor.execute('''
                INSERT INTO users (first_name, last_name, email, password, phone, birthdate, membership_type) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (first_name, last_name, email, hashed_password, phone, birthdate, membership_type))
            
            # Get the ID of the newly inserted user
            user_id = cursor.lastrowid
            
            # Log this interaction
            cursor.execute('''
                INSERT INTO interactions (user_id, interaction_type, interaction_data)
                VALUES (?, ?, ?)
            ''', (user_id, 'registration', f"User registered with email {email}"))
            
            conn.commit()
            
            # Fetch the user data to return
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user_data = cursor.fetchone()
            
            # Convert row to dict and remove password
            user_dict = dict(user_data)
            user_dict.pop('password')
            
            # Convert snake_case to camelCase for frontend
            safe_user = {
                'id': user_dict['id'],
                'firstName': user_dict['first_name'],
                'lastName': user_dict['last_name'],
                'email': user_dict['email'],
                'phone': user_dict['phone'],
                'birthdate': user_dict['birthdate'],
                'membershipType': user_dict['membership_type'],
                'registrationDate': user_dict['registration_date']
            }
            
            logger.info(f"User registration successful: {email}")
            return jsonify({
                'success': True, 
                'message': 'Registration successful! Welcome to Healthy Life Fitness Club.',
                'user': safe_user
            })
        except sqlite3.IntegrityError as e:
            logger.error(f"Database integrity error during registration: {e}")
            # This error occurs if the email already exists (due to UNIQUE constraint)
            return jsonify({
                'success': False, 
                'error': 'This email is already registered.'
            }), 409
        except sqlite3.Error as e:
            logger.error(f"SQLite error during registration: {e}")
            return jsonify({
                'success': False, 
                'error': f'Database error: {str(e)}'
            }), 500
        finally:
            if conn:
                conn.close()
            
    except Exception as e:
        logger.exception(f"Unexpected error during registration: {e}")
        return jsonify({
            'success': False, 
            'error': f'An error occurred during registration: {str(e)}'
        }), 500

@app.route('/login', methods=['POST'])
def login():
    """Handle user login."""
    logger.debug("Received login request")
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password are required'}), 400
            
        conn = None
        try:
            # Connect to database and find the user
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password'], password):
                # User authenticated successfully
                logger.info(f"User login successful: {email}")
                
                # Log this interaction
                cursor.execute('''
                    INSERT INTO interactions (user_id, interaction_type, interaction_data)
                    VALUES (?, ?, ?)
                ''', (user['id'], 'login', f"User logged in with email {email}"))
                
                conn.commit()
                
                # Convert row to dict and remove password
                user_dict = dict(user)
                user_dict.pop('password')
                
                # Convert snake_case to camelCase for frontend
                safe_user = {
                    'id': user_dict['id'],
                    'firstName': user_dict['first_name'],
                    'lastName': user_dict['last_name'],
                    'email': user_dict['email'],
                    'phone': user_dict['phone'],
                    'birthdate': user_dict['birthdate'],
                    'membershipType': user_dict['membership_type'],
                    'registrationDate': user_dict['registration_date']
                }
                
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'user': safe_user
                })
            else:
                # Log failed login attempt
                if user:
                    cursor.execute('''
                        INSERT INTO interactions (user_id, interaction_type, interaction_data)
                        VALUES (?, ?, ?)
                    ''', (user['id'], 'failed_login', f"Failed login attempt for {email}"))
                    conn.commit()
                
                logger.warning(f"Failed login attempt for email: {email}")
                return jsonify({
                    'success': False, 
                    'error': 'Invalid email or password'
                }), 401
        except sqlite3.Error as e:
            logger.error(f"SQLite error during login: {e}")
            return jsonify({
                'success': False, 
                'error': f'Database error: {str(e)}'
            }), 500
        finally:
            if conn:
                conn.close()
            
    except Exception as e:
        logger.exception(f"Unexpected error during login: {e}")
        return jsonify({
            'success': False,
            'error': f'An error occurred during login: {str(e)}'
        }), 500

@app.route('/check-server', methods=['GET'])
def check_server():
    """Simple endpoint to check if server is running."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    conn.close()
    
    return jsonify({
        'status': 'online', 
        'message': 'Server is running properly',
        'database': 'SQLite user.db',
        'user_count': user_count
    })

@app.route('/log-interaction', methods=['POST'])
def log_interaction():
    """Log user interaction with the website."""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        interaction_type = data.get('type')
        interaction_data = data.get('data')
        
        if not interaction_type:
            return jsonify({'success': False, 'error': 'Interaction type is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # If user_id is provided, verify the user exists
        if user_id:
            cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
            if not cursor.fetchone():
                conn.close()
                return jsonify({'success': False, 'error': 'User not found'}), 404
        
        cursor.execute('''
            INSERT INTO interactions (user_id, interaction_type, interaction_data)
            VALUES (?, ?, ?)
        ''', (user_id, interaction_type, interaction_data))
        
        conn.commit()
        interaction_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Interaction logged successfully',
            'interactionId': interaction_id
        })
        
    except Exception as e:
        logger.exception(f"Error logging interaction: {e}")
        return jsonify({
            'success': False,
            'error': f'An error occurred while logging interaction: {str(e)}'
        }), 500

@app.route('/update-membership', methods=['POST'])
def update_membership():
    """Update a user's membership type."""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        membership_type = data.get('membershipType')
        billing_cycle = data.get('billingCycle', 'monthly')
        
        if not all([user_id, membership_type]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Update the user's membership
            cursor.execute('''
                UPDATE users 
                SET membership_type = ?
                WHERE id = ?
            ''', (membership_type, user_id))
            
            # Log this interaction
            cursor.execute('''
                INSERT INTO interactions (user_id, interaction_type, interaction_data)
                VALUES (?, ?, ?)
            ''', (user_id, 'membership_update', f"Membership updated to {membership_type} with {billing_cycle} billing"))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Membership updated successfully'
            })
        except sqlite3.Error as e:
            logger.error(f"SQLite error during membership update: {e}")
            return jsonify({
                'success': False,
                'error': f'Database error: {str(e)}'
            }), 500
        finally:
            if conn:
                conn.close()
                
    except Exception as e:
        logger.exception(f"Unexpected error during membership update: {e}")
        return jsonify({
            'success': False, 
            'error': f'An error occurred: {str(e)}'
        }), 500

@app.route('/cancel-membership', methods=['POST'])
def cancel_membership():
    """Cancel a user's membership."""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400
        
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Update the user's membership to 'none'
            cursor.execute('''
                UPDATE users 
                SET membership_type = 'none'
                WHERE id = ?
            ''', (user_id,))
            
            # Log this interaction
            cursor.execute('''
                INSERT INTO interactions (user_id, interaction_type, interaction_data)
                VALUES (?, ?, ?)
            ''', (user_id, 'membership_cancelled', f"User {user_id} cancelled their membership"))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Membership cancelled successfully'
            })
        except sqlite3.Error as e:
            logger.error(f"SQLite error during membership cancellation: {e}")
            return jsonify({
                'success': False,
                'error': f'Database error: {str(e)}'
            }), 500
        finally:
            if conn:
                conn.close()
                
    except Exception as e:
        logger.exception(f"Unexpected error during membership cancellation: {e}")
        return jsonify({
            'success': False, 
            'error': f'An error occurred: {str(e)}'
        }), 500

if __name__ == '__main__':
    # Check if database exists before starting
    if not os.path.exists(DB_PATH):
        logger.warning(f"Database file '{DB_PATH}' not found.")
        logger.warning("Please run 'python database_setup.py' first to create the database.")
    else:
        try:
            # Ensure tables exist
            from database_setup import create_tables
            create_tables()
            logger.info("Database tables verified.")
        except Exception as e:
            logger.error(f"Could not verify database tables: {e}")
    
    # Run the Flask application
    app.run(debug=True, port=5000, host='0.0.0.0')
