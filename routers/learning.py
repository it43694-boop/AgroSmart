from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth
from services.social_training_service import (
    create_learning_course,
    list_learning_courses,
    enroll_in_course,
    update_course_progress,
    list_user_enrollments,
    create_webinar,
    list_webinars,
    register_webinar,
)
from utils import _raise_service_error

router = APIRouter(prefix="/api", tags=["learning"])


@router.post("/learning/courses/", response_model=schemas.LearningCourseResponse)
def create_learning_course_endpoint(course: schemas.LearningCourseCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = create_learning_course(current_user.id, course.dict(), db)
    return db.query(models.LearningCourse).filter(models.LearningCourse.id == result["course_id"]).first()


@router.get("/learning/courses/", response_model=list[schemas.LearningCourseResponse])
def get_learning_courses(
    category: Optional[str] = None,
    level: Optional[str] = None,
    content_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return list_learning_courses(db, category, level, content_type)


@router.post("/learning/courses/{course_id}/enroll/")
def enroll_course_endpoint(course_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = enroll_in_course(current_user.id, course_id, db)
    _raise_service_error(result)
    return result


@router.patch("/learning/courses/{course_id}/progress/")
def update_course_progress_endpoint(
    course_id: int,
    body: schemas.CourseProgressUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    result = update_course_progress(current_user.id, course_id, body.progress_percent, db)
    _raise_service_error(result)
    return result


@router.get("/learning/enrollments/", response_model=list[schemas.LearningEnrollmentResponse])
def get_my_enrollments(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return list_user_enrollments(current_user.id, db)


@router.post("/learning/webinars/", response_model=schemas.WebinarResponse)
def create_webinar_endpoint(webinar: schemas.WebinarCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = create_webinar(current_user.id, webinar.dict(), db)
    return db.query(models.Webinar).filter(models.Webinar.id == result["webinar_id"]).first()


@router.get("/learning/webinars/", response_model=list[schemas.WebinarResponse])
def get_webinars(upcoming: bool = True, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return list_webinars(db, upcoming)


@router.post("/learning/webinars/{webinar_id}/register/", response_model=schemas.WebinarRegistrationResponse)
def register_webinar_endpoint(webinar_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = register_webinar(current_user.id, webinar_id, db)
    _raise_service_error(result)
    return db.query(models.WebinarRegistration).filter(models.WebinarRegistration.id == result["registration_id"]).first()
