"""
API Client for Streamlit UI

Handles all HTTP communication with the FastAPI backend.
"""

import requests
from typing import List, Dict, Any, Optional


class APIClient:
    """Client for WebScribe API"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    def scrape_urls(
        self,
        urls: List[str],
        engine: str = "static",
        template_id: str = "research-summary"
    ) -> Dict[str, Any]:
        """
        Submit URLs for scraping.

        Returns:
            {"jobs": [{"job_id": "...", "url": "...", "status": "queued"}, ...]}
        """
        response = requests.post(
            f"{self.base_url}/v1/scrape",
            json={
                "urls": urls,
                "engine": engine,
                "template_id": template_id
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get job status and details.

        Returns:
            {
                "job_id": "...",
                "url": "...",
                "status": "running",
                "logs": [...],
                "created_at": "...",
                "updated_at": "..."
            }
        """
        response = requests.get(
            f"{self.base_url}/v1/jobs/{job_id}",
            timeout=5
        )
        response.raise_for_status()
        return response.json()

    def get_notes_for_job(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get all note versions for a job.

        Returns:
            {
                "notes": [
                    {
                        "id": "...",
                        "job_id": "...",
                        "title": "...",
                        "content": "...",
                        "template_id": "...",
                        "tags": [...],
                        "version": 1,
                        "saved_path": null,
                        "created_at": "..."
                    },
                    ...
                ]
            }
        """
        response = requests.get(
            f"{self.base_url}/v1/notes/{job_id}",
            timeout=5
        )
        response.raise_for_status()
        return response.json()["notes"]

    def update_note(
        self,
        note_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a note's title and/or content.

        Returns:
            Updated note object
        """
        payload = {}
        if title is not None:
            payload["title"] = title
        if content is not None:
            payload["content"] = content

        response = requests.put(
            f"{self.base_url}/v1/notes/{note_id}",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def save_note_to_kb(self, note_id: str) -> Dict[str, Any]:
        """
        Save a note to the Knowledge Base.

        Returns:
            {"note_id": "...", "saved_path": "/path/to/file.md"}
        """
        response = requests.post(
            f"{self.base_url}/v1/notes/{note_id}/save",
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def rerun_ai_synthesis(self, job_id: str, template_id: str) -> Dict[str, Any]:
        """
        Re-run AI synthesis with a different template.

        Returns:
            {"job_id": "...", "message": "..."}
        """
        response = requests.post(
            f"{self.base_url}/v1/jobs/{job_id}/rerun",
            json={"template_id": template_id},
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def health_check(self) -> bool:
        """
        Check if API is healthy.

        Returns:
            True if API is responding, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
