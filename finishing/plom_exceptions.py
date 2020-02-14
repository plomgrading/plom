class SeriousException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class PlomSeriousException(SeriousException):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class BenignException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class PlomAPIException(BenignException):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


class PlomBenignException(BenignException):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


class PlomNoMoreException(BenignException):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


class PlomAuthenticationException(BenignException):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


class PlomLatexException(BenignException):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


class PlomExistingLoginException(BenignException):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
