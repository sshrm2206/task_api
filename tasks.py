from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import db, Task

tasks_bp = Blueprint("tasks", __name__)

ALLOWED_STATUSES = {"pending", "in_progress", "completed"}
ALLOWED_PRIORITIES = {"low", "medium", "high"}


def _current_user_id():
    return int(get_jwt_identity())


@tasks_bp.route("", methods=["GET"])
@jwt_required()
def list_tasks():
    user_id = _current_user_id()
    query = Task.query.filter_by(user_id=user_id)

    status = request.args.get("status")
    priority = request.args.get("priority")
    search = request.args.get("search")

    if status:
        if status not in ALLOWED_STATUSES:
            return jsonify({"error": f"invalid status filter '{status}'"}), 400
        query = query.filter_by(status=status)

    if priority:
        if priority not in ALLOWED_PRIORITIES:
            return jsonify({"error": f"invalid priority filter '{priority}'"}), 400
        query = query.filter_by(priority=priority)

    if search:
        query = query.filter(Task.title.ilike(f"%{search}%"))

    # simple pagination
    try:
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)
    except ValueError:
        return jsonify({"error": "page and per_page must be integers"}), 400

    pagination = query.order_by(Task.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        {
            "tasks": [t.to_dict() for t in pagination.items],
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        }
    ), 200


@tasks_bp.route("/<int:task_id>", methods=["GET"])
@jwt_required()
def get_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=_current_user_id()).first()
    if not task:
        return jsonify({"error": "task not found"}), 404
    return jsonify(task.to_dict()), 200


@tasks_bp.route("", methods=["POST"])
@jwt_required()
def create_task():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    status = data.get("status", "pending")
    priority = data.get("priority", "medium")

    if status not in ALLOWED_STATUSES:
        return jsonify({"error": f"invalid status '{status}'"}), 400
    if priority not in ALLOWED_PRIORITIES:
        return jsonify({"error": f"invalid priority '{priority}'"}), 400

    task = Task(
        title=title,
        description=data.get("description"),
        status=status,
        priority=priority,
        user_id=_current_user_id(),
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@tasks_bp.route("/<int:task_id>", methods=["PUT"])
@jwt_required()
def update_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=_current_user_id()).first()
    if not task:
        return jsonify({"error": "task not found"}), 404

    data = request.get_json(silent=True) or {}

    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title cannot be empty"}), 400
        task.title = title

    if "description" in data:
        task.description = data.get("description")

    if "status" in data:
        if data["status"] not in ALLOWED_STATUSES:
            return jsonify({"error": f"invalid status '{data['status']}'"}), 400
        task.status = data["status"]

    if "priority" in data:
        if data["priority"] not in ALLOWED_PRIORITIES:
            return jsonify({"error": f"invalid priority '{data['priority']}'"}), 400
        task.priority = data["priority"]

    db.session.commit()
    return jsonify(task.to_dict()), 200


@tasks_bp.route("/<int:task_id>", methods=["DELETE"])
@jwt_required()
def delete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=_current_user_id()).first()
    if not task:
        return jsonify({"error": "task not found"}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "task deleted"}), 200
