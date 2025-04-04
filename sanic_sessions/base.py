# Author: Khaled Abdel Moezz
# Base Session Interface for Sanic Sessions
# Provides the core session management functionality for various storage backends

import abc
import datetime
import time
import uuid
import ujson
from sanic_sessions.utils import CallbackDict

def get_request_container(request):
    """Get the appropriate container for session data on a request object.
    
    Args:
        request (sanic.Request): The incoming request object
        
    Returns:
        dict: Either request.ctx.__dict__ or the request object itself
    """
    return request.ctx.__dict__ if hasattr(request, "ctx") else request

class SessionDict(CallbackDict):
    """Dictionary-like session object with modification tracking.
    
    Extends CallbackDict to track session modifications and store session ID.
    
    Args:
        initial (dict, optional): Initial session data
        sid (str, optional): Session ID
        
    Attributes:
        sid (str): Unique session identifier
        modified (bool): Flag indicating if session data has changed
    """
    
    def __init__(self, initial=None, sid=None):
        """Initialize a new SessionDict instance."""
        def on_update(self):
            self.modified = True
        super().__init__(initial, on_update)
        self.sid = sid
        self.modified = False

class BaseSessionInterface(metaclass=abc.ABCMeta):
    """Abstract base class for session storage interfaces.
    
    Provides core session management functionality that concrete implementations
    must extend with storage-specific methods.
    
    Args:
        expiry (int): Session expiration time in seconds
        prefix (str): Prefix for storage keys
        cookie_name (str): Name of the session cookie
        domain (str, optional): Cookie domain
        httponly (bool): HttpOnly cookie flag
        sessioncookie (bool): Whether to use session-only cookies
        samesite (str, optional): SameSite cookie policy
        session_name (str): Attribute name for request session
        secure (bool): Secure cookie flag
    """
    
    def __init__(
        self,
        expiry,
        prefix,
        cookie_name,
        domain,
        httponly,
        sessioncookie,
        samesite,
        session_name,
        secure,
    ):
        """Initialize the base session interface."""
        self.expiry = expiry
        self.prefix = prefix
        self.cookie_name = cookie_name
        self.domain = domain
        self.httponly = httponly
        self.sessioncookie = sessioncookie
        self.samesite = samesite
        self.session_name = session_name
        self.secure = secure

    def _delete_cookie(self, request, response):
        """Remove the session cookie from the response.
        
        Args:
            request (sanic.Request): Current request object
            response (sanic.Response): Outgoing response object
        """
        req = get_request_container(request)
        expires = datetime.datetime.now(datetime.timezone.utc)
        response.cookies.add_cookie(
            self.cookie_name,
            req[self.session_name].sid,
            expires=expires,
            max_age=0,
            httponly=self.httponly,
            secure=self.secure,
            domain=self.domain,
            samesite=self.samesite
        )

    @staticmethod
    def _calculate_expires(expiry):
        """Calculate expiration datetime from seconds.
        
        Args:
            expiry (int): Seconds until expiration
            
        Returns:
            datetime: Timezone-aware expiration datetime
        """
        expires = time.time() + expiry
        return datetime.datetime.fromtimestamp(expires, datetime.timezone.utc)

    def _set_cookie_props(self, request, response):
        """Set session cookie properties on the response.
        
        Args:
            request (sanic.Request): Current request object
            response (sanic.Response): Outgoing response object
        """
        req = get_request_container(request)
        cookie = response.cookies.add_cookie(
            self.cookie_name,
            req[self.session_name].sid,
            httponly=self.httponly,
            secure=self.secure,
            domain=self.domain,
            samesite=self.samesite
        )
        if not self.sessioncookie:
            cookie.expires = self._calculate_expires(self.expiry)
            cookie.max_age = self.expiry

    async def open(self, request) -> SessionDict:
        """Initialize or restore a session for the request.
        
        Args:
            request (sanic.Request): Current request object
            
        Returns:
            SessionDict: The initialized session object
            
        Note:
            Creates new session if none exists or if existing session is invalid
        """
        sid = None
        
        # Modern cookie access
        if hasattr(request.cookies, 'get_cookie'):
            try:
                cookie = request.cookies.get_cookie(self.cookie_name)
                sid = cookie.value if cookie else None
            except Exception:
                pass
        
        # Legacy fallback
        if sid is None:
            try:
                sid = request.cookies.get(self.cookie_name)
            except Exception:
                pass

        if not sid:
            sid = uuid.uuid4().hex
            session_dict = SessionDict(sid=sid)
        else:
            val = await self._get_value(self.prefix, sid)
            if val is not None:
                data = ujson.loads(val)
                session_dict = SessionDict(data, sid=sid)
            else:
                session_dict = SessionDict(sid=sid)

        req = get_request_container(request)
        req[self.session_name] = session_dict
        return session_dict

    async def save(self, request, response) -> None:
        """Persist session data and set response cookies.
        
        Args:
            request (sanic.Request): Current request object
            response (sanic.Response): Outgoing response object
            
        Note:
            Deletes session if empty, otherwise saves changes
        """
        req = get_request_container(request)
        if self.session_name not in req:
            return

        key = self.prefix + req[self.session_name].sid
        if not req[self.session_name]:
            await self._delete_key(key)
            if req[self.session_name].modified:
                self._delete_cookie(request, response)
            return

        val = ujson.dumps(dict(req[self.session_name]))
        await self._set_value(key, val)
        self._set_cookie_props(request, response)

    @abc.abstractmethod
    async def _get_value(self, prefix: str, sid: str):
        """Abstract method to get session data from storage.
        
        Args:
            prefix (str): Key prefix
            sid (str): Session ID
            
        Returns:
            str: Serialized session data
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def _delete_key(self, key: str):
        """Abstract method to delete session data from storage.
        
        Args:
            key (str): Full storage key
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def _set_value(self, key: str, data: SessionDict):
        """Abstract method to store session data.
        
        Args:
            key (str): Full storage key
            data (SessionDict): Session data to store
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError