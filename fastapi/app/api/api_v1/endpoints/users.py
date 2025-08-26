"""
ユーザー関連 API エンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging
import traceback
from sqlalchemy import func

from app.schemas.user import (
    UserCreate, UserRegisterResponse, UserLogin, UserLoginResponse, 
    UserOut, generate_random_username, UserRoleUpdate, UserRoleUpdateResponse,
    PasswordChange, PasswordChangeResponse, UserDeleteResponse
)
from app.utils.jwt import create_access_token, authenticate_user, get_current_user, get_current_admin
from app.models.user import User
from app.core.security import get_password_hash, verify_password
from app.db.database import get_db
from app.models.teacher import TeacherProfile

# ログ設定
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/register", response_model=UserRegisterResponse)
async def register_user(
    user_data: UserCreate, 
    db: Session = Depends(get_db)
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


@router.get("/{user_id}", response_model=UserOut)
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
        
        # 使用 Pydantic 的 model_validate 方法从 SQLAlchemy 对象创建响应
        return UserOut.model_validate(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ユーザー情報取得エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.get("/", response_model=list[UserOut])
async def get_all_users(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    全ユーザー情報取得API（管理者のみ）
    
    Args:
        current_user: 現在のユーザー（管理者権限が必要）
        db: データベースセッション
    
    Returns:
        list[UserOut]: ユーザー情報のリスト
    
    Raises:
        HTTPException: 管理者権限がない場合
    """
    logger.info(f"全ユーザー情報取得リクエスト by {current_user.email}")
    
    try:
        # 管理者権限チェック（get_current_admin依存性で既にチェック済み）
        
        # 削除されていないユーザーを全て取得
        users = db.query(User).filter(
            User.is_deleted == False
        ).all()
        
        logger.info(f"全ユーザー情報取得成功: {len(users)}件")
        
        # Pydanticモデルに変換して返却
        return [UserOut.model_validate(user) for user in users]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"全ユーザー情報取得エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )
    

@router.patch("/{user_id}/role", response_model=UserRoleUpdateResponse)
async def update_user_role(
    user_id: int,
    role_data: UserRoleUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    ユーザー役割更新API（管理者のみ）
    
    Args:
        user_id: 更新対象のユーザーID
        role_data: 新しい役割情報
        current_user: 現在のユーザー（管理者権限が必要）
        db: データベースセッション
    
    Returns:
        UserRoleUpdateResponse: 更新結果
    
    Raises:
        HTTPException: 権限不足、ユーザー不存在、サーバーエラー時
    """
    logger.info(f"ユーザー役割更新リクエスト: ユーザーID {user_id} -> {role_data.role} by {current_user.email}")
    
    try:
        # 対象ユーザーが存在するかチェック
        target_user = db.query(User).filter(
            User.id == user_id,
            User.is_deleted == False
        ).first()
        
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="更新対象のユーザーが見つかりません"
            )
        
        # 自分自身の役割を変更しようとしている場合はエラー
        if target_user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="自分自身の役割を変更することはできません"
            )
        
        # 役割が実際に変更されるかチェック
        if target_user.role == role_data.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="指定された役割は既に設定されています"
            )
        
        old_role = target_user.role
        target_user.role = role_data.role
        target_user.updated_at = func.now()
        
        teacher_profile_created = False
        
        # 役割がteacherに変更された場合、teacher_profilesテーブルにレコードを作成
        if role_data.role == "teacher":
            # 既存のteacher_profileが存在するかチェック
            existing_profile = db.query(TeacherProfile).filter(
                TeacherProfile.id == user_id
            ).first()
            
            if not existing_profile:
                # 新しいteacher_profileを作成
                new_teacher_profile = TeacherProfile(
                    id=user_id,
                    phone=None,
                    bio=None,
                    profile_image=None
                )
                db.add(new_teacher_profile)
                teacher_profile_created = True
                logger.info(f"教師プロフィールを作成しました: ユーザーID {user_id}")
        
        # データベースに保存
        db.commit()
        
        logger.info(f"ユーザー役割更新完了: ユーザーID {user_id} {old_role} -> {role_data.role}")
        
        return UserRoleUpdateResponse(
            user_id=user_id,
            new_role=role_data.role,
            teacher_profile_created=teacher_profile_created
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"ユーザー役割更新エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )
    

@router.patch("/password", response_model=PasswordChangeResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    パスワード変更API（本人のみ）
    
    Args:
        password_data: パスワード変更情報
        current_user: 現在のユーザー（本人のみ）
        db: データベースセッション
    
    Returns:
        PasswordChangeResponse: 変更結果
    
    Raises:
        HTTPException: 現在のパスワードが正しくない、サーバーエラー時
    """
    logger.info(f"パスワード変更リクエスト by {current_user.email}")
    
    try:
        # 現在のパスワードが正しいかチェック
        if not verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="現在のパスワードが正しくありません"
            )
        
        # 新しいパスワードが現在のパスワードと同じでないかチェック
        if verify_password(password_data.new_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="新しいパスワードは現在のパスワードと異なる必要があります"
            )
        
        # 新しいパスワードをハッシュ化して更新
        new_hashed_password = get_password_hash(password_data.new_password)
        current_user.hashed_password = new_hashed_password
        current_user.updated_at = func.now()
        
        # データベースに保存
        db.commit()
        
        logger.info(f"パスワード変更完了: ユーザー {current_user.email}")
        
        return PasswordChangeResponse()
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"パスワード変更エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )
    

@router.delete("/{user_id}", response_model=UserDeleteResponse)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    ユーザー削除API（管理者のみ）
    
    Args:
        user_id: 削除対象のユーザーID
        current_user: 現在のユーザー（管理者権限が必要）
        db: データベースセッション
    
    Returns:
        UserDeleteResponse: 削除結果
    
    Raises:
        HTTPException: 権限不足、ユーザー不存在、自分自身を削除しようとした場合、サーバーエラー時
    """
    logger.info(f"ユーザー削除リクエスト: ユーザーID {user_id} by {current_user.email}")
    
    try:
        # 対象ユーザーが存在するかチェック
        target_user = db.query(User).filter(
            User.id == user_id,
            User.is_deleted == False
        ).first()
        
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="削除対象のユーザーが見つかりません"
            )
        
        # 自分自身を削除しようとしている場合はエラー
        if target_user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="自分自身を削除することはできません"
            )
        
        # 他の管理者を削除しようとしている場合はエラー
        if target_user.role == "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="管理者ユーザーを削除することはできません"
            )
        
        # ユーザーを削除済みにマーク（ソフトデリート）
        target_user.is_deleted = True
        target_user.deleted_at = func.now()
        target_user.updated_at = func.now()
        
        # データベースに保存
        db.commit()
        
        logger.info(f"ユーザー削除完了: ユーザーID {user_id} ({target_user.email})")
        
        return UserDeleteResponse(
            deleted_user_email=target_user.email
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"ユーザー削除エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )
    
