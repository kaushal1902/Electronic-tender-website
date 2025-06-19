import sqlite3
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get a connection to the SQLite database"""
    db_path = os.path.join(os.getcwd(), 'instance', 'tender.db')
    logger.info(f"Connecting to database at {db_path}")
    
    # Check if the database file exists
    if not os.path.exists(db_path):
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        logger.warning(f"Database file not found. Creating a new one at {db_path}")
    
    return sqlite3.connect(db_path)

def run_migration():
    """Run the migration to add missing columns to database tables"""
    
    logger.info("Starting migration for SQLite database")
    
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Begin transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Check if the user table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        if not cursor.fetchone():
            logger.error("The 'user' table does not exist. Initialize the application first.")
            return False
        
        # Check if the company_name column already exists in user table
        cursor.execute("PRAGMA table_info(user)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]  # SQLite column name is at index 1
        
        # Add company fields if they don't exist
        if 'company_name' not in column_names:
            logger.info("Adding company fields to user table")
            
            # Add each company field
            cursor.execute("ALTER TABLE user ADD COLUMN company_name TEXT")
            cursor.execute("ALTER TABLE user ADD COLUMN company_registration_number TEXT")
            cursor.execute("ALTER TABLE user ADD COLUMN company_tax_id TEXT")
            cursor.execute("ALTER TABLE user ADD COLUMN company_website TEXT")
            cursor.execute("ALTER TABLE user ADD COLUMN company_founded_year INTEGER")
            cursor.execute("ALTER TABLE user ADD COLUMN company_size TEXT")
            cursor.execute("ALTER TABLE user ADD COLUMN industry_sector TEXT")
            cursor.execute("ALTER TABLE user ADD COLUMN business_description TEXT")
            cursor.execute("ALTER TABLE user ADD COLUMN company_address TEXT")
            
            # Set some default values for existing users to prevent NULL constraint violations
            cursor.execute("UPDATE user SET company_name = 'Not Provided' WHERE company_name IS NULL")
            
            logger.info("Company fields added successfully")
        else:
            logger.info("Company fields already exist in the user table")
        
        # Check if the tender table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tender'")
        if cursor.fetchone():
            # Check if winner_selected and winner_id columns exist
            cursor.execute("PRAGMA table_info(tender)")
            tender_columns = cursor.fetchall()
            tender_column_names = [col[1] for col in tender_columns]
            
            if 'winner_selected' not in tender_column_names:
                logger.info("Adding winner_selected column to tender table")
                cursor.execute("ALTER TABLE tender ADD COLUMN winner_selected BOOLEAN DEFAULT 0")
                logger.info("winner_selected column added successfully")
            else:
                logger.info("winner_selected column already exists in the tender table")
                
            if 'winner_id' not in tender_column_names:
                logger.info("Adding winner_id column to tender table")
                cursor.execute("ALTER TABLE tender ADD COLUMN winner_id INTEGER")
                logger.info("winner_id column added successfully")
            else:
                logger.info("winner_id column already exists in the tender table")
                
            if 'status' not in tender_column_names:
                logger.info("Adding status column to tender table")
                cursor.execute("ALTER TABLE tender ADD COLUMN status TEXT DEFAULT 'active'")
                logger.info("status column added successfully")
            else:
                logger.info("status column already exists in the tender table")
                
        # Check if the tender_application table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tender_application'")
        if cursor.fetchone():
            # Check if bid_score column exists
            cursor.execute("PRAGMA table_info(tender_application)")
            app_columns = cursor.fetchall()
            app_column_names = [col[1] for col in app_columns]
            
            if 'bid_score' not in app_column_names:
                logger.info("Adding bid_score column to tender_application table")
                cursor.execute("ALTER TABLE tender_application ADD COLUMN bid_score FLOAT DEFAULT 0.0")
                logger.info("bid_score column added successfully")
            else:
                logger.info("bid_score column already exists in the tender_application table")
                
            if 'ranking' not in app_column_names:
                logger.info("Adding ranking column to tender_application table")
                cursor.execute("ALTER TABLE tender_application ADD COLUMN ranking INTEGER DEFAULT 0")
                logger.info("ranking column added successfully")
            else:
                logger.info("ranking column already exists in the tender_application table")
                
            if 'is_winner' not in app_column_names:
                logger.info("Adding is_winner column to tender_application table")
                cursor.execute("ALTER TABLE tender_application ADD COLUMN is_winner BOOLEAN DEFAULT 0")
                logger.info("is_winner column added successfully")
            else:
                logger.info("is_winner column already exists in the tender_application table")
                
            if 'notification_sent' not in app_column_names:
                logger.info("Adding notification_sent column to tender_application table")
                cursor.execute("ALTER TABLE tender_application ADD COLUMN notification_sent BOOLEAN DEFAULT 0")
                logger.info("notification_sent column added successfully")
            else:
                logger.info("notification_sent column already exists in the tender_application table")
        
        # Commit the transaction
        conn.commit()
        logger.info("Migration completed successfully")
        return True
        
    except Exception as e:
        # Rollback the transaction in case of error
        conn.rollback()
        logger.error(f"Migration failed: {str(e)}")
        return False
    finally:
        # Close the connection
        cursor.close()
        conn.close()

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("Database migration completed successfully")
    else:
        print("Database migration failed")