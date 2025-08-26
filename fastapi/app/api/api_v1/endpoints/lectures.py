"""
講座関連 API エンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List
import logging
import traceback

from app.models.lecture import Lecture, LectureTeacher
from app.models.user import User
from app.models.teacher import TeacherProfile
from app.schemas.lecture import (
    LectureListOut, LectureDetailOut, LectureCreate, LectureCreateResponse, 
    LectureTeacherChange, LectureTeacherChangeResponse,
    MultiTeacherLectureResponse, AddTeacherToLectureRequest, 
    LectureTeacherOut
)
from app.utils.jwt import get_current_user, get_current_admin
from app.db.database import get_db

# ログ設定
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=LectureCreateResponse)
async def create_lecture(
    lecture_data: LectureCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    講座作成API（講師・管理者）
    
    Args:
        lecture_data: 作成する講座情報
            - teacher_id: 講座の主讲讲师ID（必須）
            - is_multi_teacher: 是否为多讲师讲座（講師はFalseのみ、管理者のみTrue可能）
        current_user: 現在のユーザー（講師または管理者）
        db: データベースセッション
    
    Returns:
        LectureCreateResponse: 作成結果
    
    Raises:
        HTTPException: 権限不足、講師プロフィール不存在、サーバーエラー時
        
    注意事項:
        - 講師は自分自身のみを講座の主讲讲师として指定可能
        - 講師は多讲师講座を作成不可（is_multi_teacher = False）
        - 管理者は任意の講師を指定可能
        - 管理者のみ多讲师講座を作成可能（is_multi_teacher = True）
    """
    logger.info(f"講座作成リクエスト: {lecture_data.lecture_title} by {current_user.email}")
    
    try:
        # 権限チェック：講師または管理者のみアクセス可能
        if current_user.role not in ["teacher", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この操作を実行する権限がありません。講師または管理者権限が必要です"
            )
        
        # 講師の場合、講師プロフィールが存在するかチェック
        if current_user.role == "teacher":
            teacher_profile = db.query(TeacherProfile).filter(
                TeacherProfile.id == current_user.id
            ).first()
            
            if not teacher_profile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="講師プロフィールが存在しません。先に講師プロフィールを作成してください"
                )
            
            # 讲师无法创建多讲师讲座
            if lecture_data.is_multi_teacher:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="講師は多讲师講座を作成することはできません。管理者のみが多讲师講座を作成できます"
                )
            
            # 讲师必须指定teacher_id，且只能指定自己
            if not lecture_data.teacher_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="講師は講座の主讲讲师を指定する必要があります"
                )
            
            if lecture_data.teacher_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="講師は自分自身のみを講座の主讲讲师として指定できます"
                )
        
        # 管理员的情况
        elif current_user.role == "admin":
            # 管理员必须指定teacher_id
            if not lecture_data.teacher_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="管理者は講座の主讲讲师を指定する必要があります"
                )
            
            # 验证指定的讲师是否存在且是讲师角色
            target_teacher = db.query(User).filter(
                User.id == lecture_data.teacher_id,
                User.role == "teacher",
                User.is_deleted == False
            ).first()
            
            if not target_teacher:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="指定された講師が見つからないか、講師ロールを持っていません"
                )
            
            # 验证讲师是否有讲师档案
            target_teacher_profile = db.query(TeacherProfile).filter(
                TeacherProfile.id == lecture_data.teacher_id
            ).first()
            
            if not target_teacher_profile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="指定された講師のプロフィールが存在しません"
                )
        
        # 确定讲座的主讲讲师ID
        final_teacher_id = lecture_data.teacher_id
        
        # 创建新讲座
        new_lecture = Lecture(
            teacher_id=final_teacher_id,
            lecture_title=lecture_data.lecture_title,
            lecture_description=lecture_data.lecture_description,
            approval_status="pending",  # デフォルトは承認待ち
            is_multi_teacher=lecture_data.is_multi_teacher  # 设置多讲师标识
        )
        
        # データベースに保存
        db.add(new_lecture)
        db.commit()
        db.refresh(new_lecture)
        
        logger.info(f"講座作成完了: 講座ID {new_lecture.id}, タイトル: {new_lecture.lecture_title}, 主讲讲师: {final_teacher_id}, 多讲师: {new_lecture.is_multi_teacher}")
        
        return LectureCreateResponse(
            lecture_id=new_lecture.id,
            lecture_title=new_lecture.lecture_title,
            approval_status=new_lecture.approval_status,
            created_at=new_lecture.created_at
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"講座作成エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.get("/", response_model=List[LectureListOut])
async def get_all_lectures(
    db: Session = Depends(get_db)
):
    """
    講座一覧取得API（認証不要）
    
    Args:
        db: データベースセッション
    
    Returns:
        List[LectureListOut]: 講座情報のリスト
    
    Raises:
        HTTPException: サーバーエラー時
    """
    logger.info("講座一覧取得リクエスト")
    
    try:
        # 削除されていない講座を全て取得
        query = db.query(
            Lecture, User, TeacherProfile
        ).join(
            TeacherProfile, Lecture.teacher_id == TeacherProfile.id
        ).join(
            User, TeacherProfile.id == User.id
        ).filter(
            Lecture.is_deleted == False,
            User.is_deleted == False
        ).order_by(Lecture.created_at.desc())
        
        lectures = query.all()
        
        logger.info(f"講座一覧取得成功: {len(lectures)}件")
        
        # 結果をLectureListOutモデルに変換
        lecture_list = []
        for lecture, user, profile in lectures:
            lecture_data = {
                "id": lecture.id,
                "lecture_title": lecture.lecture_title,
                "lecture_description": lecture.lecture_description,
                "approval_status": lecture.approval_status,
                "teacher_name": user.name,
                "is_multi_teacher": lecture.is_multi_teacher,  # 新增：多讲师标识
                "created_at": lecture.created_at,
                "updated_at": lecture.updated_at
            }
            lecture_list.append(LectureListOut(**lecture_data))
        
        return lecture_list
        
    except Exception as e:
        logger.error(f"講座一覧取得エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )



@router.get("/{lecture_id}", response_model=LectureDetailOut)
async def get_lecture_by_id(
    lecture_id: int,
    db: Session = Depends(get_db)
):
    """
    特定講座詳細取得API（認証不要）
    
    Args:
        lecture_id: 講座ID
        db: データベースセッション
    
    Returns:
        LectureDetailOut: 講座詳細情報
    
    Raises:
        HTTPException: 講座不存在、サーバーエラー時
    """
    logger.info(f"特定講座詳細取得リクエスト: 講座ID {lecture_id}")
    
    try:
        # 指定されたIDの講座とその講師情報を取得
        lecture_data = db.query(
            Lecture, User, TeacherProfile
        ).join(
            TeacherProfile, Lecture.teacher_id == TeacherProfile.id
        ).join(
            User, TeacherProfile.id == User.id
        ).filter(
            and_(
                Lecture.id == lecture_id,
                Lecture.is_deleted == False,
                User.is_deleted == False
            )
        ).first()
        
        if not lecture_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された講座が見つかりません"
            )
        
        lecture, user, profile = lecture_data
        
        logger.info(f"特定講座詳細取得成功: 講座ID {lecture_id}")
        
        # LectureDetailOutモデルに変換して返却
        lecture_detail = {
            "id": lecture.id,
            "lecture_title": lecture.lecture_title,
            "lecture_description": lecture.lecture_description,
            "teacher_id": lecture.teacher_id,
            "approval_status": lecture.approval_status,
            "is_multi_teacher": lecture.is_multi_teacher,  # 新增：多讲师标识
            "created_at": lecture.created_at,
            "updated_at": lecture.updated_at,
            "teacher_name": user.name,
            "teacher_email": user.email,
            "teacher_phone": profile.phone if profile else None,
            "teacher_bio": profile.bio if profile else None,
            "teacher_profile_image": profile.profile_image if profile else None
        }
        
        return LectureDetailOut(**lecture_detail)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"特定講座詳細取得エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.patch("/{lecture_id}/teacher", response_model=LectureTeacherChangeResponse)
async def change_lecture_teacher(
    lecture_id: int,
    teacher_data: LectureTeacherChange,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    講座担当講師変更API（管理者のみ）
    
    Args:
        lecture_id: 変更対象の講座ID
        teacher_data: 新しい講師情報
        current_user: 現在のユーザー（管理者権限が必要）
        db: データベースセッション
    
    Returns:
        LectureTeacherChangeResponse: 変更結果
    
    Raises:
        HTTPException: 権限不足、講座不存在、講師不存在、サーバーエラー時
        
    注意事項:
        - 単讲师講座：任意の講師に変更可能
        - 多讲师講座：既に講座に参加している講師のみに変更可能
    """
    logger.info(f"講座担当講師変更リクエスト: 講座ID {lecture_id} -> 講師ID {teacher_data.new_teacher_id} by {current_user.email}")
    
    try:
        # 対象講座が存在するかチェック
        lecture = db.query(Lecture).filter(
            Lecture.id == lecture_id,
            Lecture.is_deleted == False
        ).first()
        
        if not lecture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="変更対象の講座が見つかりません"
            )
        
        # 多讲师讲座の場合、新しい講師が講座に参加しているかチェック
        if lecture.is_multi_teacher:
            existing_teacher = db.query(LectureTeacher).filter(
                LectureTeacher.lecture_id == lecture_id,
                LectureTeacher.teacher_id == teacher_data.new_teacher_id
            ).first()
            
            if not existing_teacher:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="多讲师講座の場合、先に講師を講座に追加してください"
                )
        
        # 新しい講師が存在するかチェック
        new_teacher = db.query(User).filter(
            User.id == teacher_data.new_teacher_id,
            User.is_deleted == False
        ).first()
        
        if not new_teacher:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された講師が見つかりません"
            )
        
        # 新しい講師に講師プロフィールが存在するかチェック
        new_teacher_profile = db.query(TeacherProfile).filter(
            TeacherProfile.id == teacher_data.new_teacher_id
        ).first()
        
        if not new_teacher_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="指定された講師のプロフィールが存在しません"
            )
        
        # 現在の講師情報を取得
        old_teacher = db.query(User).filter(
            User.id == lecture.teacher_id,
            User.is_deleted == False
        ).first()
        
        if not old_teacher:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="現在の講師情報が見つかりません"
            )
        
        # 同じ講師に変更しようとしている場合はエラー
        if lecture.teacher_id == teacher_data.new_teacher_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="現在と同じ講師に変更することはできません"
            )
        
        # 講師を変更
        old_teacher_id = lecture.teacher_id
        old_teacher_name = old_teacher.name
        
        lecture.teacher_id = teacher_data.new_teacher_id
        lecture.updated_at = func.now()
        
        # データベースに保存
        db.commit()
        
        logger.info(f"講座担当講師変更完了: 講座ID {lecture_id}, 講師ID {old_teacher_id} -> {teacher_data.new_teacher_id}")
        
        return LectureTeacherChangeResponse()
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"講座担当講師変更エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


# ==================== 多讲师讲座管理API ====================

@router.post("/{lecture_id}/teachers", response_model=MultiTeacherLectureResponse)
async def add_teacher_to_lecture(
    lecture_id: int,
    teacher_data: AddTeacherToLectureRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    多讲师講座に講師を追加するAPI（管理者のみ）
    
    Args:
        lecture_id: 講座ID
        teacher_data: 追加する講師情報
        current_user: 現在のユーザー（管理者権限が必要）
        db: データベースセッション
    
    Returns:
        MultiTeacherLectureResponse: 操作結果
    
    Raises:
        HTTPException: 権限不足、講座不存在、講師不存在、サーバーエラー時
    """
    logger.info(f"講座に講師追加リクエスト: 講座ID {lecture_id}, 講師ID {teacher_data.teacher_id} by {current_user.email}")
    
    try:
        # 講座が存在し、多讲师講座かどうかをチェック
        lecture = db.query(Lecture).filter(
            Lecture.id == lecture_id,
            Lecture.is_deleted == False
        ).first()
        
        if not lecture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された講座が見つかりません"
            )
        
        if not lecture.is_multi_teacher:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="この講座は多讲师講座ではありません"
            )
        
        # 追加する講師が存在し、講師ロールを持っているかチェック
        target_teacher = db.query(User).filter(
            User.id == teacher_data.teacher_id,
            User.role == "teacher",
            User.is_deleted == False
        ).first()
        
        if not target_teacher:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された講師が見つからないか、講師ロールを持っていません"
            )
        
        # 講師に講師プロフィールが存在するかチェック
        target_teacher_profile = db.query(TeacherProfile).filter(
            TeacherProfile.id == teacher_data.teacher_id
        ).first()
        
        if not target_teacher_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="指定された講師のプロフィールが存在しません"
            )
        
        # この講師が既にこの講座に参加しているかチェック
        existing_teacher = db.query(LectureTeacher).filter(
            LectureTeacher.lecture_id == lecture_id,
            LectureTeacher.teacher_id == teacher_data.teacher_id
        ).first()
        
        if existing_teacher:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="この講師は既にこの講座に参加しています"
            )
        
        # 講師-講座関連レコードを作成
        lecture_teacher = LectureTeacher(
            lecture_id=lecture_id,
            teacher_id=teacher_data.teacher_id
        )
        
        db.add(lecture_teacher)
        db.commit()
        
        logger.info(f"講座に講師追加成功: 講座ID {lecture_id}, 講師ID {teacher_data.teacher_id}")
        
        return MultiTeacherLectureResponse(
            message="講座に講師を追加しました",
            lecture_id=lecture_id,
            affected_teacher_id=teacher_data.teacher_id
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"講座に講師追加エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.delete("/{lecture_id}/teachers/{teacher_id}", response_model=MultiTeacherLectureResponse)
async def remove_teacher_from_lecture(
    lecture_id: int,
    teacher_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    多讲师講座から講師を削除するAPI（管理者のみ）
    
    Args:
        lecture_id: 講座ID
        teacher_id: 削除する講師ID
        current_user: 現在のユーザー（管理者権限が必要）
        db: データベースセッション
    
    Returns:
        MultiTeacherLectureResponse: 操作結果
    
    Raises:
        HTTPException: 権限不足、講座不存在、講師不存在、サーバーエラー時
    """
    logger.info(f"講座から講師削除リクエスト: 講座ID {lecture_id}, 講師ID {teacher_id} by {current_user.email}")
    
    try:
        # 講座が存在し、多讲师講座かどうかをチェック
        lecture = db.query(Lecture).filter(
            Lecture.id == lecture_id,
            Lecture.is_deleted == False
        ).first()
        
        if not lecture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された講座が見つかりません"
            )
        
        if not lecture.is_multi_teacher:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="この講座は多讲师講座ではありません"
            )
        
        # 講座の主讲讲师は削除できない（lecturesテーブルのteacher_id）
        if teacher_id == lecture.teacher_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="講座の主讲讲师は削除できません。主讲讲师を変更する場合は、別のAPIを使用してください"
            )
        
        # 削除する講師がこの講座に参加しているかチェック
        lecture_teacher = db.query(LectureTeacher).filter(
            LectureTeacher.lecture_id == lecture_id,
            LectureTeacher.teacher_id == teacher_id
        ).first()
        
        if not lecture_teacher:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された講師はこの講座に参加していません"
            )
        
        # 講師-講座関連レコードを削除
        db.delete(lecture_teacher)
        db.commit()
        
        logger.info(f"講座から講師削除成功: 講座ID {lecture_id}, 講師ID {teacher_id}")
        
        return MultiTeacherLectureResponse(
            message="講座から講師を削除しました",
            lecture_id=lecture_id,
            affected_teacher_id=teacher_id
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"講座から講師削除エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )





@router.get("/{lecture_id}/teachers", response_model=List[LectureTeacherOut])
async def get_lecture_teachers(
    lecture_id: int,
    db: Session = Depends(get_db)
):
    """
    講座の全講師リストを取得するAPI（認証不要）
    
    Args:
        lecture_id: 講座ID
        db: データベースセッション
    
    Returns:
        List[LectureTeacherOut]: 講師情報リスト
    
    Raises:
        HTTPException: 講座不存在、サーバーエラー時
    """
    logger.info(f"講座講師リスト取得リクエスト: 講座ID {lecture_id}")
    
    try:
        # 講座が存在するかチェック
        lecture = db.query(Lecture).filter(
            Lecture.id == lecture_id,
            Lecture.is_deleted == False
        ).first()
        
        if not lecture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された講座が見つかりません"
            )
        
        # 多讲师講座かどうかをチェック
        if not lecture.is_multi_teacher:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="この講座は多讲师講座ではありません。多讲师講座のみこのAPIを使用できます"
            )
        
        # 講座の全講師情報を取得（lecture_teachersテーブルから）
        lecture_teachers = db.query(LectureTeacher).filter(
            LectureTeacher.lecture_id == lecture_id
        ).all()
        
        # 講師情報リストを構築
        teacher_list = []
        
        # 1. まず主讲讲师を追加
        primary_teacher_user = db.query(User).filter(
            User.id == lecture.teacher_id,
            User.is_deleted == False
        ).first()
        
        if primary_teacher_user:
            primary_teacher_info = LectureTeacherOut(
                teacher_id=lecture.teacher_id,
                teacher_name=primary_teacher_user.name
            )
            teacher_list.append(primary_teacher_info)
        
        # 2. 次にlecture_teachersテーブルの講師を追加
        for lt in lecture_teachers:
            # 主讲讲师と重複しないようにチェック
            if lt.teacher_id != lecture.teacher_id:
                teacher_user = db.query(User).filter(
                    User.id == lt.teacher_id,
                    User.is_deleted == False
                ).first()
                
                if teacher_user:
                    teacher_info = LectureTeacherOut(
                        teacher_id=lt.teacher_id,
                        teacher_name=teacher_user.name
                    )
                    teacher_list.append(teacher_info)
        
        logger.info(f"講座講師リスト取得成功: 講座ID {lecture_id}, 講師数: {len(teacher_list)}")
        
        return teacher_list
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"講座講師リスト取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )
