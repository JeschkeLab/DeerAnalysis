import json
from datetime import datetime, timezone

import numpy as np

from deeranalysis.utils.database import get_session, Job


def _json_default(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    return str(obj)


def to_jsonable(obj):
    """Recursively converts numpy arrays/scalars (as found in fit kwargs) into plain
    JSON-serializable Python objects, so they can be stored in a SQLAlchemy JSON column."""
    if obj is None:
        return None
    return json.loads(json.dumps(obj, default=_json_default))


def create_job(job_type, page, label, params=None):
    """Creates a new Job row with status 'queued' and returns its id."""
    session = get_session()
    job = Job(job_type=job_type, page=page, label=label, params=to_jsonable(params) or {}, status="queued")
    session.add(job)
    session.commit()
    job_id = job.id
    session.close()
    return job_id


def update_job(job_id, status=None, message=None, error=None, result_data=None):
    session = get_session()
    job = session.query(Job).filter_by(id=job_id).first()
    if job is None:
        session.close()
        return
    if status is not None:
        job.status = status
    if message is not None:
        job.message = message
    if error is not None:
        job.error = error
    if result_data is not None:
        job.result_data = to_jsonable(result_data)
    job.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.close()


def get_job(job_id):
    session = get_session()
    job = session.query(Job).filter_by(id=job_id).first()
    if job is not None:
        session.expunge(job)
    session.close()
    return job


def list_jobs(limit=100):
    session = get_session()
    jobs = session.query(Job).order_by(Job.created_at.desc()).limit(limit).all()
    session.expunge_all()
    session.close()
    return jobs


def list_jobs_for_page(page, limit=50):
    session = get_session()
    jobs = (
        session.query(Job)
        .filter_by(page=page)
        .order_by(Job.created_at.desc())
        .limit(limit)
        .all()
    )
    session.expunge_all()
    session.close()
    return jobs


def count_running_jobs():
    session = get_session()
    count = session.query(Job).filter_by(status="running").count()
    session.close()
    return count


def clear_finished_jobs():
    """Deletes all done/error/cancelled jobs (the drawer's 'Clean up' action). Running and
    queued jobs are left untouched."""
    session = get_session()
    session.query(Job).filter(Job.status.in_(["done", "error", "cancelled"])).delete(synchronize_session=False)
    session.commit()
    session.close()
