class AwsError(Exception):
    """Exception caused by AWS server side issues."""
    pass


class ServiceError(Exception):
    """Deployed service didn't start/stop as expected."""
    pass
    