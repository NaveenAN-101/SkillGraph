from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from db import run_query
from fastapi.middleware.cors import CORSMiddleware
from neo4j.exceptions import ConstraintError
from datetime import datetime, timezone
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

app = FastAPI(title="SkillGraph API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "SkillGraph API running 🚀"}


@app.get("/learning-path/{job}")
def learning_path(job: str):
    query = """
    MATCH (j:JobRole {title: $job})-[:REQUIRES]->(s:Skill)

    OPTIONAL MATCH path = (root:Skill)-[:PREREQUISITE_OF*0..]->(s)

    WITH s, coalesce(max(length(path)), 0) AS depth

    RETURN s.name AS skill, depth
    ORDER BY depth ASC, skill ASC
    """
    return run_query(query, {"job": job})


@app.get("/skill-gap/{user}/{job}")
def skill_gap(user: str, job: str):
    query = """
    MATCH (u:User {user_id: $user})
    MATCH (j:JobRole {title: $job})-[:REQUIRES]->(req:Skill)
    WHERE NOT (u)-[:HAS_SKILL]->(req)
    RETURN DISTINCT req.name AS missing_skill,
           req.level AS required_level
    """
    return run_query(query, {"user": user, "job": job})


@app.get("/course-recommendations/{user}/{job}")
def course_recommendations(user: str, job: str):
    query = """
    MATCH (u:User {user_id: $user})
    MATCH (j:JobRole {title: $job})-[:REQUIRES]->(s:Skill)
    WHERE NOT (u)-[:HAS_SKILL]->(s)
    MATCH (c:Course)-[:TEACHES]->(s)
    RETURN DISTINCT
        s.name AS missing_skill,
        c.name AS recommended_course,
        c.platform AS platform,
        c.difficulty AS difficulty
    """
    return run_query(query, {"user": user, "job": job})


class UserCreate(BaseModel):
    user_id: str
    name: str
    level: str

class UserUpdate(BaseModel):
    name: str
    level: str

class UserSkill(BaseModel):
    user_id: str
    skill_name: str
    proficiency: int



@app.post("/users")
def create_user(user: UserCreate):
    query = """
    CREATE (u:User {
        user_id: $user_id,
        name: $name,
        level: $level
    })
    RETURN u
    """
    return run_query(query, user.dict())

@app.get("/users")
def get_users():
    query = """
    MATCH (u:User)
    RETURN u.user_id AS user_id, u.name AS name, u.level AS level
    """
    return run_query(query)

@app.get("/users/{user_id}")
def get_user(user_id: str):
    query = """
    MATCH (u:User {user_id: $user_id})
    RETURN u.user_id AS user_id, u.name AS name, u.level AS level
    """
    result = run_query(query, {"user_id": user_id})
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result

@app.put("/users/{user_id}")
def update_user(user_id: str, data: UserUpdate):
    query = """
    MATCH (u:User {user_id: $user_id})
    SET u.name = $name,
        u.level = $level
    RETURN u
    """
    result = run_query(query, {"user_id": user_id, **data.dict()})
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result

@app.delete("/users/{user_id}")
def delete_user(user_id: str):
    query = """
    MATCH (u:User {user_id: $user_id})
    DETACH DELETE u
    """
    run_query(query, {"user_id": user_id})
    return {"status": "User deleted"}

class SkillCreate(BaseModel):
    name: str
    category: str
    level: str


@app.post("/skills")
def create_skill(skill: SkillCreate):
    query = """
    CREATE (s:Skill {
        name: $name,
        category: $category,
        level: $level
    })
    RETURN s
    """
    try:
        return run_query(query, skill.dict())
    except ConstraintError:
        raise HTTPException(
            status_code=400,
            detail="Skill already exists"
        )

@app.get("/skills")
def get_skills():
    query = """
    MATCH (s:Skill)
    RETURN s.name AS name, s.category AS category, s.level AS level
    """
    return run_query(query)

@app.delete("/skills/{name}")
def delete_skill(name: str):
    query = """
    MATCH (s:Skill {name: $name})
    DETACH DELETE s
    """
    run_query(query, {"name": name})
    return {"status": "Skill deleted"}

class JobRoleCreate(BaseModel):
    title: str
    domain: str
    experience_level: str

@app.post("/jobroles")
def create_jobrole(job: JobRoleCreate):
    query = """
    CREATE (j:JobRole {
        title: $title,
        domain: $domain,
        experience_level: $experience_level
    })
    RETURN j
    """
    try:
        return run_query(query, job.dict())
    except ConstraintError:
        raise HTTPException(
            status_code=400,
            detail="JobRole already exists"
        )

@app.get("/jobroles")
def get_jobroles():
    query = """
    MATCH (j:JobRole)
    RETURN j.title AS title,
           j.domain AS domain,
           j.experience_level AS experience_level
    """
    return run_query(query)

@app.delete("/jobroles/{title}")
def delete_jobrole(title: str):
    query = """
    MATCH (j:JobRole {title: $title})
    DETACH DELETE j
    """
    run_query(query, {"title": title})
    return {"status": "JobRole deleted"}

class CourseCreate(BaseModel):
    name: str
    platform: str
    difficulty: str
    duration_hours: int
    skill_name: str

@app.post("/courses")
def create_course(course: CourseCreate):
    query = """
    MATCH (s:Skill {name: $skill_name})
    WITH s
    WHERE s IS NOT NULL

    MERGE (c:Course {name: $name})
    SET c.platform = $platform,
      c.difficulty = $difficulty,
      c.duration_hours = $duration_hours
    MERGE (c)-[:TEACHES]->(s)

    RETURN c, s
    """
    result = run_query(query, course.dict())

    if not result:
        raise HTTPException(
            status_code=400,
            detail="Skill not found. Course not created."
        )

    return result 

@app.get("/courses")
def get_courses():
    query = """
    MATCH (c:Course)
    RETURN c.name AS name,
           c.platform AS platform,
           c.difficulty AS difficulty,
           c.duration_hours AS duration_hours
    """
    return run_query(query)

@app.delete("/courses/{name}")
def delete_course(name: str):
    query = """
    MATCH (c:Course {name: $name})
    DETACH DELETE c
    """
    run_query(query, {"name": name})
    return {"status": "Course deleted"}

class JobSkillRelation(BaseModel):
    job_title: str
    skill_name: str

@app.post("/jobroles/add-skill")
def add_skill_to_job(data: JobSkillRelation):
    query = """
    MATCH (j:JobRole {title: $job_title})
    MATCH (s:Skill {name: $skill_name})
    MERGE (j)-[:REQUIRES]->(s)
    RETURN j, s
    """
    return run_query(query, data.dict())

class SkillPrerequisite(BaseModel):
    prerequisite: str
    target_skill: str

@app.post("/skills/add-prerequisite")
def add_prerequisite(data: SkillPrerequisite):

    # Prevent self-dependency
    if data.prerequisite == data.target_skill:
        raise HTTPException(status_code=400, detail="Skill cannot depend on itself")

    # Check reverse dependency
    check_query = """
    MATCH (a:Skill {name: $target})
    MATCH (b:Skill {name: $prereq})
    MATCH (a)-[:PREREQUISITE_OF]->(b)
    RETURN a
    """
    reverse = run_query(check_query, {
        "target": data.target_skill,
        "prereq": data.prerequisite
    })

    if reverse:
        raise HTTPException(status_code=400, detail="Circular dependency detected")

    query = """
    MATCH (a:Skill {name: $prerequisite})
    MATCH (b:Skill {name: $target_skill})
    MERGE (a)-[:PREREQUISITE_OF]->(b)
    RETURN a, b
    """
    return run_query(query, data.dict())

class CourseSkillRelation(BaseModel):
    course_name: str
    skill_name: str


@app.post("/courses/add-skill")
def add_course_skill(data: CourseSkillRelation):
    query = """
    MATCH (c:Course {name: $course_name})
    MATCH (s:Skill {name: $skill_name})
    RETURN c, s
    """
    result = run_query(query, data.dict())

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Course or Skill not found"
        )

    relation_query = """
    MATCH (c:Course {name: $course_name})
    MATCH (s:Skill {name: $skill_name})
    MERGE (c)-[:TEACHES]->(s)
    RETURN c, s
    """
    return run_query(relation_query, data.dict())

@app.delete("/jobroles/remove-skill")
def remove_skill_from_job(data: JobSkillRelation):
    query = """
    MATCH (j:JobRole {title: $job_title})
    MATCH (s:Skill {name: $skill_name})
    MATCH (j)-[r:REQUIRES]->(s)
    DELETE r
    RETURN j, s
    """
    result = run_query(query, data.dict())
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Relationship not found"
        )
    return {"status": "Skill removed from job"}

@app.delete("/skills/remove-prerequisite")
def remove_prerequisite(data: SkillPrerequisite):
    query = """
    MATCH (a:Skill {name: $prerequisite})
    MATCH (b:Skill {name: $target_skill})
    MATCH (a)-[r:PREREQUISITE_OF]->(b)
    DELETE r
    RETURN a, b
    """
    result = run_query(query, data.dict())
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Prerequisite relationship not found"
        )
    return {"status": "Prerequisite removed"}

@app.delete("/courses/remove-skill")
def remove_course_skill(data: CourseSkillRelation):
    query = """
    MATCH (c:Course {name: $course_name})
    MATCH (s:Skill {name: $skill_name})
    MATCH (c)-[r:TEACHES]->(s)
    DELETE r
    RETURN c, s
    """
    result = run_query(query, data.dict())
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Relationship not found"
        )
    return {"status": "Course no longer teaches skill"}

@app.get("/jobroles/{title}/skills")
def get_job_skills(title: str):
    query = """
    MATCH (j:JobRole {title: $title})
    OPTIONAL MATCH (j)-[:REQUIRES]->(s:Skill)
    RETURN s.name AS skill,
           s.category AS category,
           s.level AS level
    """
    return run_query(query, {"title": title})

@app.get("/skills/{name}/prerequisites")
def get_skill_prerequisites(name: str):
    query = """
    MATCH (a:Skill)-[:PREREQUISITE_OF]->(b:Skill {name: $name})
    RETURN a.name AS prerequisite
    """
    return run_query(query, {"name": name})

@app.get("/skills/{name}/courses")
def get_skill_courses(name: str):
    query = """
    MATCH (c:Course)-[:TEACHES]->(s:Skill {name: $name})
    RETURN c.name AS course,
           c.platform AS platform,
           c.difficulty AS difficulty
    """
    return run_query(query, {"name": name})

@app.get("/progress/{user_id}/{job_title}")
def calculate_progress(user_id: str, job_title: str):
    query = """
    MATCH (j:JobRole {title: $job_title})-[:REQUIRES]->(s:Skill)
    WITH collect(DISTINCT s) AS required_skills

    OPTIONAL MATCH (u:User {user_id: $user_id})-[:HAS_SKILL]->(us:Skill)
    WITH required_skills, collect(DISTINCT us) AS user_skills

    RETURN size(required_skills) AS total_required,
       size([x IN required_skills WHERE x IN user_skills]) AS matched

    """
    result = run_query(query, {"user_id": user_id, "job_title": job_title})

    if not result:
        raise HTTPException(status_code=404, detail="User or Job not found")

    total = result[0]["total_required"]
    matched = result[0]["matched"]

    percent = 0
    if total > 0:
        percent = (matched / total) * 100

    return {
        "total_required": total,
        "matched": matched,
        "progress_percent": round(percent, 2)
    }

