"""
GrooveGrab Custom Exceptions
"""

class GrooveGrabError(Exception):
    """Base exception for GrooveGrab CLI errors."""
    pass

class ProviderError(GrooveGrabError):
    """Raised when a provider fails to handle or resolve a request."""
    pass

class ExtractionError(GrooveGrabError):
    """Raised when stream extraction fails."""
    pass

class TranscodeError(GrooveGrabError):
    """Raised when audio conversion fails."""
    pass

class MetadataError(GrooveGrabError):
    """Raised when tagging or metadata processing fails."""
    pass

class ConfigError(GrooveGrabError):
    """Raised when configuration operations fail."""
    pass
