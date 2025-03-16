An Intelligent System for Automatic SQL Query Generation

This program is an intelligent system for automatically generating SQL queries based on user questions in natural language. It utilizes large language models (LLMs) like GPT-4 and semantic search techniques to analyze data and extract information from the database.
Key Features of the Program
1. Retrieving Metadata and Database Structure

    PyODBC is used to connect to the SQL Server database.
    Information about tables, descriptions, columns, and foreign key relationships is extracted and modeled into a directed graph using NetworkX.
    This metadata is stored and cached in Redis to prevent redundant queries to the database.
2. Analyzing User Questions and Identifying Relevant Tables

    The user’s question is processed by GPT-4o to identify relevant schemas.
    FAISS-based semantic search is used to determine which tables are most related to the user’s query.
    A depth-first search (DFS) algorithm is applied to analyze table relationships within the database graph.
    If there is no direct connection between the selected tables, intermediary tables are automatically added.
3. Automatic SQL Query Generation Based on Metadata

    After selecting the appropriate tables, the program generates a customized prompt for GPT-4, asking it to create an SQL query.
    The query is structured according to the database schema, table relationships, and SQL rules.
    The generated query is displayed to the user, ready for execution.
4. Caching Data for Performance Optimization

    Database metadata and table relationship graphs are stored in Redis to reduce repeated database retrievals.
    FAISS stores processed data to speed up future searches.

Summary
🔹 This program is an intelligent query system that enables users to retrieve information from a database without writing manual SQL queries.
🔹 The use of AI models and semantic search ensures that even if the user’s question is not precise, the system can still extract relevant information.
🔹 The program follows an object-oriented programming (OOP) structure, enhancing readability, flexibility, and scalability.
🔹 Caching in Redis and storing search vectors in FAISS improve the system’s performance.

