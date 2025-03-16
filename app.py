import os
import re
import pickle
import json
import redis
import pyodbc
import networkx as nx
import matplotlib.pyplot as plt
from openai import OpenAI
from langchain.vectorstores import FAISS
from langchain.docstore.document import Document
from langchain_openai import OpenAIEmbeddings

class DatabaseManager:
    """
    Handles database connections and metadata retrieval.
    """
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.metadata = {}
        self.graph = nx.DiGraph()

    def connect(self):
        """Establishes a connection to the database."""
        return pyodbc.connect(self.connection_string)

    def fetch_metadata(self):
        """Retrieves database metadata including table relationships."""
        conn = self.connect()
        cursor = conn.cursor()
        
        for schema in self.schemas:
            cursor.execute(f"""
                SELECT t.name AS table_name, ISNULL(p.value, '') AS table_description
                FROM sys.tables t
                LEFT JOIN sys.extended_properties p ON t.object_id = p.major_id AND p.minor_id = 0                
            """)
            tables = cursor.fetchall()
            
            for table in tables:
                table_name, table_description = table
                self.metadata[f"{schema}.{table_name}"] = {
                    "table_description": table_description,
                    "columns": {}
                }                
                cursor.execute(f"""
                    SELECT c.name AS column_name, p.value AS column_description
                    FROM sys.columns c
                    LEFT JOIN sys.extended_properties p ON c.object_id = p.major_id AND c.column_id = p.minor_id
                    WHERE c.object_id = OBJECT_ID('{schema}.{table_name}')
                """)
                columns = cursor.fetchall()
                
                for column in columns:
                    column_name, column_description = column
                    self.metadata[f"{schema}.{table_name}"]["columns"][column_name] = column_description or ""
                
                self.graph.add_node(f"{schema}.{table_name}", description=table_description)
                
                cursor.execute(f"""
                    SELECT fk.name, SCHEMA_NAME(tp.schema_id) + '.' + tp.name AS ref_table
                    FROM sys.foreign_keys fk
                    INNER JOIN sys.tables tp ON fk.referenced_object_id = tp.object_id
                    WHERE fk.parent_object_id = OBJECT_ID('{schema}.{table_name}')
                """)
                relations = cursor.fetchall()
                
                for relation in relations:
                    self.graph.add_edge(f"{schema}.{table_name}", relation[1], relation=relation[0])        
        conn.close()
        return self.metadata, self.graph

class QueryGenerator:
    """
    Handles semantic search and SQL query generation.
    """
    def __init__(self, metadata, graph, api_key):
        self.metadata = metadata
        self.graph = graph
        self.client = OpenAI(api_key=api_key)
        self.embedder = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=api_key)
        self.vector_store = None
    
    def embed_dataset(self, dataset_path):
        """Embeds the dataset for semantic similarity search."""
        mapping_data = self.load_json(dataset_path)
        documents = [
            Document(page_content=f"Question: {entry['question']}\nAnswer: {entry['answer']}")
            for entry in mapping_data
        ]
        self.vector_store = FAISS.from_documents(documents, self.embedder)
        self.vector_store.save_local("faiss_index_dataset")

    def search_by_semantic_similarity(self, question):
        """Performs semantic search for relevant information."""
        self.vector_store = FAISS.load_local("faiss_index_dataset", self.embedder, allow_dangerous_deserialization=True)
        docs = self.vector_store.similarity_search(question, k=10)
        return "\n".join(doc.page_content for doc in docs) if docs else "No relevant results found."
    
    def generate_sql_query(self, question):
        """Generates an SQL query based on the user's question."""
        prompt = f"""
        You are a database expert.
        
        User Question:
        "{question}"
        
        Database Schema Information:
        {self.metadata}
        
        Generate a SQL query that correctly joins related tables and retrieves relevant data.
        Ensure that the query maintains logical relationships between tables.
        """        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )        
        return response.choices[0].message.content    
    @staticmethod
    def load_json(file_path):
        """Loads a JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

if __name__ == "__main__":
    DATABASE_CONFIG = {
        'server': os.getenv('DbConfig_Server'),
        'database': os.getenv('DbConfig_Database'),
        'username': os.getenv('DbConfig_Username'),
        'password': os.getenv('DbConfig_Password'),
        'driver': os.getenv('DbConfig_Driver')
    }
    connection_string = f"DRIVER={DATABASE_CONFIG['driver']};SERVER={DATABASE_CONFIG['server']};DATABASE={DATABASE_CONFIG['database']};UID={DATABASE_CONFIG['username']};PWD={DATABASE_CONFIG['password']}"
    
    db_manager = DatabaseManager(connection_string)
    metadata, graph = db_manager.fetch_metadata()
    
    api_key = os.getenv("openai_key")
    query_gen = QueryGenerator(metadata, graph, api_key)
    query_gen.embed_dataset("dataset.json")
    
    question = "Show the sales invoices for transactions made after 2024, categorized by region for the financial year 1400."
    sql_query = query_gen.generate_sql_query(question)
    print("Generated SQL Query:", sql_query)
