from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from ..errors.exceptions import InvalidTokenError

class TokenHandler:

    def __init__(self, secret_key: str, algorithm: str, expire_minutes: int):
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._expire_minutes = expire_minutes

    def create_token(self, user_id: str) -> str:

        expire = datetime.now(timezone.utc) + timedelta(minutes=self._expire_minutes)
        payload = {"sub" : user_id, "exp": expire}
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
    

    def decode_token(self, token: str) -> str:

        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])

        except JWTError:
            raise InvalidTokenError()

        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            raise InvalidTokenError()

        return subject