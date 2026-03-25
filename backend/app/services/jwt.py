from datetime import timedelta, datetime, timezone
import jwt
from app.core.config import settings



class JwtService:

    def create_access_token(self,email: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=24*60)
        to_encode = {
            "email": email,
            "exp": expire
        }
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def get_email_from_token(self,token:str) ->str:
        payload = self.decode_jwt(token)
        if "email" not in payload:
            raise Exception("Invalid token")
        return payload["email"]
        

    def create_refresh_token(self,email: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(weeks=1)
        to_encode = {
            "email": email,
            "exp": expire
        }
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def decode_jwt(self,encoded_jwt: str) -> dict:
        try:
            payload = jwt.decode(encoded_jwt, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            print("Token has expired")
        except jwt.InvalidTokenError:
            print("Invalid token")

