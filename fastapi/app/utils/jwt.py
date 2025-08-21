"""
JWT Token 関連機能
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password
from app.db.database import get_db
from app.models.user import User

# HTTP Bearer 認証スキーム
security = HTTPBearer()

# JWT Token ペイロードの構造
class TokenPayload:
    """JWT Token ペイロード"""
    sub: str  # ユーザーID
    email: str  # メールアドレス
    role: str  # ユーザーロール
    exp: datetime  # 有効期限


def create_access_token(
    subject: Union[str, int], 
    email: str, 
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    アクセストークンを作成
    
    Args:
        subject: ユーザーID
        email: メールアドレス
        role: ユーザーロール
        expires_delta: 有効期限（指定しない場合は設定ファイルの値を使用）
    
    Returns:
        str: JWT トークン
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "sub": str(subject),
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenPayload]:
    """
    JWT トークンを検証
    
    Args:
        token: JWT トークン
    
    Returns:
        TokenPayload: トークンペイロード（検証失敗時はNone）
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # ペイロードからTokenPayloadオブジェクトを作成
        token_payload = TokenPayload()
        token_payload.sub = payload.get("sub")
        token_payload.email = payload.get("email")
        token_payload.role = payload.get("role")
        token_payload.exp = datetime.fromtimestamp(payload.get("exp"))
        
        return token_payload
        
    except JWTError:
        return None


def authenticate_user(email: str, password: str, db: Session) -> Optional[User]:
    """
    ユーザー認証
    
    Args:
        email: メールアドレス
        password: パスワード
        db: データベースセッション
    
    Returns:
        User: 認証成功時のユーザーオブジェクト（失敗時はNone）
    """
    # メールアドレスでユーザーを検索
    user = db.query(User).filter(
        User.email == email,
        User.is_deleted == False
    ).first()
    
    if not user:
        return None
    
    # パスワードを検証
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    現在のユーザーを取得（依存性注入用）
    
    Args:
        credentials: HTTP認証情報
        db: データベースセッション
    
    Returns:
        User: 現在のユーザーオブジェクト
    
    Raises:
        HTTPException: 認証失敗時
    """
    token = credentials.credentials
    
    # トークンを検証
    token_payload = verify_token(token)
    if not token_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンです",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # トークンの有効期限をチェック
    if datetime.now(timezone.utc) > token_payload.exp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンの有効期限が切れています",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # データベースからユーザーを取得
    user = db.query(User).filter(
        User.id == int(token_payload.sub),
        User.is_deleted == False
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つかりません",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    現在のアクティブユーザーを取得
    
    Args:
        current_user: 現在のユーザー
    
    Returns:
        User: アクティブなユーザーオブジェクト
    
    Raises:
        HTTPException: ユーザーが削除されている場合
    """
    if current_user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="削除されたユーザーです"
        )
    
    return current_user


def get_current_user_with_role(required_role: str):
    """
    特定のロールを持つユーザーのみアクセス可能な依存性
    
    Args:
        required_role: 必要なロール
    
    Returns:
        依存性関数
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{required_role}権限が必要です"
            )
        return current_user
    
    return role_checker


# 便利な依存性関数
get_current_admin = get_current_user_with_role("admin")
get_current_teacher = get_current_user_with_role("teacher")
get_current_student = get_current_user_with_role("student")
