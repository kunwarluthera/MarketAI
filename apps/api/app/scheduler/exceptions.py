class RetryableJobError(Exception):
    """A job may be retried without changing its financial meaning."""


class PermanentJobError(Exception):
    """A job input is invalid and requires operator intervention."""


class JobLeaseLostError(RetryableJobError):
    pass


class DataUnavailableError(RetryableJobError):
    pass


class DataStaleError(RetryableJobError):
    pass


class ReconciliationMismatchError(PermanentJobError):
    pass


class FinancialIntegrityError(PermanentJobError):
    pass
