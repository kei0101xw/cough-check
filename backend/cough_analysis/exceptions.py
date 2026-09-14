class CoughAnalysisError(Exception):
    """Base class for errors safe to expose through the API."""


class InvalidAudioError(CoughAnalysisError):
    pass


class ModelUnavailableError(CoughAnalysisError):
    pass
