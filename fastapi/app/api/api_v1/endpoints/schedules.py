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

# ログ設定
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=ScheduleCreateResponse)
async def create_schedule(
    schedule_data: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    予約可能時間登録API（講師・管理者）
    
    Args:
        schedule_data: 登録するスケジュール情報
            - lecture_id: 講座ID（必須）
            - teacher_id: 講師ID（必須）
            - date: 予約可能日期（YYYY-MM-DD形式）
            - start: 開始時間（HH:MM形式）
            - end: 終了時間（HH:MM形式）
        current_user: 現在のユーザー（講師または管理者）
        db: データベースセッション
    
    Returns:
        ScheduleCreateResponse: 登録結果
    
    Raises:
        HTTPException: 権限不足、講座不存在、講師不存在、時間重複、サーバーエラー時
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
        
        # 同じ講座で同じ日時が重複していないかチェック
        existing_schedule = db.query(LectureSchedule).filter(
            and_(
                LectureSchedule.lecture_id == schedule_data.lecture_id,
                LectureSchedule.booking_date == booking_date,
                LectureSchedule.is_expired == False
            )
        ).first()
        
        if existing_schedule:
            # 時間が重複しているかチェック
            if not (end_time <= existing_schedule.start_time or start_time >= existing_schedule.end_time):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="指定された時間帯は既に他のスケジュールと重複しています"
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


@router.get("/", response_model=List[ScheduleListOut])
async def get_all_schedules(
    db: Session = Depends(get_db)
):
    """
    講座スケジュール一覧取得API（認証不要）
    
    Args:
        db: データベースセッション
    
    Returns:
        List[ScheduleListOut]: スケジュール情報のリスト
    
    Raises:
        HTTPException: サーバーエラー時
    """
    logger.info("講座スケジュール一覧取得リクエスト")
    
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
        ).order_by(
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
