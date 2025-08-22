"""
講師関連 API エンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.user import User
from app.models.teacher import TeacherProfile
from app.schemas.teacher import TeacherListOut
from app.db.database import get_db
import logging

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
        import traceback
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
        import traceback
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )
