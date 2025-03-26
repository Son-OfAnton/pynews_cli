"""
Utilities for testing Job listings functionality.
"""
import json
from unittest.mock import Mock


def create_mock_response(status_code=200, json_data=None):
    """Create a mock requests response object with the given status code and JSON data."""
    mock_response = Mock()
    mock_response.status_code = status_code
    
    def mock_json():
        return json_data
        
    mock_response.json = mock_json
    
    return mock_response


def generate_mock_job_story(job_id=20000, score=5, title="Job: Software Engineer at Example Corp"):
    """
    Generate a mock job story.
    
    Args:
        job_id: ID for the job story
        score: Job story score
        title: Job title with company name
        
    Returns:
        Dictionary representing a job story
    """
    return {
        "id": job_id,
        "title": title,
        "text": "<p>This is a job description for a position at Example Corp.</p><p>Requirements: Python, JavaScript, etc.</p>",
        "score": score,
        "time": 1616513396,  # Example timestamp
        "by": "user123",
        "type": "job",
        "url": f"https://example.com/jobs/{job_id}"
    }


def generate_mock_job_stories(num_jobs=10, base_id=20000, vary_timestamps=True, vary_scores=True):
    """
    Generate a list of mock job stories with various attributes.
    
    Args:
        num_jobs: Number of job stories to generate
        base_id: Starting ID for the jobs
        vary_timestamps: If True, give each job a different timestamp
        vary_scores: If True, vary job scores
        
    Returns:
        List of job story dictionaries
    """
    import random
    
    companies = ["Google", "Amazon", "Meta", "Apple", "Microsoft", "Netflix", "Startup", 
                "Tesla", "SpaceX", "Remote Company"]
    positions = ["Software Engineer", "Frontend Developer", "Backend Engineer", "Data Scientist",
                "Product Manager", "DevOps Engineer", "Full Stack Developer", "Mobile Developer",
                "ML Engineer", "Technical Writer"]
    
    jobs = []
    base_time = 1616513396
    
    for i in range(num_jobs):
        job_id = base_id + i
        company = companies[i % len(companies)]
        position = positions[i % len(positions)]
        title = f"Job: {position} at {company}"
        
        # Generate varying timestamps if requested
        timestamp = base_time + (3600 * i if vary_timestamps else 0)
        
        # Generate varying scores if requested
        score = random.randint(1, 30) if vary_scores else 5
        
        # Create job with keywords in the text for testing keyword filtering
        keywords = ["remote", "senior", "junior", "entry-level", "Python", "JavaScript", "React", "SQL"]
        selected_keywords = random.sample(keywords, 3)  # Pick 3 random keywords
        text = f"<p>This is a job for a {position} at {company}.</p><p>We're looking for someone with skills in {', '.join(selected_keywords)}.</p>"
        
        jobs.append({
            "id": job_id,
            "title": title,
            "text": text,
            "score": score,
            "time": timestamp,
            "by": f"user{i}",
            "type": "job",
            "url": f"https://example.com/jobs/{job_id}"
        })
    
    return jobs


def generate_job_story_ids(num_jobs=100):
    """Generate a list of mock job story IDs."""
    return list(range(20000, 20000 + num_jobs))