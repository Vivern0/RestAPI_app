from typing import Optional

from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.repository import users as repository_users


class Auth:
    pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
    SECRET_KEY = 'fM4pJvK5s2vY9rB1qX4cU7zW0pS3lN6f'
    ALGORITHM = 'HS256'
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/auth/token')

    def verify_password(
        self,
        plain_password: str,
        hashed_password: str
    ):
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str):
        return self.pwd_context.hash(password)

    async def create_token(
        self,
        username: str,
        delta: timedelta,
        scope: str
    ):
        cur_time = datetime.now(timezone.utc)
        expiration_time = cur_time + delta

        payload = {
            'sub': username,
            'iat': cur_time,
            'exp': expiration_time,
            'scope': scope
        }

        jwt_token = jwt.encode(
            payload, self.SECRET_KEY, algorithm=self.ALGORITHM
        )
        return jwt_token

    async def create_access_token(self, username: str):
        return await self.create_token(
            username, timedelta(minutes=15), 'access_token'
        )

    async def create_refresh_token(self, username: str):
        return await self.create_token(
            username, timedelta(days=7), 'refresh_token'
        )

    async def decode_refresh_token(self, refresh_token: str):
        try:
            payload = jwt.decode(
                refresh_token,
                self.SECRET_KEY,
                algorithms=[self.ALGORITHM]
            )
            if payload['scope'] == 'refresh_token':
                email = payload['sub']
                return email
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid scope for token'
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Could not validate credentials'
            )

    async def get_current_user(
            self,
            token: str = Depends(oauth2_scheme),
            db: Session = Depends(get_db)
    ):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(
                token,
                self.SECRET_KEY,
                algorithms=[self.ALGORITHM]
            )
            if payload['scope'] == 'access_token':
                email = payload["sub"]
                if email is None:
                    raise credentials_exception
            else:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        user = await repository_users.get_user_by_email(email, db)
        if user is None:
            raise credentials_exception
        return user


auth_service = Auth()