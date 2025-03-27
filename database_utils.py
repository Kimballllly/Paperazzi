import mysql.connector

def connect_to_database():
    """
    Establishes a connection to the MySQL database.
    Returns:
        connection (MySQLConnection): The database connection object.
    """
    try:
        connection = mysql.connector.connect(
            host="paperazzi.cre40o0wmfru.ap-southeast-2.rds.amazonaws.com",
            user="admin",
            password="paperazzi",
            database="paperazzi"
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None


def update_job_status(job_id, status, details=None):
    """
    Updates the status of a job in the database.
    Args:
        job_id (int): The ID of the job to update.
        status (str): The new status for the job.
        details (str, optional): Additional details to log.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    connection = connect_to_database()
    if not connection:
        return False

    try:
        cursor = connection.cursor()
        query = "UPDATE print_job_details SET status = %s WHERE job_id = %s"
        cursor.execute(query, (status, job_id))

        if details:
            details_query = "UPDATE print_job_details SET details = %s WHERE job_id = %s"
            cursor.execute(details_query, (str(details), job_id))

        connection.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Error updating job status: {err}")
        return False
    finally:
        connection.close()
