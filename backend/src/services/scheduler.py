"""Background scheduler for automated workflow runs.

A lightweight asyncio loop polls the database for workflows with a due
`next_run_at`, executes them (topological order over the DAG), records a
WorkflowRun, and computes the next run from a cron expression.
"""
import asyncio
from datetime import datetime, timezone

from src.models.workflow import WorkflowDAG, WorkflowRun, WorkflowEdgeModel, WorkflowNodeModel
from src.utils.logger import logger

POLL_INTERVAL_SECONDS = 30


async def compute_next_run(cron: str, after: datetime) -> datetime | None:
    """Return the next UTC datetime matching a 5-field cron expression, or None if invalid."""
    try:
        from croniter import croniter

        return croniter(cron, after).get_next(datetime)
    except Exception as e:
        logger.warning(f"Invalid cron expression '{cron}': {e}")
        return None


def _topo_order(nodes: list[WorkflowNodeModel], edges: list[WorkflowEdgeModel]) -> list[str]:
    node_ids = [n.id for n in nodes]
    if not edges:
        return node_ids
    in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
    adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for e in edges:
        if e.source not in adjacency or e.target not in in_degree:
            continue
        adjacency[e.source].append(e.target)
        in_degree[e.target] += 1
    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    order: list[str] = []
    while queue:
        nid = queue.pop(0)
        order.append(nid)
        for neighbour in adjacency[nid]:
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                queue.append(neighbour)
    return order if len(order) == len(node_ids) else node_ids


async def _execute_dag(wf: WorkflowDAG, prompt: str, user_id: str) -> dict:
    from src.agents.registry import AgentRegistry

    nodes_map = {n.id: n for n in wf.nodes}
    order = _topo_order(wf.nodes, wf.edges)

    run = WorkflowRun(
        workflow_id=str(wf.id),
        user_id=user_id,
        prompt=prompt,
        status="running",
    )
    await run.insert()

    handoff = prompt
    final_output = ""
    had_error = False

    for node_id in order:
        node = nodes_map.get(node_id)
        if not node:
            continue
        agent = AgentRegistry.get_agent(node.agent_id)
        if not agent:
            run.node_results.append({
                "nodeId": node_id, "agentId": node.agent_id,
                "success": False, "error": f"Agent '{node.agent_id}' not found",
            })
            had_error = True
            continue
        try:
            ctx = {
                "user_id": user_id,
                "workflow_id": str(wf.id),
                "step": 0,
                "google_access_token": "",
            }
            result = await agent.execute(handoff, ctx)
            run.node_results.append({
                "nodeId": node_id, "agentId": node.agent_id,
                "success": result.success, "output": (result.output or "")[:2000],
                "error": result.error,
            })
            if result.success:
                final_output = result.output or ""
                handoff = (
                    f"Original task: {prompt}\n\n"
                    f"Output from previous agent ({node.agent_id}):\n{result.output}\n\n"
                    "Continue as the next specialist in the pipeline."
                )
            else:
                had_error = True
        except Exception as e:
            had_error = True
            run.node_results.append({
                "nodeId": node_id, "agentId": node.agent_id,
                "success": False, "error": str(e),
            })

    run.status = "error" if had_error else "complete"
    run.final_output = final_output
    run.completed_at = datetime.now(timezone.utc)
    await run.save()
    return {"status": run.status, "run_id": str(run.id), "output": final_output}


async def _run_due_workflows() -> None:
    now = datetime.now(timezone.utc)
    due = await WorkflowDAG.find(
        WorkflowDAG.schedule_enabled == True,
        {"$or": [{"next_run_at": {"$lte": now}}, {"next_run_at": None}]},
    ).to_list()

    for wf in due:
        if wf.next_run_at is not None and wf.next_run_at > now:
            continue
        prompt = (wf.prompt or "").strip()
        if not prompt or not wf.nodes:
            continue
        try:
            await _execute_dag(wf, prompt, wf.user_id or "default")
            wf.last_run_at = now
            wf.next_run_at = await compute_next_run(wf.schedule_cron or "", datetime.now(timezone.utc))
            if wf.next_run_at is None:
                wf.schedule_enabled = False
            await wf.save()
            logger.info(f"Scheduled workflow '{wf.name}' ran at {now.isoformat()}")
        except Exception as e:
            logger.error(f"Scheduled workflow {wf.id} failed: {e}")


async def scheduler_loop() -> None:
    while True:
        try:
            await _run_due_workflows()
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


_scheduler_task: asyncio.Task | None = None


async def start_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task is not None:
        return
    _scheduler_task = asyncio.create_task(scheduler_loop())
    logger.info("Workflow scheduler started")


async def stop_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task is not None:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
        _scheduler_task = None
        logger.info("Workflow scheduler stopped")