@app.post("/users/add-skill")
def add_user_skill(data: UserSkill):
    query = """
    MATCH (u:User {user_id: $user_id})
    MATCH (s:Skill {name: $skill_name})
    MERGE (u)-[r:HAS_SKILL]->(s)
    SET r.proficiency = $proficiency
    RETURN 
        u.user_id AS user_id,
        s.name AS skill,
        r.proficiency AS proficiency
    """
    result = run_query(query, data.dict())
    if not result:
        raise HTTPException(
            status_code=404,
            detail="User or Skill not found"
        )
    return result

@app.get("/graph/{job}")
def get_graph(job: str):
    query = """
    MATCH (j:JobRole {title: $job})
    OPTIONAL MATCH (j)-[:REQUIRES]->(s:Skill)
    OPTIONAL MATCH (p:Skill)-[:PREREQUISITE_OF]->(s)
    OPTIONAL MATCH (c:Course)-[:TEACHES]->(s)

    RETURN
      j.title AS job,
      s.name AS skill,
      p.name AS prerequisite,
      c.name AS course
    """
    return run_query(query, {"job": job})

@app.get("/career-recommendations/{user_id}")
def recommend_jobs(user_id: str):

    query = """
    MATCH (u:User {user_id: $user_id})-[:HAS_SKILL]->(us:Skill)

    MATCH (j:JobRole)-[:REQUIRES]->(s:Skill)

    WITH u, j, collect(DISTINCT s) AS required_skills,
         collect(DISTINCT us) AS user_skills

    RETURN 
        j.title AS job,
        size(required_skills) AS total_required,
        size([x IN required_skills WHERE x IN user_skills]) AS matched,
        round(
            toFloat(size([x IN required_skills WHERE x IN user_skills])) /
            size(required_skills) * 100, 2
        ) AS match_percent

    ORDER BY match_percent DESC
    """

    return run_query(query, {"user_id": user_id})

@app.get("/career-transition/{user_id}")
def career_transition(user_id: str):

    query = """
    MATCH (u:User {user_id:$user_id})-[:HAS_SKILL]->(us:Skill)

    MATCH (j:JobRole)-[:REQUIRES]->(s:Skill)

    WITH u, j,
         collect(DISTINCT us) AS user_skills,
         collect(DISTINCT s) AS required_skills

    WITH j,
         required_skills,
         user_skills,
         [x IN required_skills WHERE x IN user_skills] AS matched,
         [x IN required_skills WHERE NOT x IN user_skills] AS missing

    WITH j,
         size(required_skills) AS total_required,
         size(matched) AS matched_count,
         missing

    OPTIONAL MATCH (c:Course)-[:TEACHES]->(ms:Skill)
    WHERE ms IN missing

    RETURN
        j.title AS job,
        total_required,
        matched_count,
        round(toFloat(matched_count)/total_required * 100,2) AS match_percent,
        [m IN missing | m.name] AS missing_skills,
        collect(DISTINCT c.name) AS recommended_courses

    ORDER BY match_percent DESC
    """
    
    return run_query(query, {"user_id": user_id})

@app.get("/career-graph/{user_id}/{job_title}")
def career_graph(user_id: str, job_title: str):

    query = """
    MATCH (u:User {user_id:$user_id})

    OPTIONAL MATCH (u)-[:HAS_SKILL]->(us:Skill)

    MATCH (j:JobRole {title:$job_title})-[:REQUIRES]->(s:Skill)

    WITH u, j, collect(DISTINCT us) AS user_skills, collect(DISTINCT s) AS required_skills

    WITH u, j,
         user_skills,
         required_skills,
         [x IN required_skills WHERE x IN user_skills] AS matched,
         [x IN required_skills WHERE NOT x IN user_skills] AS missing

    OPTIONAL MATCH (c:Course)-[:TEACHES]->(ms:Skill)
    WHERE ms IN missing

    RETURN
        u.user_id AS user,
        j.title AS job,
        [x IN matched | x.name] AS matched_skills,
        [x IN missing | x.name] AS missing_skills,
        collect(DISTINCT c.name) AS courses
    """

    return run_query(query, {"user_id": user_id, "job_title": job_title})


