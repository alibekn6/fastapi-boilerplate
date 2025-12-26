"""
Rate limiter configuration module.

This module initializes the SlowAPI limiter instance that can be imported
by both the main application and route modules without causing circular imports.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize SlowAPI limiter
# This can be imported by route modules and the main app
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[]  # No global limits, configure per-endpoint
)
