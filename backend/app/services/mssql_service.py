import pyodbc
from app.config import settings
from datetime import datetime

class MSSQLService:
    """Service for MS SQL Server operations (company database)
    
    Stores original PDF files in company's MS SQL vault
    Per supervisor approval + FYP PDF Table 1.3
    """
    
    def __init__(self):
        self.server = settings.MSSQL_SERVER
        self.port = settings.MSSQL_PORT
        self.database = settings.MSSQL_DATABASE
        self.user = settings.MSSQL_USER
        self.password = settings.MSSQL_PASSWORD
    
    def get_connection(self):
        """Get MS SQL Server connection"""
        try:
            connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.server},{self.port};DATABASE={self.database};UID={self.user};PWD={self.password}"
            conn = pyodbc.connect(connection_string)
            return conn
        except Exception as e:
            raise Exception(f"MS SQL Connection failed: {str(e)}")
    
    def save_document(self, file_id: str, filename: str, file_size: int, file_path: str, file_data: bytes) -> dict:
        """Save document to MS SQL Server vault
        
        Creates table if not exists:
        Documents (id, file_id, filename, file_size, file_data, upload_date)
        """
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create table if not exists
            create_table_query = """
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Documents' and xtype='U')
            CREATE TABLE Documents (
                id INT PRIMARY KEY IDENTITY(1,1),
                file_id VARCHAR(36) UNIQUE,
                filename VARCHAR(255),
                file_size INT,
                file_data VARBINARY(MAX),
                upload_date DATETIME
            )
            """
            cursor.execute(create_table_query)
            conn.commit()
            
            # Insert document
            insert_query = """
            INSERT INTO Documents (file_id, filename, file_size, file_data, upload_date)
            VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(insert_query, (file_id, filename, file_size, file_data, datetime.now()))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return {
                "status": "success",
                "message": f"Document saved to MS SQL Server: {filename}",
                "file_id": file_id
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "file_id": file_id
            }
    
    def get_document(self, file_id: str) -> dict:
        """Retrieve document from MS SQL Server"""
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = "SELECT file_id, filename, file_size, upload_date FROM Documents WHERE file_id = ?"
            cursor.execute(query, (file_id,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                return {
                    "status": "success",
                    "file_id": result[0],
                    "filename": result[1],
                    "file_size": result[2],
                    "upload_date": result[3].isoformat()
                }
            else:
                return {
                    "status": "not_found",
                    "message": f"Document {file_id} not found in vault"
                }
        
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def list_documents(self, limit: int = 10) -> dict:
        """List documents from MS SQL Server"""
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = f"SELECT TOP {limit} file_id, filename, file_size, upload_date FROM Documents ORDER BY upload_date DESC"
            cursor.execute(query)
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            documents = []
            for row in results:
                documents.append({
                    "file_id": row[0],
                    "filename": row[1],
                    "file_size": row[2],
                    "upload_date": row[3].isoformat()
                })
            
            return {
                "status": "success",
                "documents": documents,
                "total": len(documents)
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "documents": []
            }
