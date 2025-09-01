"""
講座スケジュール管理 API エンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List
import logging
import traceback
from datetime import datetime, date, time

from app.models.lecture import Lecture
from app.models.booking import LectureSchedule
from app.models.user import User
from app.models.teacher import TeacherProfile
from app.schemas.booking import (
    ScheduleCreate, ScheduleCreateResponse, ScheduleOut, ScheduleListOut
)
from app.utils.jwt import get_current_user, get_current_admin
from app.db.database import get_db
from app.models.booking import LectureBooking

# ログ設定
logger = logging.getLogger(__name__)

router = APIRouter()


def check_time_conflicts(
    db: Session, 
    lecture_id: int, 
    booking_date: date, 
    start_time: time, 
    end_time: time, 
    exclude_id: int = None
) -> tuple[bool, LectureSchedule | None]:
    """
    時間重複チェック関数
    """
    query = db.query(LectureSchedule).filter(
        and_(
            LectureSchedule.lecture_id == lecture_id,
            LectureSchedule.booking_date == booking_date,
            LectureSchedule.is_expired == False
        )
    )
    
    if exclude_id:
        query = query.filter(LectureSchedule.id != exclude_id)
    
    conflicting_schedules = query.all()
    
    for schedule in conflicting_schedules:
        if (start_time < schedule.end_time and end_time > schedule.start_time):
            return True, schedule
    
    return False, None


@router.post("/", response_model=ScheduleCreateResponse)
async def create_schedule(
    schedule_data: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    予約可能時間登録API（講師・管理者）
    """
    logger.info(f"予約可能時間登録リクエスト: 講座ID {schedule_data.lecture_id}, 講師ID {schedule_data.teacher_id} by {current_user.email}")
    
    try:
        # 権限チェック：講師または管理者のみアクセス可能
        if current_user.role not in ["teacher", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この操作を実行する権限がありません。講師または管理者権限が必要です"
            )
        
        # 講座の存在性をチェック
        lecture = db.query(Lecture).filter(
            Lecture.id == schedule_data.lecture_id,
            Lecture.is_deleted == False
        ).first()
        
        if not lecture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された講座が見つかりません"
            )
        
        # 講師の場合、自分が担当する講座のみ登録可能
        if current_user.role == "teacher":
            if lecture.teacher_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="講師は自分が担当する講座のスケジュールのみ登録できます"
                )
            
            # teacher_idは自分自身である必要がある
            if schedule_data.teacher_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="講師は自分自身のIDのみ指定できます"
                )
        
        # 管理者の場合、指定された講師が存在するかチェック
        elif current_user.role == "admin":
            teacher = db.query(User).filter(
                User.id == schedule_data.teacher_id,
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
                TeacherProfile.id == schedule_data.teacher_id
            ).first()
            
            if not teacher_profile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="指定された講師のプロフィールが存在しません"
                )
        
        # 日付と時間の形式を変換
        try:
            booking_date = datetime.strptime(schedule_data.date, "%Y-%m-%d").date()
            start_time = datetime.strptime(schedule_data.start, "%H:%M").time()
            end_time = datetime.strptime(schedule_data.end, "%H:%M").time()
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"日付または時間の形式が正しくありません: {str(e)}"
            )
        
        # 開始時間が終了時間より前であることをチェック
        if start_time >= end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="開始時間は終了時間より前である必要があります"
            )
        
        # 過去の日付でないことをチェック
        if booking_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="過去の日付にはスケジュールを登録できません"
            )
        
        # 時間衝突チェック
        has_conflict, conflicting_schedule = check_time_conflicts(
            db, schedule_data.lecture_id, booking_date, start_time, end_time
        )
        
        if has_conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"指定された時間帯は既に他のスケジュールと重複しています。既存の時間: {conflicting_schedule.start_time}-{conflicting_schedule.end_time}"
            )
        
        # 新しいスケジュールを作成
        new_schedule = LectureSchedule(
            lecture_id=schedule_data.lecture_id,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time
        )
        
        # データベースに保存
        db.add(new_schedule)
        db.commit()
        db.refresh(new_schedule)
        
        logger.info(f"予約可能時間登録完了: スケジュールID {new_schedule.id}, 講座ID {schedule_data.lecture_id}, 日付 {booking_date}, 時間 {start_time}-{end_time}")
        
        return ScheduleCreateResponse(
            schedule_id=new_schedule.id
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"予約可能時間登録エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.delete("/{schedule_id}", response_model=dict)
async def delete_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    予約可能時間削除API（講師・管理者）
    
    Args:
        schedule_id: 削除するスケジュールID
        current_user: 現在のユーザー（講師または管理者）
        db: データベースセッション
    
    Returns:
        dict: 削除結果
    
    Raises:
        HTTPException: 権限不足、スケジュール不存在、サーバーエラー時
    """
    logger.info(f"予約可能時間削除リクエスト: スケジュールID {schedule_id} by {current_user.email}")
    
    try:
        # 権限チェック：講師または管理者のみアクセス可能
        if current_user.role not in ["teacher", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この操作を実行する権限がありません。講師または管理者権限が必要です"
            )
        
        # スケジュールの存在性をチェック
        schedule = db.query(LectureSchedule).filter(
            LectureSchedule.id == schedule_id,
            LectureSchedule.is_expired == False
        ).first()
        
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたスケジュールが見つかりません"
            )
        
        # 講座の存在性をチェック
        lecture = db.query(Lecture).filter(
            Lecture.id == schedule.lecture_id,
            Lecture.is_deleted == False
        ).first()
        
        if not lecture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="関連する講座が見つかりません"
            )
        
        # 講師の場合、自分が担当する講座のスケジュールのみ削除可能
        if current_user.role == "teacher":
            if lecture.teacher_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="講師は自分が担当する講座のスケジュールのみ削除できます"
                )
        
        # スケジュールを削除（物理削除ではなく論理削除）
        schedule.is_expired = True
        db.commit()
        
        logger.info(f"予約可能時間削除完了: スケジュールID {schedule_id}")
        
        return {
            "success": True,
            "message": "予約可能時間の削除が完了しました",
            "schedule_id": schedule_id
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"予約可能時間削除エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.get("/", response_model=List[ScheduleListOut])
async def get_all_schedules(
    lecture_id: int = None,
    teacher_id: int = None,
    db: Session = Depends(get_db)
):
    """
    講座スケジュール一覧取得API（認証不要）
    
    Args:
        lecture_id: 講座ID（オプション）
        teacher_id: 講師ID（オプション）
        db: データベースセッション
    
    Returns:
        List[ScheduleListOut]: スケジュール情報のリスト
    
    Raises:
        HTTPException: サーバーエラー時
    """
    logger.info(f"講座スケジュール一覧取得リクエスト: 講座ID {lecture_id}, 講師ID {teacher_id}")
    
    try:
        # 削除されていない講座のスケジュールを全て取得
        query = db.query(
            LectureSchedule, Lecture, User
        ).join(
            Lecture, LectureSchedule.lecture_id == Lecture.id
        ).join(
            User, Lecture.teacher_id == User.id
        ).filter(
            Lecture.is_deleted == False,
            User.is_deleted == False,
            LectureSchedule.is_expired == False
        )
        
        # フィルタリング
        if lecture_id:
            query = query.filter(LectureSchedule.lecture_id == lecture_id)
        
        if teacher_id:
            query = query.filter(Lecture.teacher_id == teacher_id)
        
        # ソート
        query = query.order_by(
            LectureSchedule.booking_date.asc(),
            LectureSchedule.start_time.asc()
        )
        
        schedules = query.all()
        
        logger.info(f"講座スケジュール一覧取得成功: {len(schedules)}件")
        
        # 結果をScheduleListOutモデルに変換
        schedule_list = []
        for schedule, lecture, user in schedules:
            schedule_data = {
                "id": schedule.id,
                "lecture_id": schedule.lecture_id,
                "lecture_title": lecture.lecture_title,
                "teacher_name": user.name,
                "booking_date": schedule.booking_date,
                "start_time": schedule.start_time,
                "end_time": schedule.end_time,
                "created_at": schedule.created_at
            }
            schedule_list.append(ScheduleListOut(**schedule_data))
        
        return schedule_list
        
    except Exception as e:
        logger.error(f"講座スケジュール一覧取得エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.get("/lecture/{lecture_id}", response_model=List[ScheduleOut])
async def get_schedules_by_lecture(
    lecture_id: int,
    db: Session = Depends(get_db)
):
    """
    特定講座のスケジュール一覧取得API（認証不要）
    
    Args:
        lecture_id: 講座ID
        db: データベースセッション
    
    Returns:
        List[ScheduleOut]: スケジュール情報のリスト
    
    Raises:
        HTTPException: 講座不存在、サーバーエラー時
    """
    logger.info(f"特定講座のスケジュール一覧取得リクエスト: 講座ID {lecture_id}")
    
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
        
        # 指定された講座のスケジュールを取得
        schedules = db.query(LectureSchedule).filter(
            and_(
                LectureSchedule.lecture_id == lecture_id,
                LectureSchedule.is_expired == False
            )
        ).order_by(
            LectureSchedule.booking_date.asc(),
            LectureSchedule.start_time.asc()
        ).all()
        
        logger.info(f"特定講座のスケジュール一覧取得成功: 講座ID {lecture_id}, {len(schedules)}件")
        
        return schedules
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"特定講座のスケジュール一覧取得エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.get("/{schedule_id}", response_model=ScheduleOut)
async def get_schedule_by_id(
    schedule_id: int,
    db: Session = Depends(get_db)
):
    """
    特定スケジュール詳細取得API（認証不要）
    
    Args:
        schedule_id: スケジュールID
        db: データベースセッション
    
    Returns:
        ScheduleOut: スケジュール詳細情報
    
    Raises:
        HTTPException: スケジュール不存在、サーバーエラー時
    """
    logger.info(f"特定スケジュール詳細取得リクエスト: スケジュールID {schedule_id}")
    
    try:
        # 指定されたIDのスケジュールを取得
        schedule = db.query(LectureSchedule).filter(
            LectureSchedule.id == schedule_id,
            LectureSchedule.is_expired == False
        ).first()
        
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたスケジュールが見つかりません"
            )
        
        logger.info(f"特定スケジュール詳細取得成功: スケジュールID {schedule_id}")
        
        return schedule
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"特定スケジュール詳細取得エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.get("/lecture-schedules", response_model=List[dict])
async def get_lecture_schedules_for_frontend(
    db: Session = Depends(get_db)
):
    """
    フロントエンド互換講座スケジュール取得API
    """
    logger.info("フロントエンド互換講座スケジュール取得リクエスト")
    
    try:
            schedules = db.query(
                LectureSchedule, Lecture, User
            ).join(
                Lecture, LectureSchedule.lecture_id == Lecture.id
            ).join(
                User, Lecture.teacher_id == User.id
            ).filter(
                Lecture.is_deleted == False,
                User.is_deleted == False,
                LectureSchedule.is_expired == False
            ).order_by(
                LectureSchedule.booking_date.asc(),
                LectureSchedule.start_time.asc()
            ).all()
            
            frontend_schedules = []
            for schedule, lecture, user in schedules:
                frontend_schedule = {
                    "id": schedule.id,
                    "lecture_id": schedule.lecture_id,
                    "teacher_id": user.id,
                    "date": schedule.booking_date.strftime("%Y-%m-%d"),
                    "start": schedule.start_time.strftime("%H:%M"),
                    "end": schedule.end_time.strftime("%H:%M"),
                    "created_at": schedule.created_at.isoformat() if schedule.created_at else None
                }
                frontend_schedules.append(frontend_schedule)
            
            logger.info(f"フロントエンド互換講座スケジュール取得成功: {len(frontend_schedules)}件")
            return frontend_schedules
        
    except Exception as e:
        logger.error(f"フロントエンド互換講座スケジュール取得エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.post("/lecture-schedules", response_model=dict)
async def create_lecture_schedules_for_frontend(
    request_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    フロントエンド互換講座スケジュール作成API
    """
    logger.info(f"フロントエンド互換講座スケジュール作成リクエスト: {current_user.email}")
    
    try:
        if current_user.role not in ["teacher", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この操作を実行する権限がありません。講師または管理者権限が必要です"
            )
        
        schedules_data = request_data.get("schedules", [])
        if not schedules_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="スケジュールデータが提供されていません"
            )
        
        new_schedules = []
        for schedule_data in schedules_data:
            required_fields = ["lecture_id", "teacher_id", "date", "start", "end"]
            for field in required_fields:
                if field not in schedule_data:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"必須フィールドが不足しています: {field}"
                    )
            
            if current_user.role == "teacher" and schedule_data["teacher_id"] != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="講師は自分自身のIDのみ指定できます"
                )
            
            lecture = db.query(Lecture).filter(
                Lecture.id == schedule_data["lecture_id"],
                Lecture.is_deleted == False
            ).first()
            
            if not lecture:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"講座ID {schedule_data['lecture_id']} が見つかりません"
                )
            
            if current_user.role == "teacher" and lecture.teacher_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="講師は自分が担当する講座のスケジュールのみ登録できます"
                )
            
            try:
                booking_date = datetime.strptime(schedule_data["date"], "%Y-%m-%d").date()
                start_time = datetime.strptime(schedule_data["start"], "%H:%M").time()
                end_time = datetime.strptime(schedule_data["end"], "%H:%M").time()
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"日付または時間の形式が正しくありません: {str(e)}"
                )
            
            if start_time >= end_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="開始時間は終了時間より前である必要があります"
                )
            
            if booking_date < date.today():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"過去の日付にはスケジュールを登録できません: {schedule_data['date']}"
                )
            
            has_conflict, conflicting_schedule = check_time_conflicts(
                db, schedule_data["lecture_id"], booking_date, start_time, end_time
            )
            
            if has_conflict:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"日付 {schedule_data['date']} の指定された時間帯は既に他のスケジュールと重複しています。既存の時間: {conflicting_schedule.start_time}-{conflicting_schedule.end_time}"
                )
            
            new_schedule = LectureSchedule(
                lecture_id=schedule_data["lecture_id"],
                booking_date=booking_date,
                start_time=start_time,
                end_time=end_time
            )
            new_schedules.append(new_schedule)
        
        db.add_all(new_schedules)
        db.commit()
        
        logger.info(f"フロントエンド互換講座スケジュール作成成功: {len(new_schedules)}件")
        
        return {
            "success": True,
            "message": f"{len(new_schedules)}件の時間枠を登録しました",
            "created_count": len(new_schedules)
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"フロントエンド互換講座スケジュール作成エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.delete("/date/{target_date}", response_model=dict)
async def delete_schedules_by_date(
    target_date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    指定日の全可予約時間削除API（教師のみ）
    """
    logger.info(f"指定日可予約時間削除リクエスト: 日付 {target_date} by {current_user.email}")
    
    try:
        if current_user.role != "teacher":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この操作を実行する権限がありません。教師権限が必要です"
            )
        
        try:
            target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="日付の形式が正しくありません。YYYY-MM-DD形式で入力してください"
            )
        
        if target_date_obj < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="過去の日付のスケジュールは削除できません"
            )
        
        schedules_to_delete = db.query(LectureSchedule).join(
            Lecture, LectureSchedule.lecture_id == Lecture.id
        ).filter(
            and_(
                LectureSchedule.booking_date == target_date_obj,
                Lecture.teacher_id == current_user.id,
                Lecture.is_deleted == False,
                LectureSchedule.is_expired == False
            )
        ).all()
        
        if not schedules_to_delete:
            return {
                "success": True,
                "message": f"日付 {target_date} に削除可能なスケジュールがありません",
                "deleted_count": 0
            }
        
        for schedule in schedules_to_delete:
            existing_booking = db.query(LectureBooking).filter(
                and_(
                    LectureBooking.lecture_id == schedule.lecture_id,
                    LectureBooking.booking_date == schedule.booking_date,
                    LectureBooking.start_time == schedule.start_time,
                    LectureBooking.end_time == schedule.end_time,
                    LectureBooking.status.in_(["pending", "confirmed"]),
                    LectureBooking.is_expired == False
                )
            ).first()
            
            if existing_booking:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"日付 {target_date} の時間帯 {schedule.start_time}-{schedule.end_time} は既に予約されているため削除できません"
                )
        
        deleted_count = 0
        for schedule in schedules_to_delete:
            schedule.is_expired = True
            deleted_count += 1
        
        db.commit()
        
        logger.info(f"指定日可予約時間削除完了: 日付 {target_date}, 削除件数 {deleted_count}")
        
        return {
            "success": True,
            "message": f"日付 {target_date} の {deleted_count}件の可予約時間を削除しました",
            "deleted_count": deleted_count,
            "target_date": target_date
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"指定日可予約時間削除エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )


@router.delete("/lecture/{lecture_id}/all", response_model=dict)
async def delete_all_schedules_by_lecture(
    lecture_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    指定講座の全可予約時間削除API（教師のみ）
    """
    logger.info(f"指定講座全可予約時間削除リクエスト: 講座ID {lecture_id} by {current_user.email}")
    
    try:
        if current_user.role != "teacher":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この操作を実行する権限がありません。教師権限が必要です"
            )
        
        lecture = db.query(Lecture).filter(
            and_(
                Lecture.id == lecture_id,
                Lecture.is_deleted == False
            )
        ).first()
        
        if not lecture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された講座が見つかりません"
            )
        
        if lecture.teacher_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この講座のスケジュールを削除する権限がありません。自分が担当する講座のみ削除できます"
            )
        
        schedules_to_delete = db.query(LectureSchedule).filter(
            and_(
                LectureSchedule.lecture_id == lecture_id,
                LectureSchedule.is_expired == False
            )
        ).all()
        
        if not schedules_to_delete:
            return {
                "success": True,
                "message": f"講座ID {lecture_id} に削除可能なスケジュールがありません",
                "deleted_count": 0
            }
        
        for schedule in schedules_to_delete:
            existing_booking = db.query(LectureBooking).filter(
                and_(
                    LectureBooking.lecture_id == schedule.lecture_id,
                    LectureBooking.booking_date == schedule.booking_date,
                    LectureBooking.start_time == schedule.start_time,
                    LectureBooking.end_time == schedule.end_time,
                    LectureBooking.status.in_(["pending", "confirmed"]),
                    LectureBooking.is_expired == False
                )
            ).first()
            
            if existing_booking:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"日付 {schedule.booking_date} の時間帯 {schedule.start_time}-{schedule.end_time} は既に予約されているため削除できません"
                )
        
        deleted_count = 0
        for schedule in schedules_to_delete:
            schedule.is_expired = True
            deleted_count += 1
        
        db.commit()
        
        logger.info(f"指定講座全可予約時間削除完了: 講座ID {lecture_id}, 削除件数 {deleted_count}")
        
        return {
            "success": True,
            "message": f"講座ID {lecture_id} の {deleted_count}件の可予約時間を削除しました",
            "deleted_count": deleted_count,
            "lecture_id": lecture_id,
            "lecture_title": lecture.lecture_title
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"指定講座全可予約時間削除エラー: {str(e)}")
        logger.error(f"エラーの詳細: {type(e).__name__}")
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )
