from feeluown.excs import ProviderIOError


class QQIOError(ProviderIOError):
    def __init__(self, message):
        super().__init__(message, provider='qq')
