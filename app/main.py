from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import uuid
import os
import io

from app.agents.content_writer_agent import ContentWriterAgent
from app.doc.doc_constructor_agent import build_document

app = FastAPI(title="ABAP Functional Spec Generator")
JOBS = {}  # job_id -> {"status": ..., "file_bytes": ..., "error": ...}


def generate_doc_background(payload, job_id):
    try:
        agent = ContentWriterAgent()
        results = agent.run(payload)

        sections = [{"title": sec["section_name"], "type": "text"} for sec in results]

        doc = build_document(results, sections)

        # ---------------------------
        # SAVE DOCX TO MEMORY (BytesIO)
        # ---------------------------
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        # Store bytes in memory
        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["file_bytes"] = buffer.getvalue()

    except Exception as e:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(e)


@app.post("/generate_doc")
async def generate_doc(payload: dict, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "pending", "file_bytes": None, "error": None}
    background_tasks.add_task(generate_doc_background, payload, job_id)
    return {"job_id": job_id, "status": "started"}


@app.get("/generate_doc/{job_id}")
async def get_doc(job_id: str):

    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, detail="Invalid job_id")

    if job["status"] == "pending":
        return {"status": "pending"}

    if job["status"] == "failed":
        return JSONResponse(status_code=500, content={"status": "failed", "error": job["error"]})

    if job["status"] == "done":
        file_bytes = job["file_bytes"]
        if not file_bytes:
            raise HTTPException(500, detail="No file found in memory")

        # Return as download
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=Functional_Spec_{job_id}.docx"
            }
        )
