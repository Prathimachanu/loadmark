class LoadmarkError(Exception):
    """Base class for all loadmark errors."""


class RunInProgressError(LoadmarkError):
    """Another run of the same checkpoint is still running."""


class InvalidLookbackError(LoadmarkError):
    """The lookback value could not be understood."""
