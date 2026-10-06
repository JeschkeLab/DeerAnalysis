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
from datetime import datetime, timezone

import dash_mantine_components as dmc
from dash import html, dcc, callback, Input, Output, State, ALL, MATCH, ctx, no_update
from dash_iconify import DashIconify

from deeranalysis.utils.database import init_db, get_job_settings
from deeranalysis.components.setup_modal_desktop import get_DeerAnalysis_directory
from deeranalysis.utils.job_tracking import (
    list_jobs, list_jobs_for_page, update_job, get_job, delete_job, clear_finished_jobs,
    is_unsaved, prune_unsaved_jobs,
)
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
            auto_save, max_cached = get_job_settings()
            if auto_save:
                # Auto-save the fit so results aren't lost if nobody comes back to click "Save
                # Fit" on the originating page — a failure here shouldn't erase the "done" fit
                # result, just note that the save itself didn't happen.
                try:
                    save_fit_from_job(job, result)
                    update_job(job_id, saved=True)
                except Exception as save_err:
                    import traceback
                    traceback.print_exc()
                    update_job(job_id, message=f"Fit computed but auto-save failed: {save_err}")
            # Unsaved results only live in the job cache; cap how many are kept.
            prune_unsaved_jobs(max_cached)
        except Exception as e:
            import traceback
            traceback.print_exc()
            update_job(job_id, status="error", error=str(e))
        return no_update
    return run_slot_job


for _slot in range(MAX_CONCURRENT_JOBS):
    _make_cancel_callback(_slot)
    _make_slot_worker(_slot)


# --- Per-page "Recent jobs" panel -------------------------------------------------------------

RECENT_JOBS_SHOWN = 4

JOB_STATUS_ICONS = {
    "queued": "mdi:clock-outline",
    "running": "mdi:progress-clock",
    "done": "mdi:check-circle-outline",
    "error": "mdi:alert-circle-outline",
    "cancelled": "mdi:cancel",
}


def queued_jobs_panel(page_id):
    """Small panel listing this page's own queued/running/finished jobs, with 'Load result' and
    'Delete' actions for finished ones. Cancellation happens from the jobs drawer (top bar), not here.

    The job the page itself just queued is loaded into the plot automatically once it finishes
    (see pending-auto-load store below) — the "Add to Queue -> wait -> see the result"
    experience should feel like the old synchronous "Run Fit" button, just non-blocking. This
    is deliberately narrow: each page's queue_fit callback sets pending-auto-load to the new
    job's id, and a page-specific "invalidate" callback (watching the same inputs queue_fit
    reads) clears it back to None the moment any parameter changes — so a stale result never
    silently overwrites a plot whose settings have since moved on. Because pending-auto-load is
    an in-memory Store, it's also naturally cleared by navigating away and back, so returning to
    a page never auto-loads a job that finished while you were elsewhere; "Load result" is still
    offered per job for that case."""
    return html.Div([
        dcc.Interval(id={"type": "page-jobs-poll", "page": page_id}, interval=2000),
        dcc.Store(id={"type": "job-load-request", "page": page_id}),
        dcc.Store(id={"type": "pending-auto-load", "page": page_id}, storage_type="memory"),
        dcc.Store(id={"type": "delete-job-target", "page": page_id}, storage_type="memory"),
        html.Div(id={"type": "page-jobs-panel", "page": page_id}),
        dmc.Modal(
            id={"type": "delete-job-modal", "page": page_id},
            title="Delete job?",
            centered=True,
            size="sm",
            children=[
                dmc.Text(id={"type": "delete-job-modal-text", "page": page_id}, size="sm"),
                dmc.Group([
                    dmc.Button("Cancel", variant="default", size="xs",
                               id={"type": "delete-job-cancel", "page": page_id}),
                    dmc.Button("Delete", color="red", size="xs",
                               leftSection=DashIconify(icon="mdi:trash-can-outline", width=14),
                               id={"type": "delete-job-confirm", "page": page_id}),
                ], justify="flex-end", mt="md", gap="xs"),
            ],
        ),
    ])


