from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

class PasswordHandler:

    def __init__(self):
        self._password_hash = PasswordHash((BcryptHasher(), ))

    def hash_password(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        return self._password_hash.verify(password, hashed_password)

