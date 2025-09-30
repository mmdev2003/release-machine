class ErrAccountNotFound(Exception):
    def __str__(self):
        return 'Account not found'

class ErrTokenExpired(Exception):
    def __str__(self):
        return 'Token expired'

class ErrTokenInvalid(Exception):
    def __str__(self):
        return 'Invalid token'