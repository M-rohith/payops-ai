class PayOpsAIError(Exception):
    """Safe base exception for frontend-facing copilot failures."""


class AIConfigurationError(PayOpsAIError):
    pass


class AIToolError(PayOpsAIError):
    pass


class AIToolRoundLimitError(PayOpsAIError):
    pass


class AIProviderError(PayOpsAIError):
    pass
