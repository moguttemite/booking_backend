"""
講師関連 API エンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging
import traceback

from app.models.user import User
from app.models.teacher import TeacherProfile
from app.schemas.teacher import TeacherListOut, TeacherProfileUpdate, TeacherProfileUpdateResponse
from app.utils.jwt import get_current_user, get_current_admin
from app.db.database import get_db

# ログ設定
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=list[TeacherListOut])
async def get_all_teachers(
    db: Session = Depends(get_db)
):
    """
    講師一覧取得API（認証不要）
    
    Args:
        db: データベースセッション
    
    Returns:
        list[TeacherListOut]: 講師情報のリスト
    
    Raises:
        HTTPException: サーバーエラー時
    """
    logger.info("講師一覧取得リクエスト")
    
    try:
        # 講師ロールを持つユーザーとその講師プロフィールを取得
        teachers = db.query(
            User, TeacherProfile
        ).outerjoin(
            TeacherProfile, User.id == TeacherProfile.id
        ).filter(
            and_(
                User.role == "teacher",
                User.is_deleted == False
            )
        ).all()
        
        logger.info(f"講師一覧取得成功: {len(teachers)}件")
        
        # 結果をTeacherListOutモデルに変換
        teacher_list = []
        for user, profile in teachers:
            teacher_data = {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": profile.phone if profile else None,
                "bio": profile.bio if profile else None,
                "profile_image": profile.profile_image if profile else None
            }
            teacher_list.append(TeacherListOut(**teacher_data))
        
        return teacher_list
        
    except Exception as e:
        logger.error(f"講師一覧取得エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.get("/{teacher_id}", response_model=TeacherListOut)
async def get_teacher_by_id(
    teacher_id: int,
    db: Session = Depends(get_db)
):
    """
    特定講師情報取得API（認証不要）
    
    Args:
        teacher_id: 講師ID
        db: データベースセッション
    
    Returns:
        TeacherListOut: 講師情報
    
    Raises:
        HTTPException: 講師不存在、サーバーエラー時
    """
    logger.info(f"特定講師情報取得リクエスト: 講師ID {teacher_id}")
    
    try:
        # 指定されたIDの講師とそのプロフィールを取得
        teacher_data = db.query(
            User, TeacherProfile
        ).outerjoin(
            TeacherProfile, User.id == TeacherProfile.id
        ).filter(
            and_(
                User.id == teacher_id,
                User.role == "teacher",
                User.is_deleted == False
            )
        ).first()
        
        if not teacher_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された講師が見つかりません"
            )
        
        user, profile = teacher_data
        
        logger.info(f"特定講師情報取得成功: 講師ID {teacher_id}")
        
        # TeacherListOutモデルに変換して返却
        teacher_info = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": profile.phone if profile else None,
            "bio": profile.bio if profile else None,
            "profile_image": profile.profile_image if profile else None
        }
        
        return TeacherListOut(**teacher_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"特定講師情報取得エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.patch("/{teacher_id}/profile", response_model=TeacherProfileUpdateResponse)
async def update_teacher_profile(
    teacher_id: int,
    profile_data: TeacherProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    講師プロフィール更新API（本人・管理者）
    
    Args:
        teacher_id: 更新対象の講師ID
        profile_data: 更新するプロフィール情報
        current_user: 現在のユーザー（本人または管理者）
        db: データベースセッション
    
    Returns:
        TeacherProfileUpdateResponse: 更新結果
    
    Raises:
        HTTPException: 権限不足、講師不存在、サーバーエラー時
    """
    logger.info(f"講師プロフィール更新リクエスト: 講師ID {teacher_id} by {current_user.email}")
    
    try:
        # 権限チェック：本人または管理者のみアクセス可能
        if current_user.id != teacher_id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この操作を実行する権限がありません"
            )
        
        # 対象講師が存在し、講師ロールを持っているかチェック
        target_user = db.query(User).filter(
            User.id == teacher_id,
            User.role == "teacher",
            User.is_deleted == False
        ).first()
        
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="更新対象の講師が見つかりません"
            )
        
        # 講師プロフィールを取得または作成
        teacher_profile = db.query(TeacherProfile).filter(
            TeacherProfile.id == teacher_id
        ).first()
        
        if not teacher_profile:
            # プロフィールが存在しない場合は新規作成
            teacher_profile = TeacherProfile(
                id=teacher_id,
                phone=None,
                bio=None,
                profile_image=None
            )
            db.add(teacher_profile)
            logger.info(f"講師プロフィールを新規作成しました: 講師ID {teacher_id}")
        
        # 更新されたフィールドを追跡
        updated_fields = []
        
        # 名前フィールドの更新（user_infosテーブル）
        if profile_data.name is not None:
            if target_user.name != profile_data.name:
                target_user.name = profile_data.name
                updated_fields.append("name")
        
        # 各フィールドを更新（Noneでない場合のみ）
        if profile_data.phone is not None:
            if teacher_profile.phone != profile_data.phone:
                teacher_profile.phone = profile_data.phone
                updated_fields.append("phone")
        
        if profile_data.bio is not None:
            if teacher_profile.bio != profile_data.bio:
                teacher_profile.bio = profile_data.bio
                updated_fields.append("bio")
        
        if profile_data.profile_image is not None:
            if teacher_profile.profile_image != profile_data.profile_image:
                teacher_profile.profile_image = profile_data.profile_image
                updated_fields.append("profile_image")
        
        # 更新されたフィールドがある場合のみupdated_atを更新
        if updated_fields:
            # user_infosテーブルのupdated_atも更新
            target_user.updated_at = func.now()
            teacher_profile.updated_at = func.now()
            
            # データベースに保存
            db.commit()
            
            logger.info(f"講師プロフィール更新完了: 講師ID {teacher_id}, 更新フィールド: {updated_fields}")
        else:
            logger.info(f"講師プロフィール更新なし: 講師ID {teacher_id} (変更なし)")
        
        return TeacherProfileUpdateResponse()
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"講師プロフィール更新エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )
