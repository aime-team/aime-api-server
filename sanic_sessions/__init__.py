# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

# Author: Khaled Abdel Moezz
# Sanic Session Extension
# Provides session management for Sanic applications with multiple storage backends

from .aioredis import AIORedisSessionInterface
from .memcache import MemcacheSessionInterface
from .memory import InMemorySessionInterface
from .mongodb import MongoDBSessionInterface
from .redis import RedisSessionInterface

__all__ = (
    "MemcacheSessionInterface",
    "RedisSessionInterface",
    "InMemorySessionInterface",
    "MongoDBSessionInterface",
    "AIORedisSessionInterface",
    "Session",
)

class Session:
    """Main session manager for Sanic applications.
    
    Provides session management middleware that can be initialized with different
    storage backends. Automatically handles session creation, storage, and expiration.
    
    Args:
        app (sanic.Sanic, optional): Sanic application instance
        interface (BaseSessionInterface, optional): Session storage interface
        
    Example:
        >>> from sanic import Sanic
        >>> from sanic_session import Session, InMemorySessionInterface
        >>> app = Sanic("MyApp")
        >>> session = Session(app, InMemorySessionInterface())
    """
    
    def __init__(self, app=None, interface=None):
        """Initialize the session manager.
        
        Args:
            app (sanic.Sanic, optional): Sanic application instance
            interface (BaseSessionInterface, optional): Session storage interface
        """
        self.interface = None
        if app:
            self.init_app(app, interface)

    def init_app(self, app, interface):
        """Initialize the session manager with a Sanic application.
        
        Args:
            app (sanic.Sanic): Sanic application instance
            interface (BaseSessionInterface): Session storage interface
            
        Note:
            If no interface is provided, defaults to InMemorySessionInterface.
            Registers request and response middleware for session handling.
        """
        self.interface = interface or InMemorySessionInterface()
        if not hasattr(app.ctx, "extensions"):
            app.ctx.extensions = {}

        app.ctx.extensions[self.interface.session_name] = self

        @app.on_request
        async def add_session_to_request(request):
            """Request middleware to initialize session.
            
            Args:
                request (sanic.Request): Incoming request object
                
            Note:
                Creates new session if initialization fails, ensuring request.ctx
                always has a valid session object.
            """
            try:
                await self.interface.open(request)
            except Exception as e:
                app.logger.error(f"Session init error: {str(e)}")
                req = get_request_container(request)
                req[self.interface.session_name] = SessionDict(sid=uuid.uuid4().hex)

        @app.on_response
        async def save_session(request, response):
            """Response middleware to persist session changes.
            
            Args:
                request (sanic.Request): Request object
                response (sanic.Response): Response object
                
            Note:
                Silently handles errors to prevent breaking the response flow.
            """
            try:
                await self.interface.save(request, response)
            except Exception as e:
                app.logger.error(f"Session save error: {str(e)}")