class AIRoadmapRequest(BaseModel):
    user_id: str
    target_job: str
    weeks: int = 12
    hours_per_week: int = 6


@app.post("/ai-roadmap")
def ai_skill_copilot(payload: AIRoadmapRequest):
    if payload.weeks < 4 or payload.weeks > 24:
        raise HTTPException(status_code=400, detail="weeks must be between 4 and 24")
    if payload.hours_per_week < 1 or payload.hours_per_week > 30:
        raise HTTPException(status_code=400, detail="hours_per_week must be between 1 and 30")

    # Validate user and target job
    user_exists = run_query(
        "MATCH (u:User {user_id: $user_id}) RETURN u.user_id AS user_id",
        {"user_id": payload.user_id}
    )
    if not user_exists:
        raise HTTPException(status_code=404, detail="User not found")

    job_exists = run_query(
        "MATCH (j:JobRole {title: $title}) RETURN j.title AS title",
        {"title": payload.target_job}
    )
    if not job_exists:
        raise HTTPException(status_code=404, detail="Target job not found")

    # Collect missing skills with rough dependency depth
    missing_query = """
    MATCH (u:User {user_id: $user_id})
    MATCH (j:JobRole {title: $job})-[:REQUIRES]->(req:Skill)
    WHERE NOT (u)-[:HAS_SKILL]->(req)
    OPTIONAL MATCH p = (root:Skill)-[:PREREQUISITE_OF*0..]->(req)
    WITH req, coalesce(max(length(p)), 0) AS depth
    RETURN req.name AS skill, req.level AS level, depth
    ORDER BY depth ASC, skill ASC
    """
    missing_skills = run_query(
        missing_query,
        {"user_id": payload.user_id, "job": payload.target_job}
    )

    if not missing_skills:
        return {
            "user_id": payload.user_id,
            "target_job": payload.target_job,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overview": {
                "status": "job_ready",
                "message": "You already match this role's required skills."
            },
            "roadmap": []
        }

    # Fetch course options for missing skills
    course_query = """
    MATCH (c:Course)-[:TEACHES]->(s:Skill)
    WHERE s.name IN $skills
    RETURN s.name AS skill,
           c.name AS course,
           c.platform AS platform,
           c.difficulty AS difficulty,
           c.duration_hours AS duration
    ORDER BY duration ASC, course ASC
    """
    course_rows = run_query(
        course_query,
        {"skills": [row["skill"] for row in missing_skills]}
    )

    course_map = {}
    for row in course_rows:
        skill = row["skill"]
        course_map.setdefault(skill, [])
        course_map[skill].append({
            "name": row["course"],
            "platform": row["platform"],
            "difficulty": row["difficulty"],
            "duration_hours": row["duration"] or 0
        })

    # Build deterministic weekly plan ("AI copilot style" explanation + adaptive blocks)
    roadmap = []
    total_hours = payload.weeks * payload.hours_per_week
    per_skill_hours = max(3, int(total_hours / max(1, len(missing_skills))))

    for idx, skill_row in enumerate(missing_skills):
        skill = skill_row["skill"]
        week_slot = min(payload.weeks, idx + 1)
        phase = "30-day"
        if week_slot > 4 and week_slot <= 8:
            phase = "60-day"
        elif week_slot > 8:
            phase = "90-day"

        chosen_courses = course_map.get(skill, [])[:2]
        roadmap.append({
            "week": week_slot,
            "phase": phase,
            "focus_skill": skill,
            "skill_level": skill_row["level"],
            "dependency_depth": skill_row["depth"],
            "recommended_hours": per_skill_hours,
            "courses": chosen_courses,
            "milestone": f"Build one mini-project using {skill}"
        })

    return {
        "user_id": payload.user_id,
        "target_job": payload.target_job,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overview": {
            "status": "in_progress",
            "missing_skill_count": len(missing_skills),
            "weeks_planned": payload.weeks,
            "hours_per_week": payload.hours_per_week,
            "message": "Roadmap generated from your current gaps, dependencies, and available courses."
        },
        "roadmap": roadmap
    }


