from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import uuid
import os

from app.agents.content_writer_agent import ContentWriterAgent
from app.doc.doc_constructor_agent import build_document

app = FastAPI(title="ABAP Functional Spec Generator")
JOBS = {}

def generate_doc_background(payload, job_id):
    try:
        agent = ContentWriterAgent()
        results = agent.run(payload)

        sections = [{"title": sec["section_name"], "type": "text"} for sec in results]

        doc = build_document(results, sections)
        output_filename = f"Functional_Spec_{job_id}.docx"
        output_path = os.path.abspath(output_filename)
        doc.save(output_path)

        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["file_path"] = output_path
    except Exception as e:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(e)

@app.post("/generate_doc")
async def generate_doc(payload: dict, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "pending", "file_path": None}
    background_tasks.add_task(generate_doc_background, payload, job_id)
    return {"job_id": job_id, "status": "started"}

@app.get("/generate_doc/{job_id}")
async def get_doc(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404)

    if job["status"] == "pending":
        return {"status": "pending"}

    if job["status"] == "done":
        return FileResponse(job["file_path"])

    return JSONResponse(status_code=500, content={"error": job["error"]})
