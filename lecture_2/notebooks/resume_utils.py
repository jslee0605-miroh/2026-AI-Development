"""Utility functions for resume screening with LLMs."""

from typing import Any, Dict, List, Optional
import httpx
import json
import csv
import os


# API Configuration
BASE_URL = "https://openrouter.ai/api/v1"


def load_resume_from_csv(csv_path: str, resume_id: str) -> Optional[Dict[str, str]]:
    """
    Load a single resume from the CSV file by ID.

    Args:
        csv_path: Path to the resumes CSV file
        resume_id: Resume ID to load

    Returns:
        Dict with resume data (ID, Resume_str, Category) or None if not found
    """
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['ID'] == resume_id:
                return {
                    'ID': row['ID'],
                    'Resume_str': row['Resume_str'],
                    'Category': row['Category']
                }
    return None


def load_all_resumes(csv_path: str, limit: Optional[int] = None) -> List[Dict[str, str]]:
    """
    Load all resumes from the CSV file.

    Args:
        csv_path: Path to the resumes CSV file
        limit: Optional limit on number of resumes to load

    Returns:
        List of dicts with resume data
    """
    resumes = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            resumes.append({
                'ID': row['ID'],
                'Resume_str': row['Resume_str'],
                'Category': row['Category']
            })
    return resumes


def load_job_req(job_req_path: str) -> str:
    """
    Load job requisition text from a markdown file.

    Args:
        job_req_path: Path to the job requisition markdown file

    Returns:
        Job requisition text as string
    """
    with open(job_req_path, 'r', encoding='utf-8') as f:
        return f.read()


def chat_completion(
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    base_url: str = BASE_URL,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    response_format: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Make a chat completion request to OpenRouter.

    Args:
        api_key: OpenRouter API key
        model: Model identifier
        messages: List of message dicts with 'role' and 'content'
        base_url: Base URL for OpenRouter API
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        response_format: Optional dict for structured output, e.g. {"type": "json_object"}

    Returns:
        Dict with keys: model, content, error (if any), usage (token counts), parsed_content (if JSON)
    """
    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format

    with httpx.Client(timeout=60) as client:
        try:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            usage = data.get("usage", {})

            # If JSON mode was requested, try to parse the content automatically
            parsed_content = None
            if response_format and response_format.get("type") == "json_object":
                try:
                    parsed_content = json.loads(content)
                except json.JSONDecodeError:
                    pass

            return {
                "model": model,
                "content": content,
                "parsed_content": parsed_content,
                "usage": usage,
                "error": None
            }

        except httpx.HTTPStatusError as e:
            return {
                "model": model,
                "content": "",
                "parsed_content": None,
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
                "usage": {}
            }
        except Exception as e:
            return {
                "model": model,
                "content": "",
                "parsed_content": None,
                "error": str(e),
                "usage": {}
            }


def extract_skills(
    api_key: str,
    resume_text: str,
    model: str = "anthropic/claude-3.5-sonnet"
) -> Dict[str, Any]:
    """
    Extract technical skills and technologies from a resume using an LLM.

    Args:
        api_key: OpenRouter API key
        resume_text: Resume text to analyze
        model: Model to use for extraction

    Returns:
        Dict with extracted skills or error information
    """
    prompt = f"""Extract the technical skills, programming languages, frameworks, and technologies from this resume.

Return a JSON object with this structure:
{{
  "programming_languages": ["list of languages"],
  "frameworks_libraries": ["list of frameworks"],
  "databases": ["list of databases"],
  "cloud_platforms": ["list of cloud platforms"],
  "tools": ["list of development tools"],
  "other_technologies": ["other relevant tech"]
}}

Resume:
{resume_text[:3000]}

Return ONLY valid JSON, no additional text."""

    messages = [{"role": "user", "content": prompt}]

    return chat_completion(
        api_key,
        model,
        messages,
        temperature=0.1,  # Low temperature for consistent extraction
        max_tokens=800,
        response_format={"type": "json_object"}
    )


def match_to_job(
    api_key: str,
    skills: Dict[str, List[str]],
    job_req: str,
    model: str = "anthropic/claude-3.5-sonnet"
) -> Dict[str, Any]:
    """
    Match extracted skills to a job requisition and provide a fit score.

    Args:
        api_key: OpenRouter API key
        skills: Extracted skills dict from extract_skills()
        job_req: Job requisition text
        model: Model to use for matching

    Returns:
        Dict with match results or error information
    """
    skills_json = json.dumps(skills, indent=2)

    prompt = f"""You are evaluating a candidate's fit for a job based on their technical skills.

Candidate Skills:
{skills_json}

Job Requisition:
{job_req[:2000]}

Analyze the match between the candidate's skills and job requirements.

Return a JSON object with this structure:
{{
  "fit_score": <number 0-100>,
  "matching_skills": ["list of skills that match requirements"],
  "missing_skills": ["list of required skills the candidate lacks"],
  "additional_strengths": ["notable skills the candidate has beyond requirements"],
  "recommendation": "<STRONG_FIT|GOOD_FIT|MODERATE_FIT|WEAK_FIT|POOR_FIT>",
  "reasoning": "<brief 2-3 sentence explanation>"
}}

Return ONLY valid JSON, no additional text."""

    messages = [{"role": "user", "content": prompt}]

    return chat_completion(
        api_key,
        model,
        messages,
        temperature=0.3,
        max_tokens=1000,
        response_format={"type": "json_object"}
    )


def screen_resume_vertical_slice(
    api_key: str,
    resume_id: str,
    csv_path: str,
    job_req_path: str,
    model: str = "anthropic/claude-3.5-sonnet"
) -> Dict[str, Any]:
    """
    Complete vertical slice: Load resume -> Extract skills -> Match to job.

    This demonstrates end-to-end processing for a single resume.

    Args:
        api_key: OpenRouter API key
        resume_id: Resume ID to process
        csv_path: Path to resumes CSV
        job_req_path: Path to job requisition file
        model: Model to use

    Returns:
        Dict with complete screening results
    """
    # Step 1: Load resume
    resume = load_resume_from_csv(csv_path, resume_id)
    if not resume:
        return {"error": f"Resume {resume_id} not found"}

    # Step 2: Load job req
    job_req = load_job_req(job_req_path)

    # Step 3: Extract skills
    skills_result = extract_skills(api_key, resume['Resume_str'], model)
    if skills_result.get('error'):
        return {"error": f"Skill extraction failed: {skills_result['error']}"}

    skills = skills_result['parsed_content']
    if not skills:
        return {"error": "Failed to parse skills JSON"}

    # Step 4: Match to job
    match_result = match_to_job(api_key, skills, job_req, model)
    if match_result.get('error'):
        return {"error": f"Job matching failed: {match_result['error']}"}

    match_data = match_result['parsed_content']
    if not match_data:
        return {"error": "Failed to parse match JSON"}

    # Combine results
    return {
        "resume_id": resume_id,
        "category": resume['Category'],
        "skills": skills,
        "match": match_data,
        "total_tokens": skills_result['usage'].get('total_tokens', 0) + match_result['usage'].get('total_tokens', 0)
    }
