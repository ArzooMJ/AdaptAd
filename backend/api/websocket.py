"""
WebSocket handler for real-time GA evolution updates.

WS /ws/evolve/{job_id}

Protocol:
  Server -> client:
    {"type": "generation", "data": {generation, best_fitness, avg_fitness, diversity}}
    {"type": "converged",  "data": {final_generation, best_chromosome, fitness}}
    {"type": "error",      "data": {message}}

  Client -> server:
    {"type": "pause"}
    {"type": "resume"}
    {"type": "stop"}
"""

import asyncio
import json
import queue

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .routes_evolve import _jobs

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/evolve/{job_id}")
async def evolve_websocket(websocket: WebSocket, job_id: str):
    await websocket.accept()

    if job_id not in _jobs:
        await websocket.send_json({"type": "error", "data": {"message": f"Job {job_id} not found."}})
        await websocket.close()
        return

    job = _jobs[job_id]

    # Attach a queue so the background task can push updates.
    ws_queue: queue.Queue = queue.Queue()
    job["ws_queue"] = ws_queue

    # Send any history already accumulated before client connected.
    for hist_entry in job.get("history", []):
        await websocket.send_json({"type": "generation", "data": hist_entry})

    # If job already finished before WS connected, send converged now and exit.
    if job.get("status") == "completed":
        engine = job.get("engine")
        genes = engine.best_chromosome.to_vector() if engine and engine.best_chromosome else []
        fitness = engine.best_fitness if engine else (job.get("best_fitness") or 0.0)
        await websocket.send_json({
            "type": "converged",
            "data": {
                "final_generation": job.get("current_generation", 0),
                "best_chromosome": genes,
                "fitness": fitness,
            },
        })
        await websocket.close()
        return

    try:
        while True:
            # Check for new messages from the evolution background task.
            try:
                msg = ws_queue.get_nowait()
                await websocket.send_json(msg)
                if msg.get("type") in ("converged", "error"):
                    break
            except queue.Empty:
                pass

            # Check for client messages (pause/resume/stop).
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                client_msg = json.loads(raw)
                msg_type = client_msg.get("type")
                if msg_type == "stop":
                    job["stop_requested"] = True
                    await websocket.send_json({"type": "stopped", "data": {}})
                    break
                elif msg_type == "pause":
                    job["paused"] = True
                elif msg_type == "resume":
                    job["paused"] = False
            except asyncio.TimeoutError:
                pass
            except Exception:
                pass

            # Exit if job is done and queue is drained.
            if job.get("status") in ("completed", "error") and ws_queue.empty():
                break

            await asyncio.sleep(0.05)

    except WebSocketDisconnect:
        # Evolution continues in background. Client can reconnect.
        pass
    finally:
        job["ws_queue"] = None
        try:
            await websocket.close()
        except Exception:
            pass