SKILL_ALIASES = {
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "nlp": "NLP",
    "genai": "Generative AI",
    "llm": "LLM",
    "python": "Python",
    "sql": "SQL",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "fast api": "FastAPI",
    "fastapi": "FastAPI",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "react.js": "React",
    "react": "React",
    "docker": "Docker",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "airflow": "Airflow",
    "spark": "Spark",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "ci/cd": "CI/CD",
}


def _http_get_json(url: str, timeout: int = 12):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SkillGraphMarketSync/1.0"
        }
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


def _fetch_remotive_jobs(limit: int = 120):
    data = _http_get_json("https://remotive.com/api/remote-jobs")
    rows = data.get("jobs", [])
    posts = []
    for row in rows[:limit]:
        posts.append({
            "source": "Remotive",
            "external_id": str(row.get("id", "")) or hashlib.md5((row.get("url", "") + row.get("title", "")).encode("utf-8")).hexdigest(),
            "title": row.get("title", "Unknown Role"),
            "company": row.get("company_name", "Unknown Company"),
            "url": row.get("url", ""),
            "published_at": row.get("publication_date", ""),
            "text_blob": " ".join([
                row.get("title", ""),
                row.get("category", ""),
                row.get("candidate_required_location", ""),
                row.get("description", "")[:2500]
            ])
        })
    return posts


def _fetch_arbeitnow_jobs(limit: int = 120):
    # Public feed with pagination
    page = 1
    posts = []
    while len(posts) < limit:
        url = f"https://www.arbeitnow.com/api/job-board-api?page={page}"
        data = _http_get_json(url)
        rows = data.get("data", [])
        if not rows:
            break
        for row in rows:
            tags = row.get("tags") or []
            posts.append({
                "source": "Arbeitnow",
                "external_id": str(row.get("slug", "")) or hashlib.md5((row.get("job_id", "") + row.get("title", "")).encode("utf-8")).hexdigest(),
                "title": row.get("title", "Unknown Role"),
                "company": row.get("company_name", "Unknown Company"),
                "url": row.get("url", ""),
                "published_at": row.get("created_at", ""),
                "text_blob": " ".join([
                    row.get("title", ""),
                    row.get("description", "")[:2500],
                    " ".join(tags)
                ])
            })
            if len(posts) >= limit:
                break
        if not data.get("links", {}).get("next"):
            break
        page += 1
    return posts


def _fallback_market_posts():
    return [
        {
            "source": "FallbackSeed",
            "external_id": "seed-001",
            "title": "AI Engineer",
            "company": "Nova Analytics",
            "url": "",
            "published_at": "",
            "text_blob": "Python Machine Learning SQL Docker FastAPI LLM"
        },
        {
            "source": "FallbackSeed",
            "external_id": "seed-002",
            "title": "Data Engineer",
            "company": "CloudForge",
            "url": "",
            "published_at": "",
            "text_blob": "Python SQL Airflow Spark AWS ETL"
        },
        {
            "source": "FallbackSeed",
            "external_id": "seed-003",
            "title": "Backend Developer",
            "company": "StackPilot",
            "url": "",
            "published_at": "",
            "text_blob": "Python FastAPI Docker PostgreSQL CI/CD"
        },
        {
            "source": "FallbackSeed",
            "external_id": "seed-004",
            "title": "ML Ops Engineer",
            "company": "ScaleMind",
            "url": "",
            "published_at": "",
            "text_blob": "Docker Kubernetes Python CI/CD MLOps"
        }
    ]


def _extract_skills_from_text(text: str, known_skills: list[str]):
    normalized = re.sub(r"\s+", " ", (text or "").lower())
    found = set()

    for skill in known_skills:
        token = skill.lower()
        if token and token in normalized:
            found.add(skill)

    for alias, canonical in SKILL_ALIASES.items():
        if alias in normalized:
            found.add(canonical)

    return sorted(found)


