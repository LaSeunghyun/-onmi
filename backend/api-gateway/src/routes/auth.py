"""인증 관련 라우터"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
import sys
import os
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from config.settings import settings
from database.connection import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/signin")


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    locale: str = "ko-KR"


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증 - bcrypt 직접 사용"""
    try:
        # bcrypt를 직접 사용하여 호환성 문제 해결
        password_bytes = plain_password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception as e:
        logger.error(f"비밀번호 검증 오류: {e}")
        return False


def get_password_hash(password: str) -> str:
    """비밀번호 해싱 - bcrypt 직접 사용"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(password_bytes, salt)
    return hash_bytes.decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta = None):
    """JWT 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm="HS256")
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """현재 사용자 가져오기"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보를 확인할 수 없습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    async with get_db_connection() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, locale FROM users WHERE id = $1",
            user_id
        )
        if user is None:
            raise credentials_exception
        return dict(user)


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(request: SignUpRequest):
    """회원가입"""
    try:
        async with get_db_connection() as conn:
            # 이메일 중복 확인
            existing = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1",
                request.email
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 사용 중인 이메일입니다"
                )
            
            # 비밀번호 해싱 및 사용자 생성
            password_hash = get_password_hash(request.password)
            user_id = await conn.fetchval(
                """
                INSERT INTO users (email, password_hash, locale)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                request.email, password_hash, request.locale
            )
            
            # JWT 토큰 생성
            access_token = create_access_token(data={"sub": str(user_id)})
            
            return TokenResponse(access_token=access_token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"회원가입 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 처리 중 오류가 발생했습니다"
        )


@router.post("/signin", response_model=TokenResponse)
async def signin(form_data: OAuth2PasswordRequestForm = Depends()):
    """로그인 (OAuth2 형식 - application/x-www-form-urlencoded)"""
    logger.info(f"🔐 /auth/signin 호출됨")
    logger.info(f"   username (email): {form_data.username}")
    logger.info(f"   password: {'*' * len(form_data.password) if form_data.password else 'None'}")
    
    try:
        async with get_db_connection() as conn:
            user = await conn.fetchrow(
                "SELECT id, password_hash FROM users WHERE email = $1",
                form_data.username
            )
            
            if not user or not verify_password(form_data.password, user["password_hash"]):
                logger.warning(f"   ❌ 인증 실패: 이메일 또는 비밀번호 불일치")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="이메일 또는 비밀번호가 올바르지 않습니다",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            logger.info(f"   ✅ 인증 성공: 사용자 ID {user['id']}")
            access_token = create_access_token(data={"sub": str(user["id"])})
            return TokenResponse(access_token=access_token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"   ❌ 로그인 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 처리 중 오류가 발생했습니다"
        )


@router.post("/signin-json", response_model=TokenResponse)
async def signin_json(request: SignInRequest):
    """로그인 (JSON 형식) - Flutter 앱용"""
    logger.info(f"🔐 /auth/signin-json 호출됨")
    logger.info(f"   email: {request.email}")
    logger.info(f"   password: {'*' * len(request.password) if request.password else 'None'}")
    
    try:
        async with get_db_connection() as conn:
            user = await conn.fetchrow(
                "SELECT id, password_hash FROM users WHERE email = $1",
                request.email
            )
            
            if not user or not verify_password(request.password, user["password_hash"]):
                logger.warning(f"   ❌ 인증 실패: 이메일 또는 비밀번호 불일치")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="이메일 또는 비밀번호가 올바르지 않습니다",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            logger.info(f"   ✅ 인증 성공: 사용자 ID {user['id']}")
            access_token = create_access_token(data={"sub": str(user["id"])})
            return TokenResponse(access_token=access_token)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"   ❌ 로그인(JSON) 중 오류 발생: {e}")
        logger.error(f"   오류 상세:\n{error_traceback}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"로그인 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """현재 사용자 정보 조회"""
    return current_user

