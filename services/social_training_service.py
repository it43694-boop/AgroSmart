import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

import models

logger = logging.getLogger("social_training_service")


def create_social_group(user_id: int, payload: Dict[str, Any], db: Session) -> Dict[str, Any]:
    group = models.SocialGroup(
        name=payload.get("name"),
        description=payload.get("description"),
        privacy=payload.get("privacy", "public"),
        creator_id=user_id,
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    membership = models.SocialGroupMember(
        group_id=group.id,
        user_id=user_id,
        role="admin",
        status="active",
    )
    db.add(membership)
    db.commit()

    return {
        "success": True,
        "group_id": group.id,
        "name": group.name,
        "privacy": group.privacy,
        "creator_id": group.creator_id,
    }


def list_social_groups(db: Session, privacy: Optional[str] = None) -> List[Dict[str, Any]]:
    query = db.query(models.SocialGroup)
    if privacy:
        query = query.filter(models.SocialGroup.privacy == privacy)
    groups = query.order_by(models.SocialGroup.created_at.desc()).all()
    return [
        {
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "privacy": g.privacy,
            "creator_id": g.creator_id,
            "created_at": g.created_at,
            "updated_at": g.updated_at,
        }
        for g in groups
    ]


def join_social_group(user_id: int, group_id: int, db: Session) -> Dict[str, Any]:
    existing = db.query(models.SocialGroupMember).filter(
        and_(
            models.SocialGroupMember.group_id == group_id,
            models.SocialGroupMember.user_id == user_id,
        )
    ).first()
    if existing:
        return {"success": False, "error": "Déjà membre de ce groupe"}

    membership = models.SocialGroupMember(
        group_id=group_id,
        user_id=user_id,
        role="member",
        status="active",
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    return {
        "success": True,
        "membership_id": membership.id,
        "group_id": group_id,
        "user_id": user_id,
        "status": membership.status,
    }


def create_social_post(user_id: int, payload: Dict[str, Any], db: Session) -> Dict[str, Any]:
    post = models.SocialPost(
        author_id=user_id,
        group_id=payload.get("group_id"),
        title=payload.get("title"),
        content=payload.get("content"),
        media_url=payload.get("media_url"),
        experience_share=payload.get("experience_share", False),
        tags=payload.get("tags"),
        likes=0,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {
        "success": True,
        "post_id": post.id,
        "author_id": post.author_id,
        "group_id": post.group_id,
        "title": post.title,
        "content": post.content,
        "experience_share": post.experience_share,
        "tags": post.tags,
        "likes": post.likes,
    }


def list_social_posts(db: Session, group_id: Optional[int] = None, experience_share: Optional[bool] = None) -> List[Dict[str, Any]]:
    query = db.query(models.SocialPost)
    if group_id is not None:
        query = query.filter(models.SocialPost.group_id == group_id)
    if experience_share is not None:
        query = query.filter(models.SocialPost.experience_share == experience_share)
    posts = query.order_by(models.SocialPost.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "author_id": p.author_id,
            "group_id": p.group_id,
            "title": p.title,
            "content": p.content,
            "media_url": p.media_url,
            "experience_share": p.experience_share,
            "tags": p.tags,
            "likes": p.likes,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }
        for p in posts
    ]


def add_comment(user_id: int, post_id: int, payload: Dict[str, Any], db: Session) -> Dict[str, Any]:
    comment = models.SocialComment(
        post_id=post_id,
        author_id=user_id,
        content=payload.get("content"),
        parent_comment_id=payload.get("parent_comment_id"),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {
        "success": True,
        "comment_id": comment.id,
        "post_id": comment.post_id,
        "author_id": comment.author_id,
        "content": comment.content,
        "parent_comment_id": comment.parent_comment_id,
    }


def create_learning_course(user_id: int, payload: Dict[str, Any], db: Session) -> Dict[str, Any]:
    course = models.LearningCourse(
        creator_id=user_id,
        title=payload.get("title"),
        description=payload.get("description"),
        video_url=payload.get("video_url"),
        material_url=payload.get("material_url"),
        level=payload.get("level", "beginner"),
        category=payload.get("category"),
        content_type=payload.get("content_type", "course"),
        published=payload.get("published", True),
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return {
        "success": True,
        "course_id": course.id,
        "title": course.title,
    }


def list_post_comments(post_id: int, db: Session) -> List[Dict[str, Any]]:
    comments = (
        db.query(models.SocialComment)
        .filter(models.SocialComment.post_id == post_id)
        .order_by(models.SocialComment.created_at.asc())
        .all()
    )
    return [
        {
            "id": c.id,
            "post_id": c.post_id,
            "author_id": c.author_id,
            "content": c.content,
            "parent_comment_id": c.parent_comment_id,
            "created_at": c.created_at,
        }
        for c in comments
    ]


def like_social_post(user_id: int, post_id: int, db: Session) -> Dict[str, Any]:
    post = db.query(models.SocialPost).filter(models.SocialPost.id == post_id).first()
    if not post:
        return {"success": False, "error": "Publication introuvable"}
    existing = db.query(models.SocialPostLike).filter(
        and_(
            models.SocialPostLike.post_id == post_id,
            models.SocialPostLike.user_id == user_id,
        )
    ).first()
    if existing:
        return {"success": True, "post_id": post_id, "likes": post.likes, "already_liked": True}
    db.add(models.SocialPostLike(post_id=post_id, user_id=user_id))
    post.likes = (post.likes or 0) + 1
    db.commit()
    db.refresh(post)
    return {"success": True, "post_id": post_id, "likes": post.likes, "already_liked": False}


def list_learning_courses(
    db: Session,
    category: Optional[str] = None,
    level: Optional[str] = None,
    content_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query = db.query(models.LearningCourse).filter(models.LearningCourse.published == True)
    if category:
        query = query.filter(models.LearningCourse.category == category)
    if level:
        query = query.filter(models.LearningCourse.level == level)
    if content_type:
        query = query.filter(models.LearningCourse.content_type == content_type)
    courses = query.order_by(models.LearningCourse.created_at.desc()).all()
    return [
        {
            "id": c.id,
            "creator_id": c.creator_id,
            "title": c.title,
            "description": c.description,
            "video_url": c.video_url,
            "material_url": c.material_url,
            "level": c.level,
            "category": c.category,
            "content_type": c.content_type,
            "published": c.published,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }
        for c in courses
    ]


def create_webinar(user_id: int, payload: Dict[str, Any], db: Session) -> Dict[str, Any]:
    webinar = models.Webinar(
        creator_id=user_id,
        title=payload.get("title"),
        description=payload.get("description"),
        scheduled_at=payload.get("scheduled_at"),
        duration_minutes=payload.get("duration_minutes", 60),
        presenter=payload.get("presenter"),
        video_url=payload.get("video_url"),
        registration_link=payload.get("registration_link"),
        max_participants=payload.get("max_participants"),
    )
    db.add(webinar)
    db.commit()
    db.refresh(webinar)
    return {
        "success": True,
        "webinar_id": webinar.id,
        "title": webinar.title,
    }


def list_webinars(db: Session, upcoming: bool = True) -> List[Dict[str, Any]]:
    query = db.query(models.Webinar)
    if upcoming:
        query = query.filter(models.Webinar.scheduled_at >= datetime.utcnow())
    webinars = query.order_by(models.Webinar.scheduled_at.asc()).all()
    return [
        {
            "id": w.id,
            "creator_id": w.creator_id,
            "title": w.title,
            "description": w.description,
            "scheduled_at": w.scheduled_at,
            "duration_minutes": w.duration_minutes,
            "presenter": w.presenter,
            "video_url": w.video_url,
            "registration_link": w.registration_link,
            "max_participants": w.max_participants,
            "created_at": w.created_at,
        }
        for w in webinars
    ]


def register_webinar(user_id: int, webinar_id: int, db: Session) -> Dict[str, Any]:
    existing = db.query(models.WebinarRegistration).filter(
        and_(
            models.WebinarRegistration.webinar_id == webinar_id,
            models.WebinarRegistration.user_id == user_id,
        )
    ).first()
    if existing:
        return {"success": False, "error": "Déjà inscrit à ce webinaire"}

    registration = models.WebinarRegistration(
        webinar_id=webinar_id,
        user_id=user_id,
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return {
        "success": True,
        "registration_id": registration.id,
        "webinar_id": webinar_id,
        "user_id": user_id,
    }


def create_cooperative_training(user_id: int, payload: Dict[str, Any], db: Session) -> Dict[str, Any]:
    training = models.CooperativeTraining(
        cooperative_id=payload.get("cooperative_id"),
        organizer_id=user_id,
        topic=payload.get("topic"),
        description=payload.get("description"),
        session_date=payload.get("session_date"),
        capacity=payload.get("capacity", 20),
        status="open",
    )
    db.add(training)
    db.commit()
    db.refresh(training)
    return {
        "success": True,
        "training_id": training.id,
        "topic": training.topic,
        "cooperative_id": training.cooperative_id,
    }


def list_cooperative_trainings(db: Session, cooperative_id: Optional[int] = None) -> List[Dict[str, Any]]:
    query = db.query(models.CooperativeTraining)
    if cooperative_id is not None:
        query = query.filter(models.CooperativeTraining.cooperative_id == cooperative_id)
    trainings = query.order_by(models.CooperativeTraining.session_date.asc()).all()
    return [
        {
            "id": t.id,
            "cooperative_id": t.cooperative_id,
            "organizer_id": t.organizer_id,
            "topic": t.topic,
            "description": t.description,
            "session_date": t.session_date,
            "capacity": t.capacity,
            "status": t.status,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        }
        for t in trainings
    ]


def join_cooperative_training(user_id: int, training_id: int, db: Session) -> Dict[str, Any]:
    training = db.query(models.CooperativeTraining).filter(models.CooperativeTraining.id == training_id).first()
    if not training:
        return {"success": False, "error": "Session de formation introuvable"}
    current_count = db.query(func.count(models.TrainingParticipant.id)).filter(
        models.TrainingParticipant.training_id == training_id
    ).scalar() or 0
    if training.capacity and current_count >= training.capacity:
        return {"success": False, "error": "Capacité atteinte"}
    existing = db.query(models.TrainingParticipant).filter(
        and_(
            models.TrainingParticipant.training_id == training_id,
            models.TrainingParticipant.user_id == user_id,
        )
    ).first()
    if existing:
        return {"success": False, "error": "Déjà inscrit à cette formation"}

    participant = models.TrainingParticipant(
        training_id=training_id,
        user_id=user_id,
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return {
        "success": True,
        "participant_id": participant.id,
        "training_id": training_id,
        "user_id": user_id,
    }


def enroll_in_course(user_id: int, course_id: int, db: Session) -> Dict[str, Any]:
    course = db.query(models.LearningCourse).filter(models.LearningCourse.id == course_id).first()
    if not course or not course.published:
        return {"success": False, "error": "Cours introuvable ou non publié"}
    existing = db.query(models.LearningEnrollment).filter(
        and_(
            models.LearningEnrollment.course_id == course_id,
            models.LearningEnrollment.user_id == user_id,
        )
    ).first()
    if existing:
        return {
            "success": True,
            "enrollment_id": existing.id,
            "course_id": course_id,
            "progress_percent": existing.progress_percent,
            "completed": existing.completed,
            "already_enrolled": True,
        }
    enrollment = models.LearningEnrollment(
        course_id=course_id,
        user_id=user_id,
        progress_percent=0,
        completed=False,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return {
        "success": True,
        "enrollment_id": enrollment.id,
        "course_id": course_id,
        "progress_percent": enrollment.progress_percent,
        "completed": enrollment.completed,
        "already_enrolled": False,
    }


def update_course_progress(
    user_id: int, course_id: int, progress_percent: int, db: Session
) -> Dict[str, Any]:
    enrollment = db.query(models.LearningEnrollment).filter(
        and_(
            models.LearningEnrollment.course_id == course_id,
            models.LearningEnrollment.user_id == user_id,
        )
    ).first()
    if not enrollment:
        return {"success": False, "error": "Inscription au cours introuvable"}
    progress_percent = max(0, min(100, int(progress_percent)))
    enrollment.progress_percent = progress_percent
    enrollment.completed = progress_percent >= 100
    db.commit()
    db.refresh(enrollment)
    return {
        "success": True,
        "enrollment_id": enrollment.id,
        "course_id": course_id,
        "progress_percent": enrollment.progress_percent,
        "completed": enrollment.completed,
    }


def list_user_enrollments(user_id: int, db: Session) -> List[Dict[str, Any]]:
    rows = db.query(models.LearningEnrollment).filter(
        models.LearningEnrollment.user_id == user_id
    ).order_by(models.LearningEnrollment.updated_at.desc()).all()
    result = []
    for row in rows:
        course = db.query(models.LearningCourse).filter(models.LearningCourse.id == row.course_id).first()
        result.append({
            "enrollment_id": row.id,
            "course_id": row.course_id,
            "course_title": course.title if course else None,
            "content_type": course.content_type if course else None,
            "progress_percent": row.progress_percent,
            "completed": row.completed,
            "enrolled_at": row.enrolled_at,
            "updated_at": row.updated_at,
        })
    return result
