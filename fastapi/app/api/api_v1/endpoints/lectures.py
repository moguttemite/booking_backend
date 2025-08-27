"""
講座関連 API エンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List
import logging
import traceback

from app.models.lecture import Lecture, LectureTeacher, Carousel
from app.models.user import User
from app.models.teacher import TeacherProfile
from app.schemas.lecture import (
    LectureListOut, LectureDetailOut, LectureCreate, LectureCreateResponse, 
    LectureTeacherChange, LectureTeacherChangeResponse,
    MultiTeacherLectureResponse, AddTeacherToLectureRequest, 
    LectureTeacherOut, LectureApprovalUpdate, LectureApprovalUpdateResponse,
    LectureUpdate, LectureUpdateResponse, LectureDeleteResponse,
    CarouselOut, CarouselBatchUpdate, CarouselBatchUpdateResponse,
    CarouselManagementOut
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
            
            # 講師は多讲师講座を作成できません
            if lecture_data.is_multi_teacher:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="講師は多讲师講座を作成することはできません。管理者のみが多讲师講座を作成できます"
                )
            
            # 講師は講座の主讲讲师を指定する必要があり、自分自身のみ指定可能
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
        
        # 管理者の場合
        elif current_user.role == "admin":
            # 管理者は講座の主讲讲师を指定する必要があります
            if not lecture_data.teacher_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="管理者は講座の主讲讲师を指定する必要があります"
                )
            
            # 指定された講師が存在し、講師ロールを持っているかチェック
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
                "is_multi_teacher": lecture.is_multi_teacher,  # 多讲师講座フラグ
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


# ==================== カルーセル（トップページ掲載）管理API ====================

@router.put("/carousel/batch", response_model=CarouselBatchUpdateResponse)
def batch_update_carousel(
    carousel_data: CarouselBatchUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    カルーセル一括更新API（管理者のみ）
    追加・更新・削除を一括で処理
    
    Args:
        carousel_data: カルーセル一覧（完全な状態）
        current_user: 現在のユーザー（管理者権限が必要）
        db: データベースセッション
    
    Returns:
        CarouselBatchUpdateResponse: 更新結果
    
    Raises:
        HTTPException: 権限不足、講座不存在、サーバーエラー時
    """
    logger.info(f"カルーセル一括更新リクエスト: {len(carousel_data.carousel_list)}件 by {current_user.email}")
    logger.info(f"リクエストデータ: {carousel_data}")
    
    try:
        # 既存のカルーセルを削除（空のリストの場合も含む）
        try:
            db.query(Carousel).delete()
            logger.info("既存のカルーセルレコードを削除しました")
        except Exception as e:
            logger.error(f"既存のカルーセル削除エラー: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="既存のカルーセル削除中にエラーが発生しました"
            )
        
        # 空のリストの場合は削除のみで終了
        if not carousel_data.carousel_list:
            db.commit()
            logger.info("カルーセルを空にしました")
            return CarouselBatchUpdateResponse()
        
        # 表示順序の重複チェック
        orders = [item.display_order for item in carousel_data.carousel_list]
        if len(set(orders)) != len(orders):
            # 重複している表示順序を見つける
            from collections import Counter
            duplicate_counts = Counter(orders)
            duplicates = [order for order, count in duplicate_counts.items() if count > 1]
            duplicate_list = ", ".join(map(str, duplicates))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"表示順序に重複があります: {duplicate_list}"
            )
        
        # 表示順序は1から連続している必要がある
        sorted_orders = sorted(orders)
        expected_orders = list(range(1, len(orders) + 1))
        if sorted_orders != expected_orders:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="表示順序は1から連続している必要があります"
            )
        
        # 講座IDの重複チェック
        lecture_ids = [item.lecture_id for item in carousel_data.carousel_list]
        if len(set(lecture_ids)) != len(lecture_ids):
            # 重複している講座IDを見つける
            from collections import Counter
            duplicate_counts = Counter(lecture_ids)
            duplicates = [id for id, count in duplicate_counts.items() if count > 1]
            duplicate_list = ", ".join(map(str, duplicates))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"以下の講座IDが重複しています: {duplicate_list}"
            )
        
        # 講座IDの存在性チェック（シンプル版）
        existing_lectures = db.query(Lecture).filter(
            Lecture.id.in_(lecture_ids),
            Lecture.is_deleted == False
        ).all()
        
        existing_lecture_ids = {lecture.id for lecture in existing_lectures}
        missing_lecture_ids = set(lecture_ids) - existing_lecture_ids
        
        if missing_lecture_ids:
            missing_list = ", ".join(map(str, missing_lecture_ids))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"以下の講座IDが存在しません: {missing_list}"
            )
        
        # 新しいカルーセルレコードを作成
        carousel_records = []
        for item in carousel_data.carousel_list:
            carousel = Carousel(
                lecture_id=item.lecture_id,
                display_order=item.display_order,
                is_active=item.is_active
            )
            carousel_records.append(carousel)
        
        # データベースに保存
        try:
            db.add_all(carousel_records)
            db.commit()
            logger.info(f"カルーセル更新完了: {len(carousel_records)}件")
        except Exception as e:
            db.rollback()
            logger.error(f"データベース保存エラー: {str(e)}")
            
            # 具体的なエラーメッセージを提供
            error_message = str(e)
            if "duplicate key" in error_message.lower() or "unique constraint" in error_message.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="講座IDまたは表示順序が重複しています。各講座は一度だけカルーセルに掲載でき、表示順序は重複できません。"
                )
            elif "foreign key constraint" in error_message.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="指定された講座IDが存在しません。"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"データベース保存中にエラーが発生しました: {error_message}"
                )
        
        return CarouselBatchUpdateResponse()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"予期しないエラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.get("/carousel", response_model=List[CarouselOut])
