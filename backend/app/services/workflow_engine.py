import asyncio
from typing import AsyncIterator, Dict, Optional, Any, List, Callable
from datetime import datetime
from sqlmodel import Session, select

from app.db.models import Workflow, WorkflowRun
from app.services import nodes as builtin_nodes
from loguru import logger


class LocalAsyncEngine:
    """
    Minimal Local Executor (MVP)
    - Linearly execute nodes; support List.ForEach/List.ForEachRange (body must exist)
    - Events: step_started/step_succeeded/step_failed/run_completed
    - Normalization: Rewrites DSL for compatibility before execution (ForEach without body -> fold next node as body)
    """

    def __init__(self) -> None:
        self._run_tasks: Dict[int, asyncio.Task] = {}
        self._event_queues: Dict[int, "asyncio.Queue[str]"] = {}

    # ---------------- background & events ----------------
    async def _publish(self, run_id: int, event: str) -> None:
        # Fallback: Create queue if not exists, avoid missing events if frontend subscribes late
        queue = self._event_queues.get(run_id)
        if queue is None:
            logger.info(f"[Workflow] _publish queue not found, created fallback run_id={run_id}")
            queue = asyncio.Queue()
            self._event_queues[run_id] = queue
        await queue.put(event)

    async def _close_queue(self, run_id: int) -> None:
        queue = self._event_queues.get(run_id)
        if queue is not None:
            await queue.put("__CLOSE__")

    def _ensure_queue(self, run_id: int) -> asyncio.Queue:
        q = self._event_queues.get(run_id)
        if q is None:
            q = asyncio.Queue()
            self._event_queues[run_id] = q
            logger.info(f"[Workflow] Event queue created run_id={run_id}")
        return q

    def subscribe_events(self, run_id: int) -> AsyncIterator[str]:
        queue = self._ensure_queue(run_id)

        async def _gen() -> AsyncIterator[str]:
            while True:
                item = await queue.get()
                if item == "__CLOSE__":
                    break
                yield item
        return _gen()

    def _background_run(self, coro_factory: Callable[[], asyncio.Future], run_id: int) -> Optional[asyncio.Task]:
        try:
            loop = asyncio.get_running_loop()
            return loop.create_task(coro_factory())
        except RuntimeError:
            try:
                import anyio  # type: ignore
                logger.info(f"[Workflow] No event loop; submitting run_id={run_id} via anyio.from_thread.run")
                return anyio.from_thread.run(asyncio.create_task, coro_factory())
            except Exception:
                logger.warning(f"[Workflow] anyio failed; running synchronously run_id={run_id}")
                asyncio.run(coro_factory())
                return None

    # ---------------- create run ----------------
    def create_run(self, session: Session, workflow: Workflow, scope_json: Optional[dict], params_json: Optional[dict], idempotency_key: Optional[str]) -> WorkflowRun:
        run = WorkflowRun(
            workflow_id=workflow.id,
            definition_version=workflow.version,
            status="queued",
            scope_json=scope_json,
            params_json=params_json,
            idempotency_key=idempotency_key,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        # Create event queue in advance, ensuring no first batch events are lost even if frontend subscribes later
        self._ensure_queue(run.id)
        logger.info(f"[Workflow] Run created and event queue initialized run_id={run.id} workflow_id={workflow.id}")
        return run

    # ---------------- nodes ----------------
    def _resolve_node_fn(self, type_name: str):
        """Get node function from node registry"""
        registry = builtin_nodes.get_registered_nodes()
        fn = registry.get(type_name)
        if not fn:
            raise ValueError(f"Unknown node type: {type_name}, registered nodes: {list(registry.keys())}")
        return fn

    # ---------------- canonicalize ----------------
    @staticmethod
    def _canonicalize(nodes: List[dict]) -> List[dict]:
        """Normalize DSL:
        - ForEach/ForEachRange without body -> Fold next node as body, skip separate execution.
        """
        out: List[dict] = []
        i = 0
        while i < len(nodes):
            n = nodes[i]
            ntype = n.get("type")
            if ntype in ("List.ForEach", "List.ForEachRange") and not n.get("body") and i + 1 < len(nodes):
                compat = dict(n)
                compat["body"] = [nodes[i + 1]]
                out.append(compat)
                logger.warning("[Workflow] Compatibility rewrite: ForEach/Range missing body, folded next node as body")
                i += 2
                continue
            out.append(n)
            i += 1
        return out

    # ---------------- execute ----------------
    async def _execute_dsl(self, session: Session, workflow: Workflow, run: WorkflowRun) -> None:
        dsl: Dict[str, Any] = workflow.definition_json or {}
        raw_nodes: List[dict] = list(dsl.get("nodes") or [])
        
        # Check if standard format (contains edges)
        is_standard_format = "edges" in dsl and isinstance(dsl["edges"], list)
        
        if is_standard_format:
            # Standard format: Execute based on edges
            await self._execute_standard_format(session, workflow, run, dsl)
        else:
            # Legacy format: Keep original logic
            await self._execute_legacy_format(session, workflow, run, raw_nodes)

    async def _execute_standard_format(self, session: Session, workflow: Workflow, run: WorkflowRun, dsl: dict) -> None:
        """Execute standard format workflow (based on nodes+edges)"""
        nodes: List[dict] = list(dsl.get("nodes") or [])
        edges: List[dict] = list(dsl.get("edges") or [])
        state: Dict[str, Any] = {"scope": run.scope_json or {}, "touched_card_ids": set()}
        
        logger.info(f"[Workflow] Start execution run_id={run.id} workflow_id={workflow.id} nodes={len(nodes)} edges={len(edges)}")
        
        # Build execution graph
        graph = self._build_execution_graph(nodes, edges)
        
        # Execute workflow
        await self._execute_graph(graph, session, state, run.id)
        
        # Save results
        await self._save_execution_result(session, run, state)
    
    def _build_execution_graph(self, nodes: List[dict], edges: List[dict]) -> dict:
        """Build execution graph: node mapping, dependencies, successors"""
        node_map = {n["id"]: n for n in nodes}
        dependencies = {}  # node_id -> [predecessor_ids]
        successors = {}    # node_id -> {"body": [...], "next": [...]}
        
        # Build dependencies and successors
        for edge in edges:
            source, target = edge["source"], edge["target"]
            handle = edge.get("sourceHandle", "r")
            
            # Record dependency
            dependencies.setdefault(target, []).append(source)
            
            # Record successor (distinguish body and next)
            succ_type = "body" if handle == "b" else "next"
            successors.setdefault(source, {"body": [], "next": []})[succ_type].append(target)
        
        # Find start nodes
        start_nodes = [n["id"] for n in nodes if n["id"] not in dependencies]
        if not start_nodes and nodes:
            logger.warning("[Workflow] No start node, using first node")
            start_nodes = [nodes[0]["id"]]
        
        return {
            "node_map": node_map,
            "dependencies": dependencies,
            "successors": successors,
            "start_nodes": start_nodes
        }
    
    async def _execute_graph(self, graph: dict, session: Session, state: dict, run_id: int) -> None:
        """Execute workflow graph"""
        node_map = graph["node_map"]
        dependencies = graph["dependencies"]
        successors = graph["successors"]
        executed = set()
        
        async def execute_node(node_id: str) -> None:
            if node_id in executed or node_id not in node_map:
                return
            
            node = node_map[node_id]
            ntype = node.get("type")
            params = node.get("params") or {}
            
            logger.info(f"[Workflow] Executing node id={node_id} type={ntype}")
            await self._publish(run_id, f"event: step_started\ndata: {ntype}\n\n")
            
            try:
                # Execute node
                await self._execute_single_node(node, session, state, run_id, successors.get(node_id, {}), node_map)
                
                # Mark as executed
                executed.add(node_id)
                
                # If loop node, mark body nodes as executed too
                if ntype in ("List.ForEach", "List.ForEachRange"):
                    executed.update(successors.get(node_id, {}).get("body", []))
                
                logger.info(f"[Workflow] Node succeeded id={node_id} type={ntype}")
                await self._publish(run_id, f"event: step_succeeded\ndata: {ntype}\n\n")
                
                # Execute successor nodes
                await self._execute_successors(node_id, successors, dependencies, executed, execute_node)
                
            except Exception as e:
                logger.exception(f"[Workflow] Node failed id={node_id} type={ntype} err={e}")
                await self._publish(run_id, f"event: step_failed\ndata: {ntype}: {e}\n\n")
                raise
        
        # Execute all start nodes
        for start_id in graph["start_nodes"]:
            await execute_node(start_id)
    
    async def _execute_single_node(self, node: dict, session: Session, state: dict, run_id: int, 
                                   node_successors: dict, node_map: dict) -> None:
        """Execute single node"""
        ntype = node.get("type")
        params = node.get("params") or {}
        
        # Special handling for loop nodes
        if ntype in ("List.ForEach", "List.ForEachRange"):
            body_node_ids = node_successors.get("body", [])
            body_nodes = [node_map[bid] for bid in body_node_ids if bid in node_map]
            body_executor = lambda: self._execute_body_nodes(body_nodes, session, state, run_id)
            
            if ntype == "List.ForEach":
                builtin_nodes.node_list_foreach(session, state, params, body_executor)
            else:
                builtin_nodes.node_list_foreach_range(session, state, params, body_executor)
        else:
            # Normal node
            fn = self._resolve_node_fn(ntype)
            fn(session, state, params)
    
    async def _execute_successors(self, node_id: str, successors: dict, dependencies: dict, 
                                  executed: set, execute_node) -> None:
        """Execute successor nodes"""
        # Get 'next' type successors (loop body nodes executed inside loop)
        next_nodes = successors.get(node_id, {}).get("next", [])
        
        for next_id in next_nodes:
            if next_id not in executed:
                # Check if all dependencies are satisfied
                deps = dependencies.get(next_id, [])
                if all(dep in executed for dep in deps):
                    await execute_node(next_id)

    def _execute_body_nodes(self, body_nodes: List[dict], session, state, run_id: int):
        """Execute body nodes synchronously (for ForEach callback)"""
        for bn in body_nodes:
            ntype = bn.get("type")
            params = bn.get("params") or {}
            logger.info(f"[Workflow] ForEach body node type={ntype}")
            try:
                fn = self._resolve_node_fn(ntype)
                fn(session, state, params)
            except Exception as e:  # noqa: BLE001
                logger.exception(f"[Workflow] ForEach body node failed type={ntype} err={e}")
                raise

    async def _execute_legacy_format(self, session: Session, workflow: Workflow, run: WorkflowRun, raw_nodes: List[dict]) -> None:
        """Execute legacy format workflow (Backward compatibility)"""
        nodes: List[dict] = self._canonicalize(raw_nodes)
        state: Dict[str, Any] = {"scope": run.scope_json or {}, "touched_card_ids": set()}
        logger.info(f"[Workflow] Start execution legacy format run_id={run.id} workflow_id={workflow.id} nodes={len(nodes)}")

        def run_body(body_nodes: List[dict]):
            for bn in body_nodes:
                ntype = bn.get("type")
                params = bn.get("params") or {}
                logger.info(f"[Workflow] Legacy node start type={ntype}")
                if ntype == "List.ForEach":
                    body = list((bn.get("body") or []))
                    builtin_nodes.node_list_foreach(session, state, params, lambda: run_body(body))
                    logger.info("[Workflow] Legacy node end List.ForEach")
                    continue
                if ntype == "List.ForEachRange":
                    body = list((bn.get("body") or []))
                    builtin_nodes.node_list_foreach_range(session, state, params, lambda: run_body(body))
                    logger.info("[Workflow] Legacy node end List.ForEachRange")
                    continue
                fn = self._resolve_node_fn(ntype)
                asyncio.get_event_loop().create_task(self._publish(run.id, f"event: step_started\ndata: {ntype}\n\n"))
                try:
                    fn(session, state, params)
                    logger.info(f"[Workflow] Legacy node success type={ntype}")
                    asyncio.get_event_loop().create_task(self._publish(run.id, f"event: step_succeeded\ndata: {ntype}\n\n"))
                except Exception as e:  # noqa: BLE001
                    logger.exception(f"[Workflow] Legacy node failed type={ntype} err={e}")
                    asyncio.get_event_loop().create_task(self._publish(run.id, f"event: step_failed\ndata: {ntype}: {e}\n\n"))
                    raise

        run_body(nodes)
        await self._save_execution_result(session, run, state)

    async def _save_execution_result(self, session: Session, run: WorkflowRun, state: dict) -> None:
        """Save execution result"""
        logger.info(f"[Workflow] Execution finished run_id={run.id}")
        try:
            touched = list(sorted({int(x) for x in (state.get("touched_card_ids") or set())}))
            run.summary_json = {**(run.summary_json or {}), "affected_card_ids": touched}
            session.add(run)
            session.commit()
        except Exception:
            logger.exception("[Workflow] Failed to summarize affected card IDs")

    # ---------------- run ----------------
    def run(self, session: Session, run: WorkflowRun) -> None:
        if run.id in self._run_tasks:
            return

        async def _runner():
            run_id = run.id
            # Ensure event queue exists
            self._ensure_queue(run_id)
            await self._publish(run_id, "event: step_started\n\n")
            try:
                run_db: WorkflowRun = session.exec(select(WorkflowRun).where(WorkflowRun.id == run_id)).one()
                run_db.status = "running"
                run_db.started_at = datetime.utcnow()
                session.add(run_db)
                session.commit()

                workflow = session.exec(select(Workflow).where(Workflow.id == run.workflow_id)).one()
                await self._publish(run_id, "event: log\ndata: Executing DSL...\n\n")
                logger.info(f"[Workflow] run started run_id={run_id} workflow_id={workflow.id}")
                await self._execute_dsl(session, workflow, run)

                run_db = session.exec(select(WorkflowRun).where(WorkflowRun.id == run_id)).one()
                run_db.status = "succeeded"
                run_db.finished_at = datetime.utcnow()
                session.add(run_db)
                session.commit()
                # Publish completion event with affected card IDs
                try:
                    affected = []
                    try:
                        affected = list(sorted({int(x) for x in (run_db.summary_json or {}).get("affected_card_ids", [])}))
                    except Exception:
                        affected = []
                    payload = {"status": "succeeded", "affected_card_ids": affected}
                    import json as _json
                    await self._publish(run_id, f"event: run_completed\ndata: {_json.dumps(payload, ensure_ascii=False)}\n\n")
                except Exception:
                    await self._publish(run_id, "event: run_completed\ndata: {\"status\":\"succeeded\"}\n\n")
            except asyncio.CancelledError:
                run_db = session.exec(select(WorkflowRun).where(WorkflowRun.id == run_id)).one()
                run_db.status = "cancelled"
                run_db.finished_at = datetime.utcnow()
                session.add(run_db)
                session.commit()
                await self._publish(run_id, "event: run_completed\ndata: {\"status\":\"cancelled\"}\n\n")
                raise
            except Exception as e:  # noqa: BLE001
                logger.exception(f"[Workflow] run failed run_id={run_id} err={e}")
                run_db = session.exec(select(WorkflowRun).where(WorkflowRun.id == run_id)).one()
                run_db.status = "failed"
                run_db.finished_at = datetime.utcnow()
                run_db.error_json = {"message": str(e)}
                session.add(run_db)
                session.commit()
                # Failure should also carry affected cards to allow frontend selective refresh
                try:
                    affected = []
                    try:
                        affected = list(sorted({int(x) for x in (run_db.summary_json or {}).get("affected_card_ids", [])}))
                    except Exception:
                        affected = []
                    payload = {"status": "failed", "affected_card_ids": affected, "error": str(e)}
                    import json as _json
                    await self._publish(run_id, f"event: run_completed\ndata: {_json.dumps(payload, ensure_ascii=False)}\n\n")
                except Exception:
                    await self._publish(run_id, "event: run_completed\ndata: {\"status\":\"failed\"}\n\n")
            finally:
                await self._close_queue(run_id)

        task = self._background_run(lambda: _runner(), run.id)
        if task is not None:
            self._run_tasks[run.id] = task

    def cancel(self, run_id: int) -> bool:
        task = self._run_tasks.get(run_id)
        if task and not task.done():
            task.cancel()
            return True
        return False


engine = LocalAsyncEngine()