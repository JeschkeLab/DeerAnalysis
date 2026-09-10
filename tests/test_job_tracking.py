"""Tests for the background jobs table (utils/job_tracking.py, utils/database.py Job model)."""
import tempfile

import numpy as np
import pytest

from deeranalysis.utils import database as db
from deeranalysis.utils.job_tracking import (
    create_job, update_job, get_job, list_jobs, list_jobs_for_page,
    count_running_jobs, to_jsonable, clear_finished_jobs,
)


@pytest.fixture()
def temp_db():
    with tempfile.TemporaryDirectory() as tmp:
        db.init_db(tmp)
        yield tmp
        db.engine = None
        db.Session = None


def test_to_jsonable_converts_numpy():
    payload = {"a": np.array([1.0, 2.0]), "b": np.float64(3.5), "c": np.int64(2), "d": None}
    result = to_jsonable(payload)
    assert result == {"a": [1.0, 2.0], "b": 3.5, "c": 2, "d": None}
    assert isinstance(result["a"], list)
    assert isinstance(result["b"], float)
    assert isinstance(result["c"], int)


def test_create_and_get_job(temp_db):
    job_id = create_job("non-parametric_fit", page="non-parametric", label="my-dataset",
                         params={"dataset_id": 1, "distance_axis": np.array([1.5, 6.0])})
    job = get_job(job_id)
    assert job.status == "queued"
    assert job.job_type == "non-parametric_fit"
    assert job.label == "my-dataset"
    assert job.params["distance_axis"] == [1.5, 6.0]


def test_update_job(temp_db):
    job_id = create_job("parametric_fit", page="parametric", label="ds", params={})
    update_job(job_id, status="running")
    assert get_job(job_id).status == "running"

    update_job(job_id, status="done", result_data={"t": [1, 2, 3]})
    job = get_job(job_id)
    assert job.status == "done"
    assert job.result_data == {"t": [1, 2, 3]}

    update_job(job_id, status="error", error="boom")
    job = get_job(job_id)
    assert job.status == "error"
    assert job.error == "boom"


def test_update_job_missing_id_is_noop(temp_db):
    update_job(999999, status="done")  # should not raise


def test_list_jobs_ordering_and_filtering(temp_db):
    id1 = create_job("non-parametric_fit", page="non-parametric", label="a", params={})
    id2 = create_job("parametric_fit", page="parametric", label="b", params={})
    id3 = create_job("non-parametric_fit", page="non-parametric", label="c", params={})

    all_jobs = list_jobs()
    assert [j.id for j in all_jobs][:3] == [id3, id2, id1]

    page_jobs = list_jobs_for_page("non-parametric")
    assert {j.id for j in page_jobs} == {id1, id3}


def test_count_running_jobs(temp_db):
    id1 = create_job("non-parametric_fit", page="non-parametric", label="a", params={})
    id2 = create_job("parametric_fit", page="parametric", label="b", params={})
    assert count_running_jobs() == 0

    update_job(id1, status="running")
    assert count_running_jobs() == 1

    update_job(id2, status="running")
    assert count_running_jobs() == 2

    update_job(id1, status="done")
    assert count_running_jobs() == 1




def test_clear_finished_jobs(temp_db):
    id_done = create_job("non-parametric_fit", page="non-parametric", label="a", params={})
    id_error = create_job("parametric_fit", page="parametric", label="b", params={})
    id_cancelled = create_job("background_fit", page="background", label="c", params={})
    id_queued = create_job("global_fit", page="global", label="d", params={})
    id_running = create_job("population_fit", page="population", label="e", params={})
    update_job(id_done, status="done")
    update_job(id_error, status="error")
    update_job(id_cancelled, status="cancelled")
    update_job(id_running, status="running")

    clear_finished_jobs()

    remaining_ids = {j.id for j in list_jobs()}
    assert remaining_ids == {id_queued, id_running}
