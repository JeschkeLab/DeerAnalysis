"""Background jobs drawer: lists queued/running/finished fits and is the sole place jobs can be
cancelled from (the drawer is mounted once in app.py's top-level layout, so it stays present
across page navigation, unlike per-page components).

Dash's `background_callback` does not allow pattern-matching (MATCH/ALL) ids in its `cancel=`
list (see dash._callback.validate_background_inputs), so a single generic MATCH-based dispatcher
can't be cancelled per-job. Instead we run a fixed number of "slots" — each a statically
registered background callback with concrete ids — and a fast scheduler callback assigns queued
jobs to whichever slot is free. MAX_CONCURRENT_JOBS is both the concurrency cap and the slot
count.
"""
import dash_mantine_components as dmc
from dash import html, dcc, callback, Input, Output, State, no_update
from dash_iconify import DashIconify

from deeranalysis.utils.database import init_db
from deeranalysis.components.setup_modal_desktop import get_DeerAnalysis_directory
from deeranalysis.utils.job_tracking import list_jobs, update_job, get_job, clear_finished_jobs
from deeranalysis.utils.job_dispatch import JOB_HANDLERS, save_fit_from_job

MAX_CONCURRENT_JOBS = 2

PAGE_ROUTES = {
    'non-parametric': '/nonparametric',
    'parametric': '/parametric',
    'background': '/background',
    'population': '/population',
    'global': '/global',
    'deernet': '/deernet',
}

STATUS_COLORS = {
    'queued': 'gray',
    'running': 'blue',
    'done': 'green',
    'error': 'red',
    'cancelled': 'orange',
}


def jobs_drawer_button():
    return dmc.Indicator(
        dmc.ActionIcon(
            DashIconify(icon="mdi:briefcase-clock", width=20),
            id="jobs-drawer-button",
            color="gray",
            variant="subtle",
            size="lg",
        ),
        id="jobs-drawer-badge",
        label="0",
        size=16,
        disabled=True,
        color="blue",
    )


def jobs_drawer():
    slot_stores = [dcc.Store(id=f"job-slot-trigger-{i}", storage_type="memory") for i in range(MAX_CONCURRENT_JOBS)]
    return (
        dmc.Drawer(
            id="jobs-drawer",
            title="Background Jobs",
            position="right",
            size="md",
            padding="md",
            zIndex=1000,
            children=[
                dmc.Group([
                    dmc.Button("Clean up finished", id="jobs-cleanup-btn", size="xs",
                               variant="light", color="gray",
                               leftSection=DashIconify(icon="mdi:broom", width=16)),
                ], justify="flex-end", mb="sm"),
                html.Div(id="jobs-drawer-content"),
            ],
        ),
        dcc.Interval(id="jobs-poll-interval", interval=1500),
        dcc.Store(id="jobs-slot-assignments", storage_type="memory", data={}),
        *slot_stores,
    )


def _job_row(job, slot_assignments):
    is_active = job.status in ('queued', 'running')
    children = [
        dmc.Group([
            dmc.Text(job.label or job.job_type, size="sm", fw=500),
            dmc.Badge(job.status, color=STATUS_COLORS.get(job.status, 'gray'), size="sm"),
        ], justify="space-between"),
    ]
    if job.status == 'running':
        children.append(dmc.Progress(value=100, animated=True, striped=True, size="sm", mt=4))
    if job.status == 'error' and job.error:
        children.append(dmc.Text(job.error, size="xs", c="red", mt=4))

    actions = []
    if job.status == 'running':
        slot = next((s for s, jid in slot_assignments.items() if jid == job.id), None)
        if slot is not None:
            actions.append(dmc.Button("Cancel", id=f"cancel-slot-btn-{slot}",
                                       color="red", variant="light", size="xs"))
    elif job.status == 'queued':
        actions.append(dmc.Text("Waiting for a free slot…", size="xs", c="dimmed"))
    href = PAGE_ROUTES.get(job.page)
    if href:
        actions.append(dmc.Anchor(dmc.Button("Go to page", variant="subtle", size="xs"), href=href))
    if actions:
        children.append(dmc.Group(actions, mt=6, gap="xs"))

    return dmc.Paper(children, withBorder=True, p="sm", mb="xs")


@callback(
    Output("jobs-drawer", "opened"),
    Input("jobs-drawer-button", "n_clicks"),
    State("jobs-drawer", "opened"),
    prevent_initial_call=True,
)
def toggle_jobs_drawer(n_clicks, opened):
    return not opened


@callback(
    Output("jobs-drawer-content", "children", allow_duplicate=True),
    Input("jobs-cleanup-btn", "n_clicks"),
    State("jobs-slot-assignments", "data"),
    prevent_initial_call=True,
)
def cleanup_finished_jobs(n_clicks, slot_assignments):
    if not n_clicks:
        return no_update
    clear_finished_jobs()
    jobs = list_jobs(limit=100)
    rows = [_job_row(job, slot_assignments or {}) for job in jobs]
    return rows if rows else [dmc.Text("No background jobs yet.", c="dimmed", size="sm")]


