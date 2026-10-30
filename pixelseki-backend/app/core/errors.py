"""Map raw exceptions to human-readable error messages for the frontend."""

import re

_ERROR_PATTERNS: list[tuple[str, str]] = [
    # API key / auth
    (r"No API key was provided", "The service is not configured. Please contact the administrator."),
    (r"API key not valid", "The service is not available. Please contact the administrator."),
    (r"API_KEY_INVALID", "The service is not available. Please contact the administrator."),
    (r"PERMISSION_DENIED|denied access|403", "The service access has been denied. Please check your API key or billing setup."),

    # Rate limiting / quota
    (r"429|Resource has been exhausted|RESOURCE_EXHAUSTED", "The service is currently busy. Please try again in a few minutes."),
    (r"quota", "The service has reached its usage limit. Please try again later."),
    (r"rate limit", "Too many requests. Please wait a moment and try again."),

    # Server errors
    (r"500|INTERNAL|internal error|Internal Server Error", "The service encountered an internal error. Please try again."),
    (r"503|UNAVAILABLE|Service Unavailable", "The service is temporarily unavailable. Please try again later."),
    (r"overloaded|capacity", "The server is busy. Please try again in a few minutes."),

    # Timeout
    (r"timeout|timed out|deadline exceeded|DEADLINE_EXCEEDED", "The request timed out. Please try again."),

    # Content safety
    (r"safety|blocked|SAFETY|content filter", "The request was blocked by content safety filters. Try adjusting your description."),
    (r"RECITATION", "The request was blocked due to content policy. Try adjusting your description."),

    # Image generation specific
    (r"no image data|returned no image", "The service failed to generate an image. Please try again with a different description."),
    (r"image too large|payload too large", "The reference image is too large. Please use a smaller image."),

    # Network
    (r"ConnectionError|connection refused|ConnectError", "Could not connect to the service. Please try again later."),
    (r"SSLError|SSL", "Secure connection to the service failed. Please try again."),

    # Background removal
    (r"rembg|remove.*background", "Background removal failed. The image was saved without background removal."),

    # Catch-all for any HTTP error codes from APIs
    (r"4\d{2}", "The request was rejected. Please try again or adjust your input."),
    (r"5\d{2}", "The server encountered an error. Please try again later."),
]


def humanize_error(error: Exception) -> str:
    """Convert a raw exception into a user-friendly error message."""
    raw = str(error)
    error_type = type(error).__name__

    combined = f"{error_type}: {raw}"

    for pattern, message in _ERROR_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            return message

    # Fallback: generic message
    return "Something went wrong. Please try again later."
