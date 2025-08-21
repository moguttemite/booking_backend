"""
ユーザー関連 API エンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.schemas.user import UserCreate, UserRegisterResponse, UserLogin, UserLoginResponse, UserOut, generate_random_username
from app.utils.jwt import create_access_token, authenticate_user, get_current_user, get_current_admin
from app.models.user import User
from app.core.security import get_password_hash
from app.db.database import get_db
import logging

# ログ設定
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/register", response_model=UserRegisterResponse)
async def register_user(
    user_data: UserCreate, 
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """ユーザー登録 API"""
    logger.info(f"ユーザー登録リクエスト: {user_data.email}")
    
    try:
        # メールアドレスが既に存在するかチェック
        existing_user = db.query(User).filter(
            User.email == user_data.email,
            User.is_deleted == False
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="このメールアドレスは既に登録されています"
            )
        
        # 新しいユーザーを作成
        hashed_password = get_password_hash(user_data.password)
        generated_name = generate_random_username()
        db_user = User(
            name=generated_name,
            email=user_data.email,
            hashed_password=hashed_password,
            role="student"  # デフォルトは学生
        )
        
        # データベースに保存
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"ユーザー {user_data.email} の登録が完了しました")
        
        # バックグラウンドタスク（将来的にメール送信など）
        if background_tasks:
            background_tasks.add_task(send_welcome_email, user_data.email)
        
        return UserRegisterResponse()
        
    except IntegrityError:
        db.rollback()
        logger.error(f"データベース整合性エラー: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="データベースエラーが発生しました"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"ユーザー登録エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


def send_welcome_email(email: str):
    """ウェルカムメール送信（将来的な実装）"""
    logger.info(f"ウェルカムメール送信: {email}")
    # TODO: メール送信機能を実装
    pass


@router.post("/login", response_model=UserLoginResponse)
async def login_user(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """ユーザーログイン API"""
    logger.info(f"ユーザーログインリクエスト: {login_data.email}")
    
    try:
        # ユーザー認証
        user = authenticate_user(login_data.email, login_data.password, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="メールアドレスまたはパスワードが正しくありません"
            )
        
        # JWT トークンを生成
        access_token = create_access_token(
            subject=user.id,
            email=user.email,
            role=user.role
        )
        
        logger.info(f"ユーザー {login_data.email} のログインが完了しました")
        
        return UserLoginResponse(
            name=user.name,
            role=user.role,
            token=access_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ユーザーログインエラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


# @router.get("/{user_id}", response_model=UserOut)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ユーザー情報取得API（ID指定、本人と管理者のみ）"""
    logger.info(f"ユーザー情報取得リクエスト: ユーザーID {user_id} by {current_user.email}")
    
    try:
        # 権限チェック：本人または管理者のみアクセス可能
        if current_user.id != user_id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この操作を実行する権限がありません"
            )
        
        # ユーザー情報を取得
        user = db.query(User).filter(
            User.id == user_id,
            User.is_deleted == False
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ユーザーが見つかりません"
            )
        
        logger.info(f"ユーザー情報取得成功: ユーザーID {user_id}")
        
        # 直接返回用户信息，不使用model_validate
        return UserOut(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ユーザー情報取得エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        import traceback
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.get("/test-auth")
async def test_auth(current_user: User = Depends(get_current_user)):
    """JWT認証テスト用エンドポイント"""
    return {
        "message": "認証成功",
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role
    }
    
