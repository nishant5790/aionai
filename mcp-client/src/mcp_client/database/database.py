"""
Database connection and session management for MCP Client.

This module provides database connection utilities and session management
for the MCP client application.
"""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from .models import Base, User, MCPServer, QueryHistory


class Database:
    """Database connection and session manager."""
    
    def __init__(self, database_url: str = None):
        """
        Initialize database connection.
        
        Args:
            database_url: Database connection URL. If None, uses environment variable
                         or defaults to SQLite.
        """
        if database_url is None:
            database_url = os.getenv(
                "DATABASE_URL", 
                "sqlite:///./mcp_client.db"
            )
        
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all database tables."""
        Base.metadata.drop_all(bind=self.engine)
    
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session."""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_default_user(self, username: str = "admin", email: str = None) -> bool:
        """Create a default user if none exists. Returns True if user was created or already exists."""
        with self.session_scope() as session:
            existing_user = session.query(User).filter(User.username == username).first()
            if not existing_user:
                user = User(username=username, email=email)
                session.add(user)
                session.commit()
                return True
            return True
    
    def get_user_by_username(self, username: str) -> User:
        """Get user by username."""
        with self.session_scope() as session:
            user = session.query(User).filter(User.username == username).first()
            if user:
                # Create a detached copy to avoid session binding issues
                user_copy = User(
                    username=user.username,
                    email=user.email,
                    created_at=user.created_at,
                    is_active=user.is_active
                )
                user_copy.id = user.id
                return user_copy
            return None
    
    def create_mcp_server(self, user_id: int, server_data: dict) -> MCPServer:
        """Create a new MCP server configuration."""
        with self.session_scope() as session:
            server = MCPServer(owner_id=user_id, **server_data)
            session.add(server)
            session.commit()
            session.refresh(server)
            
            # Ensure all attributes are loaded before session closes
            _ = (server.id, server.name, server.description, server.server_type,
                 server.server_path, server.server_url, server.server_command,
                 server.server_args, server.server_env, server.capabilities,
                 server.last_ping, server.is_active, server.created_at,
                 server.updated_at, server.owner_id)
            
            # Detach from session to prevent DetachedInstanceError
            session.expunge(server)
            return server
    
    def get_user_servers(self, user_id: int) -> list[MCPServer]:
        """Get all MCP servers for a user."""
        with self.session_scope() as session:
            servers = session.query(MCPServer).filter(
                MCPServer.owner_id == user_id,
                MCPServer.is_active == True
            ).all()
            
            # Ensure all attributes are loaded before session closes
            for server in servers:
                # Access all attributes to ensure they're loaded
                _ = (server.id, server.name, server.description, server.server_type,
                     server.server_path, server.server_url, server.server_command,
                     server.server_args, server.server_env, server.capabilities,
                     server.last_ping, server.is_active, server.created_at,
                     server.updated_at, server.owner_id)
            
            # Detach from session to prevent DetachedInstanceError
            session.expunge_all()
            return servers
    
    def get_server_by_id(self, server_id: int) -> MCPServer:
        """Get MCP server by ID."""
        with self.session_scope() as session:
            server = session.query(MCPServer).filter(MCPServer.id == server_id).first()
            if server:
                # Ensure all attributes are loaded before session closes
                _ = (server.id, server.name, server.description, server.server_type,
                     server.server_path, server.server_url, server.server_command,
                     server.server_args, server.server_env, server.capabilities,
                     server.last_ping, server.is_active, server.created_at,
                     server.updated_at, server.owner_id)
                # Detach from session to prevent DetachedInstanceError
                session.expunge(server)
            return server
    
    def update_server_capabilities(self, server_id: int, capabilities: dict):
        """Update server capabilities."""
        with self.session_scope() as session:
            server = session.query(MCPServer).filter(MCPServer.id == server_id).first()
            if server:
                server.capabilities = capabilities
                session.commit()
    
    def log_query(self, user_id: int, server_id: int, query_data: dict) -> QueryHistory:
        """Log a query execution."""
        with self.session_scope() as session:
            query = QueryHistory(
                user_id=user_id,
                mcp_server_id=server_id,
                **query_data
            )
            session.add(query)
            session.commit()
            session.refresh(query)
            
            # Ensure all attributes are loaded before session closes
            _ = (query.id, query.query_text, query.query_type, query.tool_name,
                 query.tool_args, query.resource_uri, query.prompt_name,
                 query.prompt_args, query.result, query.error_message,
                 query.execution_time, query.created_at, query.user_id,
                 query.mcp_server_id)
            
            # Detach from session to prevent DetachedInstanceError
            session.expunge(query)
            return query
    
    def get_query_history(self, user_id: int, limit: int = 50) -> list[QueryHistory]:
        """Get query history for a user."""
        with self.session_scope() as session:
            queries = session.query(QueryHistory).filter(
                QueryHistory.user_id == user_id
            ).order_by(QueryHistory.created_at.desc()).limit(limit).all()
            
            # Ensure all attributes are loaded before session closes
            for query in queries:
                _ = (query.id, query.query_text, query.query_type, query.tool_name,
                     query.tool_args, query.resource_uri, query.prompt_name,
                     query.prompt_args, query.result, query.error_message,
                     query.execution_time, query.created_at, query.user_id,
                     query.mcp_server_id)
            
            # Detach from session to prevent DetachedInstanceError
            session.expunge_all()
            return queries


# Global database instance
db = Database()


def init_database():
    """Initialize the database with default data."""
    db.create_tables()
    
    # Create default user
    db.create_default_user("admin", "admin@localhost")
    
    # Get the default user
    default_user = db.get_user_by_username("admin")
    
    # Check if we have any servers, if not create a demo server
    servers = db.get_user_servers(default_user.id)
    if not servers:
        demo_server_data = {
            "name": "Demo Calculator Server",
            "description": "Example MCP server with calculator tools",
            "server_type": "stdio",
            "server_path": "examples/simple_server.py",
            "server_command": "python",
            "server_args": ["examples/simple_server.py"],
            "server_env": {}
        }
        db.create_mcp_server(default_user.id, demo_server_data)
    
    return db


def get_database() -> Database:
    """Get the global database instance."""
    return db


def get_db_session():
    """Dependency for FastAPI to get database session."""
    return db.get_session() 