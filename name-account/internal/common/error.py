class ErrTwoFaAlreadyEnabled(Exception):
    def __str__(self):
        return "TwoFA is already enabled for this account"

class ErrTwoFaCodeInvalid(Exception):
    def __str__(self):
        return "TwoFA code is invalid"

class ErrTwoFaNotEnabled(Exception):
    def __str__(self):
        return "TwoFA is not enabled"

class ErrUnauthorized(Exception):
    def __str__(self):
        return "Unauthorized"

class ErrInvalidPassword(Exception):
    def __str__(self):
        return "Invalid password"

class ErrAccountCreate(Exception):
    def __str__(self):
        return "Unable to create account"

class ErrInvalidEmail(Exception):
    def __str__(self):
        return "Invalid email address"

class ErrAccountNotFound(Exception):
    def __str__(self):
        return "Account not found"