@callback(
    Output("jobs-drawer-content", "children"),
    Output("jobs-drawer-badge", "label"),
    Output("jobs-drawer-badge", "disabled"),
    Output("jobs-slot-assignments", "data"),
    *[Output(f"job-slot-trigger-{i}", "data", allow_duplicate=True) for i in range(MAX_CONCURRENT_JOBS)],
    Input("jobs-poll-interval", "n_intervals"),
    State("jobs-slot-assignments", "data"),
    prevent_initial_call=True,
)
def schedule_and_render(_n_intervals, slot_assignments):
    assignments = dict(slot_assignments or {})
    slot_outputs = [no_update] * MAX_CONCURRENT_JOBS

    # Free up slots whose job has finished (or whose mapping was lost, e.g. after a page reload).
    for slot in [str(i) for i in range(MAX_CONCURRENT_JOBS)]:
        job_id = assignments.get(slot)
        if job_id is not None:
            job = get_job(job_id)
            if job is None or job.status != 'running':
                assignments[slot] = None

    jobs = list_jobs(limit=100)

    # Self-heal: a job stuck at 'running' with no slot owner (e.g. after a page reload lost the
    # in-memory slot mapping) is requeued so it can be picked up by a free slot again.
    owned_job_ids = {jid for jid in assignments.values() if jid is not None}
    for job in jobs:
        if job.status == 'running' and job.id not in owned_job_ids:
            update_job(job.id, status='queued')
            job.status = 'queued'

    queued = sorted((j for j in jobs if j.status == 'queued'), key=lambda j: j.created_at)
    for job in queued:
        free_slot = next((str(i) for i in range(MAX_CONCURRENT_JOBS) if not assignments.get(str(i))), None)
        if free_slot is None:
            break
        update_job(job.id, status='running')
        job.status = 'running'
        assignments[free_slot] = job.id
        slot_outputs[int(free_slot)] = job.id

    active_count = sum(1 for j in jobs if j.status in ('queued', 'running'))
    rows = [_job_row(job, assignments) for job in jobs]
    if not rows:
        rows = [dmc.Text("No background jobs yet.", c="dimmed", size="sm")]
    return rows, str(active_count), active_count == 0, assignments, *slot_outputs


def _make_cancel_callback(slot):
    @callback(
        Output(f"job-slot-trigger-{slot}", "data", allow_duplicate=True),
        Input(f"cancel-slot-btn-{slot}", "n_clicks"),
        State(f"job-slot-trigger-{slot}", "data"),
        prevent_initial_call=True,
    )
    def mark_slot_job_cancelled(n_clicks, job_id):
        """Optimistically flips the Job row to 'cancelled' the moment Cancel is clicked, in a
        fast ordinary callback — decoupled from Dash's own background-callback cancel machinery
        below, which terminates the subprocess but cannot run cleanup code inside it."""
        if not n_clicks or not job_id:
            return no_update
        update_job(job_id, status="cancelled")
        return no_update
    return mark_slot_job_cancelled


def _make_slot_worker(slot):
    @callback(
        Output(f"job-slot-trigger-{slot}", "data", allow_duplicate=True),
        Input(f"job-slot-trigger-{slot}", "data"),
        background=True,
        cancel=[Input(f"cancel-slot-btn-{slot}", "n_clicks")],
        prevent_initial_call=True,
    )
    def run_slot_job(job_id):
        if not job_id:
            return no_update
        # DiskcacheManager runs this callback in a separate process (see the "spawn" start
        # method set in app.py) — a fresh interpreter that never ran app.py's module-level
        # init_db() call, so database.Session would otherwise be None here. Re-running
        # init_db is idempotent (same sqlite file, no-ops on already-existing tables).
        init_db(get_DeerAnalysis_directory())
        job = get_job(job_id)
        if job is None or job.status != "running":
            return no_update
        try:
            result = JOB_HANDLERS[job.job_type](job.params or {})
            update_job(job_id, status="done", result_data=result)
            # Auto-save the fit so results aren't lost if nobody comes back to click "Save
            # Fit" on the originating page — a failure here shouldn't erase the "done" fit
            # result, just note that the save itself didn't happen.
            try:
                save_fit_from_job(job, result)
            except Exception as save_err:
                import traceback
                traceback.print_exc()
                update_job(job_id, message=f"Fit computed but auto-save failed: {save_err}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            update_job(job_id, status="error", error=str(e))
        return no_update
    return run_slot_job


for _slot in range(MAX_CONCURRENT_JOBS):
    _make_cancel_callback(_slot)
    _make_slot_worker(_slot)