def _as_utc(dt):
    # SQLite drops tzinfo on read, but the columns are written in UTC.
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _format_duration(seconds):
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def _job_timing_text(job):
    now = datetime.now(timezone.utc)
    created = _as_utc(job.created_at)
    updated = _as_utc(job.updated_at) or created
    if created is None:
        return ""
    if job.status == "queued":
        return f"Queued {_format_duration((now - created).total_seconds())} ago"
    if job.status == "running":
        # updated_at is stamped when the scheduler flips the job to 'running'.
        return f"Running for {_format_duration((now - updated).total_seconds())}"
    return f"Took {_format_duration((updated - created).total_seconds())}"


def _page_job_card(job, page_id):
    """One card per job: status icon, label, status badge, timing, progress bar and actions.
    The job model has no numeric progress, so the bar shows phase rather than percentage:
    striped while queued, animated while running, full once finished. Finished jobs keep the
    card neutral — only the tick icon is green."""
    is_done = job.status == "done"
    color = STATUS_COLORS.get(job.status, "gray")
    card_color = "gray" if is_done else color
    icon = JOB_STATUS_ICONS.get(job.status, "mdi:help-circle-outline")

    if job.status == "queued":
        progress = dmc.Progress(value=100, color="gray", striped=True, size="xs", radius="xl")
    elif job.status == "running":
        progress = dmc.Progress(value=100, color=color, striped=True, animated=True, size="xs", radius="xl")
    else:
        progress = dmc.Progress(value=100, color=card_color, size="xs", radius="xl")

    fit_name = (job.params or {}).get("fit_name")
    title_lines = [dmc.Text(fit_name or job.label or job.job_type, size="sm", fw=500, truncate="end")]
    if fit_name and job.label:
        title_lines.append(dmc.Text(job.label, size="xs", truncate="end"))
    timing = _job_timing_text(job)
    if is_unsaved(job):
        timing = f"{timing} · not saved"
    title_lines.append(dmc.Text(timing, size="xs", c="dimmed"))

    title_row = dmc.Group([
        dmc.ThemeIcon(DashIconify(icon=icon, width=16), color=color, variant="light", size="md", radius="xl"),
        dmc.Stack(title_lines, gap=0, style={"flex": 1, "minWidth": 0}),
        dmc.Badge(job.status, color=card_color, variant="light", size="sm"),
    ], gap="sm", wrap="nowrap", align="center")

    children = [title_row, progress]
    if job.status == "error" and job.error:
        children.append(dmc.Text(job.error, size="xs", c="red", lineClamp=2))
    elif job.message:
        children.append(dmc.Text(job.message, size="xs", c="dimmed", lineClamp=2))

    actions = []
    if is_unsaved(job):
        actions.append(dmc.Tooltip(
            dmc.ActionIcon(DashIconify(icon="mdi:content-save-outline", width=16),
                           variant="subtle", color="blue", size="md",
                           id={"type": "save-job-btn", "page": page_id, "job": job.id}),
            label="Save fit", withArrow=True,
        ))
    if is_done:
        actions.append(dmc.Button("Load result", size="xs", variant="light",
                                  leftSection=DashIconify(icon="mdi:chart-bell-curve", width=14),
                                  id={"type": "load-job-result-btn", "page": page_id, "job": job.id}))
    if job.status not in ("queued", "running"):
        actions.append(dmc.Tooltip(
            dmc.ActionIcon(DashIconify(icon="mdi:trash-can-outline", width=16),
                           variant="subtle", color="red", size="md",
                           id={"type": "delete-job-btn", "page": page_id, "job": job.id}),
            label="Delete job", withArrow=True,
        ))
    if actions:
        children.append(dmc.Group(actions, justify="flex-end", gap="xs"))

    return dmc.Paper(dmc.Stack(children, gap=6), withBorder=True, radius="md", p="xs", shadow="xs")


def _render_page_jobs(page_id):
    jobs = list_jobs_for_page(page_id, limit=RECENT_JOBS_SHOWN)
    if not jobs:
        return []
    n_active = sum(1 for job in jobs if job.status in ("queued", "running"))
    header = dmc.Group([
        dmc.Text("Recent jobs", size="sm", fw=600),
        dmc.Badge(f"{n_active} active", size="sm", variant="light",
                  color="blue" if n_active else "gray"),
    ], justify="space-between")
    cards = [_page_job_card(job, page_id) for job in jobs]
    return dmc.Stack([header, *cards], gap=6, mt="xs")


