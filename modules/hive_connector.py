import jaydebeapi
import jpype
import os

class HiveConnection:
    """
    Hive database connection manager using JDBC.

    Handles connection lifecycle, query execution, and result retrieval from Hive databases.
    """

    def __init__(self, username=None, password=None):
        """
        Initialize Hive connection with credentials.

        Args:
            username: Database username
            password: Database password
        """
        self.username = username
        self.password = password
        self.connection = None
        self.cursor = None

    def connect(self, host='hermes.kyuubi.vip.sddz.ebay.com', port=10009,
                database='default', additional_params='kyuubi.session.cluster=hermes',
                driver_path=None):
        """
        Establish connection to Hive database.

        Args:
            host: Database host address
            port: Database port (default: 10009)
            database: Database name (default: 'default')
            additional_params: Additional JDBC connection parameters
            driver_path: Path to JDBC driver JAR file

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.username or not self.password:
            raise ValueError("Username and password are required")

        try:
            if additional_params:
                jdbc_url = f"jdbc:hive2://{host}:{port}/{database};{additional_params}"
            else:
                jdbc_url = f"jdbc:hive2://{host}:{port}/{database}"

            driver_class = "org.apache.hive.jdbc.HiveDriver"

            if driver_path is None:
                skill_path = r'C:\Users\yuntu\Desktop\Claude AI WorkSpace\0_personal-notes\skills\run-hive-query'
                driver_path = os.path.join(skill_path, 'hive-jdbc-1.2.1000.2.6.4-ebay.3-standalone.jar')

            if not os.path.exists(driver_path):
                raise FileNotFoundError(f"JDBC driver not found at {driver_path}")

            self.connection = jaydebeapi.connect(
                driver_class,
                jdbc_url,
                [self.username, self.password],
                driver_path
            )

            self.cursor = self.connection.cursor()
            return True, "Successfully connected to Hive database"

        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def execute_query(self, query):
        """
        Execute SQL query and return results.

        Args:
            query: SQL query string to execute

        Returns:
            List of result rows

        Raises:
            Exception: If no active connection or query execution fails
        """
        if not self.cursor:
            raise Exception("No active database connection. Please connect first.")

        try:
            self.cursor.execute(query)
            results = self.cursor.fetchall()
            return results
        except Exception as e:
            raise Exception(f"Query execution failed: {str(e)}")

    def get_column_names(self):
        """Get column names from the last executed query"""
        if not self.cursor:
            raise Exception("No active database connection.")

        if self.cursor.description:
            return [desc[0] for desc in self.cursor.description]
        return None

    def get_tables(self):
        """Get list of all tables in the database."""
        return self.execute_query("SHOW TABLES")

    def describe_table(self, table_name):
        """
        Get table schema description.

        Args:
            table_name: Name of the table to describe
        """
        return self.execute_query(f"DESCRIBE {table_name}")

    def close(self):
        """Close database connection and cursor."""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
        except Exception as e:
            print(f"Error closing connection: {str(e)}")

    def is_connected(self):
        """Check if database connection is active."""
        return self.connection is not None and self.cursor is not None
