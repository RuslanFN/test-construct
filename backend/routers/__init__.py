from .auth import router as auth_router
from .tests import router as tests_router
from .public import router as public_router
from .admin import router as admin_router
from .media_router import router as media_router
from .debug import router as debug_router

__all__ = ["auth_router", "tests_router", "public_router", "admin_router", "media_router", "debug_router"]
