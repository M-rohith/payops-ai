class RazorpayError(Exception):
    """Base exception with a deliberately credential-free message."""


class RazorpayNotConfiguredError(RazorpayError):
    pass


class RazorpayAuthenticationError(RazorpayError):
    pass


class RazorpayAPIError(RazorpayError):
    pass


class RazorpayUnavailableError(RazorpayError):
    pass