@callback(
    Output({"type": "page-jobs-panel", "page": MATCH}, "children"),
    Output({"type": "job-load-request", "page": MATCH}, "data", allow_duplicate=True),
    Output({"type": "pending-auto-load", "page": MATCH}, "data", allow_duplicate=True),
    Input({"type": "page-jobs-poll", "page": MATCH}, "n_intervals"),
    State({"type": "pending-auto-load", "page": MATCH}, "data"),
    prevent_initial_call=True,
)
def update_page_jobs_panel(_n_intervals, pending_job_id):
    outputs_list = ctx.outputs_list
    out = outputs_list[0] if isinstance(outputs_list, list) else outputs_list
    page_id = out['id']['page']

    load_request = no_update
    pending_output = no_update
    if pending_job_id is not None:
        pending_job = get_job(pending_job_id)
        if pending_job is not None and pending_job.status == "done":
            load_request = pending_job_id
            pending_output = None  # consumed — stop watching it

    return _render_page_jobs(page_id), load_request, pending_output


@callback(
    Output({"type": "job-load-request", "page": MATCH}, "data"),
    Input({"type": "load-job-result-btn", "page": MATCH, "job": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def request_job_load(n_clicks_list):
    if not n_clicks_list or not any(n_clicks_list):
        return no_update
    triggered_id = ctx.triggered_id
    if not triggered_id:
        return no_update
    return triggered_id["job"]


@callback(
    Output({"type": "delete-job-modal", "page": MATCH}, "opened"),
    Output({"type": "delete-job-target", "page": MATCH}, "data"),
    Output({"type": "delete-job-modal-text", "page": MATCH}, "children"),
    Input({"type": "delete-job-btn", "page": MATCH, "job": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def ask_delete_page_job(n_clicks_list):
    # The panel re-renders every poll, which re-adds the buttons with n_clicks=None and fires
    # this callback — only act on a real click.
    triggered_id = ctx.triggered_id
    if not triggered_id or not ctx.triggered or not ctx.triggered[0]["value"]:
        return no_update, no_update, no_update
    job = get_job(triggered_id["job"])
    if job is None:
        return no_update, no_update, no_update
    name = (job.params or {}).get("fit_name") or job.label or job.job_type
    text = [f"Remove the job “{name}” from the list? ",
            "Fits already saved from it are kept."]
    return True, job.id, text


@callback(
    Output({"type": "page-jobs-panel", "page": MATCH}, "children", allow_duplicate=True),
    Output({"type": "delete-job-modal", "page": MATCH}, "opened", allow_duplicate=True),
    Output({"type": "delete-job-target", "page": MATCH}, "data", allow_duplicate=True),
    Input({"type": "delete-job-confirm", "page": MATCH}, "n_clicks"),
    Input({"type": "delete-job-cancel", "page": MATCH}, "n_clicks"),
    State({"type": "delete-job-target", "page": MATCH}, "data"),
    prevent_initial_call=True,
)
def resolve_delete_page_job(_confirm, _cancel, job_id):
    triggered_id = ctx.triggered_id
    if not triggered_id:
        return no_update, no_update, no_update
    if triggered_id["type"] == "delete-job-cancel" or job_id is None:
        return no_update, False, None
    delete_job(job_id)
    return _render_page_jobs(triggered_id["page"]), False, None


@callback(
    Output({"type": "page-jobs-panel", "page": MATCH}, "children", allow_duplicate=True),
    Input({"type": "save-job-btn", "page": MATCH, "job": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def save_page_job(n_clicks_list):
    # Same re-render guard as ask_delete_page_job.
    triggered_id = ctx.triggered_id
    if not triggered_id or not ctx.triggered or not ctx.triggered[0]["value"]:
        return no_update
    job = get_job(triggered_id["job"])
    if job is None or not is_unsaved(job) or not job.result_data:
        return no_update
    try:
        save_fit_from_job(job, job.result_data)
        update_job(job.id, saved=True)
    except Exception as e:
        import traceback
        traceback.print_exc()
        update_job(job.id, message=f"Save failed: {e}")
    return _render_page_jobs(triggered_id["page"])