@app.post("/market/sync")
def sync_market_job_posts(source: str = "all", max_posts: int = 220, allow_fallback: bool = True):
    """
    Free-market sync pipeline:
    - pulls from public/free sources when available
    - falls back to seeded feed for demos/offline usage
    - deduplicates by source+external id
    - updates skill links and prunes stale posts
    """
    source = (source or "all").strip().lower()
    if source not in {"all", "remotive", "arbeitnow", "fallback"}:
        raise HTTPException(status_code=400, detail="source must be one of: all, remotive, arbeitnow, fallback")
    if max_posts < 10 or max_posts > 500:
        raise HTTPException(status_code=400, detail="max_posts must be between 10 and 500")

    fetchers = []
    if source in {"all", "remotive"}:
        fetchers.append(("Remotive", _fetch_remotive_jobs))
    if source in {"all", "arbeitnow"}:
        fetchers.append(("Arbeitnow", _fetch_arbeitnow_jobs))

    raw_posts = []
    source_errors = []
    source_success = []

    if source == "fallback":
        raw_posts = _fallback_market_posts()
        source_success.append("FallbackSeed")
    else:
        per_source_limit = max(30, int(max_posts / max(1, len(fetchers))))
        for source_name, fetcher in fetchers:
            try:
                rows = fetcher(per_source_limit)
                raw_posts.extend(rows)
                source_success.append(source_name)
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as err:
                source_errors.append({"source": source_name, "error": str(err)})

    if not raw_posts and allow_fallback:
        raw_posts = _fallback_market_posts()
        source_success.append("FallbackSeed")

    if not raw_posts:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "No market posts fetched from available sources",
                "errors": source_errors
            }
        )

    # Dedupe by source + external id
    deduped = {}
    for post in raw_posts:
        key = f"{post['source']}::{post['external_id']}"
        if key not in deduped:
            deduped[key] = post

    posts = list(deduped.values())[:max_posts]
    ts = datetime.now(timezone.utc).isoformat()
    epoch_now = int(time.time())
    stale_cutoff = epoch_now - (45 * 24 * 3600)

    known_skill_rows = run_query("MATCH (s:Skill) RETURN s.name AS name")
    known_skills = [r["name"] for r in known_skill_rows if r.get("name")]

    upserted = 0
    linked_skills = 0
    for post in posts:
        post_key = f"{post['source']}::{post['external_id']}"

        run_query(
            """
            MERGE (p:MarketJobPost {post_key: $post_key})
            SET p.external_id = $external_id,
                p.source = $source,
                p.title = $title,
                p.company = $company,
                p.url = $url,
                p.published_at = $published_at,
                p.last_seen = $last_seen,
                p.last_seen_epoch = $last_seen_epoch
            """,
            {
                "post_key": post_key,
                "external_id": post["external_id"],
                "source": post["source"],
                "title": post["title"],
                "company": post["company"],
                "url": post["url"],
                "published_at": post["published_at"],
                "last_seen": ts,
                "last_seen_epoch": epoch_now
            }
        )

        run_query(
            """
            MATCH (p:MarketJobPost {post_key: $post_key})-[r:MARKET_REQUIRES]->(:Skill)
            DELETE r
            """,
            {"post_key": post_key}
        )

        extracted = _extract_skills_from_text(post.get("text_blob", ""), known_skills)
        for skill_name in extracted:
            run_query(
                """
                MERGE (s:Skill {name: $skill_name})
                ON CREATE SET s.category = "Market Imported", s.level = "Intermediate"
                WITH s
                MATCH (p:MarketJobPost {post_key: $post_key})
                MERGE (p)-[:MARKET_REQUIRES]->(s)
                """,
                {"skill_name": skill_name, "post_key": post_key}
            )
            linked_skills += 1

        upserted += 1

    stale_result = run_query(
        """
        MATCH (p:MarketJobPost)
        WHERE coalesce(p.last_seen_epoch, 0) < $cutoff
        WITH collect(p) AS stale_nodes
        WITH stale_nodes, size(stale_nodes) AS removed_count
        FOREACH (n IN stale_nodes | DETACH DELETE n)
        RETURN removed_count
        """,
        {"cutoff": stale_cutoff}
    )
    stale_removed = stale_result[0]["removed_count"] if stale_result else 0

    return {
        "status": "market_synced",
        "posts_synced": upserted,
        "skills_linked": linked_skills,
        "sources_used": source_success,
        "source_errors": source_errors,
        "stale_removed": stale_removed,
        "synced_at": ts
    }


