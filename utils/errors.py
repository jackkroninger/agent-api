class UserAuthenticationFaliure(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class InvalidParameter(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)