import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load the keys, overriding any existing environment variables
load_dotenv(override=True)

def get_db_connection():
    """
    Establish a connection to the MySQL database using credentials from .env
    """
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", 3306)),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "")
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        raise e
    
    return None

if __name__ == "__main__":
    conn = get_db_connection()
    if conn:
        print("Successfully connected to the MySQL database!")
        conn.close()