@app.get("/market/intelligence")
def market_intelligence():
    summary = run_query(
        """
        MATCH (p:MarketJobPost)
        RETURN count(p) AS total_posts,
               count(DISTINCT p.source) AS source_count,
               max(p.last_seen) AS last_synced_at
        """
    )
    src_breakdown = run_query(
        """
        MATCH (p:MarketJobPost)
        RETURN p.source AS source, count(*) AS posts
        ORDER BY posts DESC
        """
    )

    total_posts = summary[0]["total_posts"] if summary else 0
    trends_query = """
    MATCH (p:MarketJobPost)-[:MARKET_REQUIRES]->(s:Skill)
    OPTIONAL MATCH (c:Course)-[:TEACHES]->(s)
    RETURN s.name AS skill,
           count(DISTINCT p) AS demand_count,
           count(DISTINCT p.source) AS source_count,
           count(DISTINCT c) AS course_count
    ORDER BY demand_count DESC, skill ASC
    LIMIT 12
    """
    trend_rows = run_query(trends_query)

    trends = []
    for row in trend_rows:
        demand = row["demand_count"] or 0
        courses = row["course_count"] or 0
        source_count = row["source_count"] or 0
        scarcity = round(demand / (courses + 1), 2)
        confidence = round(min(1.0, (demand / max(1, total_posts)) * (0.65 + 0.15 * source_count)), 2)
        trends.append({
            "skill": row["skill"],
            "demand_count": demand,
            "source_count": source_count,
            "course_count": courses,
            "scarcity_index": scarcity,
            "confidence": confidence
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_posts": total_posts,
        "source_count": summary[0]["source_count"] if summary else 0,
        "last_synced_at": summary[0]["last_synced_at"] if summary else None,
        "source_breakdown": src_breakdown,
        "top_trending_skills": trends
    }


@app.get("/market/intelligence/{user_id}")
def market_intelligence_for_user(user_id: str):
    user_exists = run_query(
        "MATCH (u:User {user_id: $user_id}) RETURN u.user_id AS user_id",
        {"user_id": user_id}
    )
    if not user_exists:
        raise HTTPException(status_code=404, detail="User not found")

    query = """
    MATCH (p:MarketJobPost)-[:MARKET_REQUIRES]->(s:Skill)
    WITH s, count(DISTINCT p) AS demand_count
    MATCH (u:User {user_id: $user_id})
    OPTIONAL MATCH (u)-[:HAS_SKILL]->(us:Skill {name: s.name})
    RETURN s.name AS skill,
           demand_count,
           CASE WHEN us IS NULL THEN true ELSE false END AS is_gap
    ORDER BY demand_count DESC, skill ASC
    LIMIT 15
    """
    rows = run_query(query, {"user_id": user_id})

    priority_gaps = []
    owned = 0
    total_demand = 0
    matched_demand = 0

    for row in rows:
        total_demand += row["demand_count"] or 0
        if row["is_gap"]:
            priority_gaps.append({
                "skill": row["skill"],
                "demand_count": row["demand_count"]
            })
        else:
            owned += 1
            matched_demand += row["demand_count"] or 0

    market_fit = round((matched_demand / total_demand) * 100, 2) if total_demand > 0 else 0

    return {
        "user_id": user_id,
        "market_fit_percent": market_fit,
        "owned_trending_skills": owned,
        "priority_gap_skills": priority_gaps[:8],
        "analysis_scope": len(rows),
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