def get_carousel_lectures(
    db: Session = Depends(get_db)
):
    """
    カルーセル掲載講座一覧取得API（フロントエンド表示用、認証不要）
    
    Args:
        db: データベースセッション
    
    Returns:
        List[CarouselOut]: カルーセル掲載講座一覧（表示用）
    
    Raises:
        HTTPException: サーバーエラー時
    """
    logger.info("カルーセル掲載講座一覧取得リクエスト（フロントエンド表示用）")
    
    try:
        # アクティブなカルーセル掲載講座を表示順序順に取得
        carousel_lectures = db.query(
            Carousel, Lecture, User
        ).join(
            Lecture, Carousel.lecture_id == Lecture.id
        ).join(
            User, Lecture.teacher_id == User.id
        ).filter(
            Carousel.is_active == True,
            Lecture.is_deleted == False,
            Lecture.approval_status == "approved",
            User.is_deleted == False
        ).order_by(
            Carousel.display_order
        ).all()
        
        # 結果をCarouselOutモデルに変換
        carousel_list = []
        for carousel, lecture, user in carousel_lectures:
            # 多讲师講座かどうかをチェック
            if lecture.is_multi_teacher:
                teacher_name = "複数講師"
            else:
                teacher_name = user.name
            
            carousel_info = CarouselOut(
                lecture_id=carousel.lecture_id,
                lecture_title=lecture.lecture_title,
                lecture_description=lecture.lecture_description,
                teacher_name=teacher_name,
                display_order=carousel.display_order
            )
            carousel_list.append(carousel_info)
        
        logger.info(f"カルーセル掲載講座一覧取得成功: {len(carousel_list)}件")
        
        return carousel_list
        
    except Exception as e:
        logger.error(f"カルーセル掲載講座一覧取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.get("/carousel/management", response_model=List[CarouselManagementOut])
def get_carousel_management_list(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    カルーセル管理用一覧取得API（管理者のみ）
    
    Args:
        current_user: 現在のユーザー（管理者権限が必要）
        db: データベースセッション
    
    Returns:
        List[CarouselManagementOut]: カルーセル管理用一覧（管理画面用）
    
    Raises:
        HTTPException: 権限不足、サーバーエラー時
    """
    logger.info(f"カルーセル管理用一覧取得リクエスト by {current_user.email}")
    
    try:
        # カルーセル掲載講座を表示順序順に取得（管理用）
        carousel_list = db.query(Carousel, Lecture).join(
            Lecture, Carousel.lecture_id == Lecture.id
        ).filter(
            Carousel.is_active == True,
            Lecture.is_deleted == False
        ).order_by(
            Carousel.display_order
        ).all()
        
        # 結果をCarouselManagementOutモデルに変換
        management_list = []
        for carousel, lecture in carousel_list:
            management_info = CarouselManagementOut(
                lecture_id=carousel.lecture_id,
                lecture_title=lecture.lecture_title,
                display_order=carousel.display_order,
                is_active=carousel.is_active
            )
            management_list.append(management_info)
        
        logger.info(f"カルーセル管理用一覧取得成功: {len(management_list)}件")
        
        return management_list
        
    except Exception as e:
        logger.error(f"カルーセル管理用一覧取得エラー: {str(e)}")
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
            "teacher_name": user.name,
            "approval_status": lecture.approval_status,
            "is_multi_teacher": lecture.is_multi_teacher,
            "created_at": lecture.created_at,
            "updated_at": lecture.updated_at
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


# ==================== 多讲师講座管理API ====================

@router.post("/{lecture_id}/teachers", response_model=MultiTeacherLectureResponse)
async def add_teacher_to_lecture(
    lecture_id: int,
    request: AddTeacherToLectureRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    多讲师講座に講師を追加API（管理者のみ）
    
    Args:
        lecture_id: 講座ID
        request: 追加する講師情報
        current_user: 現在のユーザー（管理者権限が必要）
        db: データベースセッション
    
    Returns:
        MultiTeacherLectureResponse: 追加結果
    
    Raises:
        HTTPException: 権限不足、講座不存在、講師不存在、サーバーエラー時
    """
    logger.info(f"多讲师講座に講師追加リクエスト: 講座ID {lecture_id}, 講師ID {request.teacher_id} by {current_user.email}")
    
    try:
        # 講座の存在性と多讲师講座かどうかをチェック
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
        
        # 追加する講師の存在性と講師ロールをチェック
        teacher = db.query(User).filter(
            User.id == request.teacher_id,
            User.role == "teacher",
            User.is_deleted == False
        ).first()
        
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="指定された講師が見つからないか、講師ロールを持っていません"
            )
        
        # 講師プロフィールの存在性をチェック
        teacher_profile = db.query(TeacherProfile).filter(
            TeacherProfile.id == request.teacher_id
        ).first()
        
        if not teacher_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="指定された講師のプロフィールが存在しません"
            )
        
        # 既にこの講座に参加しているかチェック
        existing_teacher = db.query(LectureTeacher).filter(
            LectureTeacher.lecture_id == lecture_id,
            LectureTeacher.teacher_id == request.teacher_id
        ).first()
        
        if existing_teacher:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="指定された講師は既にこの講座に参加しています"
            )
        
        # 講師を講座に追加
        new_lecture_teacher = LectureTeacher(
            lecture_id=lecture_id,
            teacher_id=request.teacher_id
        )
        
        db.add(new_lecture_teacher)
        db.commit()
        
        logger.info(f"多讲师講座に講師追加完了: 講座ID {lecture_id}, 講師ID {request.teacher_id}")
        
        return MultiTeacherLectureResponse(
            message="講師の追加が完了しました",
            lecture_id=lecture_id,
            teacher_id=request.teacher_id
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"多讲师講座に講師追加エラー: {str(e)}")
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
    多讲师講座から講師を削除API（管理者のみ）
    
    Args:
        lecture_id: 講座ID
        teacher_id: 削除する講師ID
        current_user: 現在のユーザー（管理者権限が必要）
        db: データベースセッション
    
    Returns:
        MultiTeacherLectureResponse: 削除結果
    
    Raises:
        HTTPException: 権限不足、講座不存在、講師不存在、サーバーエラー時
    """
    logger.info(f"多讲师講座から講師削除リクエスト: 講座ID {lecture_id}, 講師ID {teacher_id} by {current_user.email}")
    
    try:
        # 講座の存在性と多讲师講座かどうかをチェック
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
        
        # 主讲讲师は削除できない
        if teacher_id == lecture.teacher_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="講座の主讲讲师は削除できません。主讲讲师を変更する場合は、講座更新APIを使用してください。"
            )
        
        # 講師がこの講座に参加しているかチェック
        lecture_teacher = db.query(LectureTeacher).filter(
            LectureTeacher.lecture_id == lecture_id,
            LectureTeacher.teacher_id == teacher_id
        ).first()
        
        if not lecture_teacher:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="指定された講師はこの講座に参加していません"
            )
        
        # 講師を講座から削除
        db.delete(lecture_teacher)
        db.commit()
        
        logger.info(f"多讲师講座から講師削除完了: 講座ID {lecture_id}, 講師ID {teacher_id}")
        
        return MultiTeacherLectureResponse(
            message="講師の削除が完了しました",
            lecture_id=lecture_id,
            teacher_id=teacher_id
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"多讲师講座から講師削除エラー: {str(e)}")
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
    多讲师講座の講師一覧取得API（認証不要）
    
    Args:
        lecture_id: 講座ID
        db: データベースセッション
    
    Returns:
        List[LectureTeacherOut]: 講師一覧
    
    Raises:
        HTTPException: 講座不存在、多讲师講座ではない、サーバーエラー時
    """
    logger.info(f"多讲师講座の講師一覧取得リクエスト: 講座ID {lecture_id}")
    
    try:
        # 講座の存在性と多讲师講座かどうかをチェック
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
        
        # 主讲讲师を含む講師一覧を取得
        teachers = []
        
        # 主讲讲师を取得
        main_teacher = db.query(User).filter(
            User.id == lecture.teacher_id,
            User.is_deleted == False
        ).first()
        
        if main_teacher:
            teachers.append(LectureTeacherOut(
                teacher_id=lecture.teacher_id,
                teacher_name=main_teacher.name
            ))
        
        # 追加講師を取得
        additional_teachers = db.query(LectureTeacher, User).join(
            User, LectureTeacher.teacher_id == User.id
        ).filter(
            LectureTeacher.lecture_id == lecture_id,
            User.is_deleted == False
        ).all()
        
        for lecture_teacher, user in additional_teachers:
            teachers.append(LectureTeacherOut(
                teacher_id=user.id,
                teacher_name=user.name
            ))
        
        logger.info(f"多讲师講座の講師一覧取得成功: 講座ID {lecture_id}, 講師数 {len(teachers)}人")
        
        return teachers
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"多讲师講座の講師一覧取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.put("/{lecture_id}/teachers", response_model=LectureTeacherChangeResponse)
async def change_lecture_teacher(
    lecture_id: int,
    request: LectureTeacherChange,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    講座の主讲讲师変更API（管理者のみ）
    
    Args:
        lecture_id: 講座ID
        request: 変更する講師情報
        current_user: 現在のユーザー（管理者権限が必要）
        db: データベースセッション
    
    Returns:
        LectureTeacherChangeResponse: 変更結果
    
    Raises:
        HTTPException: 権限不足、講座不存在、講師不存在、サーバーエラー時
    """
    logger.info(f"講座の主讲讲师変更リクエスト: 講座ID {lecture_id}, 新しい講師ID {request.teacher_id} by {current_user.email}")
    
    try:
        # 講座の存在性をチェック
        lecture = db.query(Lecture).filter(
            Lecture.id == lecture_id,
            Lecture.is_deleted == False
        ).first()
        
        if not lecture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された講座が見つかりません"
            )
        
        # 多讲师講座の場合、多讲师管理APIを使用するように案内
        if lecture.is_multi_teacher:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="多讲师講座はこのAPIで変更できません。多讲师管理APIを使用してください。"
            )
        
        # 新しい講師の存在性と講師ロールをチェック
        new_teacher = db.query(User).filter(
            User.id == request.teacher_id,
            User.role == "teacher",
            User.is_deleted == False
        ).first()
        
        if not new_teacher:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="指定された講師が見つからないか、講師ロールを持っていません"
            )
        
        # 講師プロフィールの存在性をチェック
        teacher_profile = db.query(TeacherProfile).filter(
            TeacherProfile.id == request.teacher_id
        ).first()
        
        if not teacher_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="指定された講師のプロフィールが存在しません"
            )
        
        # 既に同じ講師が指定されているかチェック
        if lecture.teacher_id == request.teacher_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="指定された講師は既にこの講座の主讲讲师です"
            )
        
        # 旧講師を追加講師リストから削除（多讲师講座の場合）
        if lecture.is_multi_teacher:
            old_lecture_teacher = db.query(LectureTeacher).filter(
                LectureTeacher.lecture_id == lecture_id,
                LectureTeacher.teacher_id == lecture.teacher_id
            ).first()
            
            if old_lecture_teacher:
                db.delete(old_lecture_teacher)
        
        # 新講師を追加講師リストに追加（多讲师講座の場合）
        if lecture.is_multi_teacher:
            new_lecture_teacher = LectureTeacher(
                lecture_id=lecture_id,
                teacher_id=request.teacher_id
            )
            db.add(new_lecture_teacher)
        
        # 主讲讲师を更新
        lecture.teacher_id = request.teacher_id
        db.commit()
        
        logger.info(f"講座の主讲讲师変更完了: 講座ID {lecture_id}, 新しい講師ID {request.teacher_id}")
        
        return LectureTeacherChangeResponse(
            message="講座の主讲讲师の変更が完了しました",
            lecture_id=lecture_id,
            old_teacher_id=lecture.teacher_id,
            new_teacher_id=request.teacher_id
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"講座の主讲讲师変更エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


# ==================== 講座審査・管理API ====================

@router.put("/{lecture_id}/approval", response_model=LectureApprovalUpdateResponse)
async def update_lecture_approval_status(
    lecture_id: int,
    approval_data: LectureApprovalUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    講座審査状態更新API（管理者のみ）
    
    Args:
        lecture_id: 講座ID
        approval_data: 更新する審査状態
        current_user: 現在のユーザー（管理者権限が必要）
        db: データベースセッション
    
    Returns:
        LectureApprovalUpdateResponse: 更新結果
    
    Raises:
        HTTPException: 権限不足、講座不存在、サーバーエラー時
    """
    logger.info(f"講座審査状態更新リクエスト: 講座ID {lecture_id}, 新しい状態 {approval_data.approval_status} by {current_user.email}")
    
    try:
        # 講座の存在性をチェック
        lecture = db.query(Lecture).filter(
            Lecture.id == lecture_id,
            Lecture.is_deleted == False
        ).first()
        
        if not lecture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された講座が見つかりません"
            )
        
        # 審査状態の妥当性をチェック
        valid_statuses = ["pending", "approved", "rejected"]
        if approval_data.approval_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="審査状態は pending、approved、rejected のいずれかである必要があります"
            )
        
        # 審査状態を更新
        lecture.approval_status = approval_data.approval_status
        db.commit()
        
        logger.info(f"講座審査状態更新完了: 講座ID {lecture_id}, 新しい状態 {approval_data.approval_status}")
        
        return LectureApprovalUpdateResponse()
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"講座審査状態更新エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.put("/{lecture_id}/update", response_model=LectureUpdateResponse)
async def update_lecture(
    lecture_id: int,
    update_data: LectureUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    講座更新API（管理者のみ）
    
    Args:
        lecture_id: 講座ID
        update_data: 更新する講座情報
        current_user: 現在のユーザー（管理者権限が必要）
        db: データベースセッション
    
    Returns:
        LectureUpdateResponse: 更新結果
    
    Raises:
        HTTPException: 権限不足、講座不存在、サーバーエラー時
    """
    logger.info(f"講座更新リクエスト: 講座ID {lecture_id} by {current_user.email}")
    
    try:
        # 講座の存在性をチェック
        lecture = db.query(Lecture).filter(
            Lecture.id == lecture_id,
            Lecture.is_deleted == False
        ).first()
        
        if not lecture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された講座が見つかりません"
            )
        
        # 講座情報を更新
        if update_data.lecture_title is not None:
            lecture.lecture_title = update_data.lecture_title
        
        if update_data.lecture_description is not None:
            lecture.lecture_description = update_data.lecture_description
        
        db.commit()
        
        logger.info(f"講座更新完了: 講座ID {lecture_id}")
        
        return LectureUpdateResponse()
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"講座更新エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.delete("/{lecture_id}", response_model=LectureDeleteResponse)
async def delete_lecture(
    lecture_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    講座削除API（管理者のみ、ソフト削除）
    
    Args:
        lecture_id: 講座ID
        current_user: 現在のユーザー（管理者権限が必要）
        db: データベースセッション
    
    Returns:
        LectureDeleteResponse: 削除結果
    
    Raises:
        HTTPException: 権限不足、講座不存在、サーバーエラー時
    """
    logger.info(f"講座削除リクエスト: 講座ID {lecture_id} by {current_user.email}")
    
    try:
        # 講座の存在性をチェック
        lecture = db.query(Lecture).filter(
            Lecture.id == lecture_id,
            Lecture.is_deleted == False
        ).first()
        
        if not lecture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された講座が見つかりません"
            )
        
        # ソフト削除を実行
        lecture.is_deleted = True
        lecture.deleted_at = func.now()
        db.commit()
        
        logger.info(f"講座削除完了: 講座ID {lecture_id}")
        
        return LectureDeleteResponse(
            title=lecture.lecture_title,
            message="講座の削除が完了しました"
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"講座削除エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )
