"""
State Reconstruction Module
Extracts structured state from full conversation history.
This is stateless by design — called on every request.
"""
import re
from typing import Any, Dict, List, Optional


# ─── Seniority Keywords ──────────────────────────────────────────────────────
SENIORITY_PATTERNS = {
    # Order matters: check more specific/senior first
    "executive": [
        "executive", "c-level", "c-suite", "cxo", "ceo", "cto", "cfo", "coo",
        "chief", "president", "senior leadership", "15+ years", "15 years",
        "20+ years",
    ],
    "director": [
        "director", "vp", "vice president", "senior director", "head of"
    ],
    "manager": [
        "manager", "team lead", "team leader", "lead", "supervisor",
        "first-line", "first line", "frontline manager"
    ],
    "graduate": [
        "graduate", "grad", "recent grad", "recent graduate", "campus hire",
        "management trainee", "graduate trainee", "final year", "final-year"
    ],
    "entry": [
        "entry-level", "entry level", "junior", "fresh", "fresher",
        "new grad", "new graduate", "intern", "trainee", "apprentice",
        "0-2 years", "0-1 year", "less than 2 years"
    ],
    "professional": [
        "mid", "mid-level", "mid level", "professional", "engineer",
        "3-7 years", "3+ years", "5+ years", "senior ic", "senior individual",
        "individual contributor", "ic", "specialist"
    ],
}

# ─── Role Keywords ────────────────────────────────────────────────────────────
ROLE_PATTERNS = {
    "software_engineer": [
        "software engineer", "software developer", "developer", "programmer",
        "swe", "engineer", "full stack", "full-stack", "backend", "frontend",
        "front end", "back end"
    ],
    "java_developer": ["java", "spring", "jvm", "j2ee"],
    "python_developer": ["python", "django", "flask", "fastapi"],
    "javascript_developer": [
        "javascript", "js", "node", "nodejs", "react", "angular", "vue"
    ],
    "devops_engineer": [
        "devops", "sre", "platform engineer", "infrastructure", "cloud engineer",
        "ci/cd", "docker", "kubernetes", "k8s", "aws", "azure", "gcp"
    ],
    "data_engineer": [
        "data engineer", "data pipeline", "etl", "bigquery", "spark",
        "data platform"
    ],
    "data_scientist": [
        "data scientist", "ml engineer", "machine learning", "ai engineer",
        "data science"
    ],
    "sales": [
        "sales", "account executive", "ae", "bdr", "sdr", "business development",
        "account manager", "sales rep", "sales representative"
    ],
    "customer_service": [
        "customer service", "customer support", "contact centre", "contact center",
        "call centre", "call center", "agent", "customer care", "inbound"
    ],
    "manager": ["manager", "people manager", "team manager"],
    "leadership": [
        "leader", "director", "vp", "chief", "cxo", "executive", "ceo",
        "cto", "cfo"
    ],
    "finance": [
        "finance", "financial analyst", "accountant", "accounting", "cpa",
        "bookkeeper", "controller"
    ],
    "hr": ["hr", "human resources", "recruiter", "talent acquisition", "hrbp"],
    "admin": ["admin", "administrative", "admin assistant", "secretary", "office"],
    "retail": ["retail", "store", "cashier", "sales associate"],
    "healthcare": [
        "healthcare", "medical", "nurse", "clinical", "health admin",
        "patient care"
    ],
    "manufacturing": [
        "manufacturing", "plant", "operator", "factory", "industrial",
        "production", "line worker"
    ],
    "marketing": ["marketing", "digital marketing", "content", "brand", "seo"],
    "legal": ["legal", "lawyer", "attorney", "paralegal"],
}

# ─── Test Type Keywords ───────────────────────────────────────────────────────
TEST_TYPE_PATTERNS = {
    "personality": [
        "personality", "behaviour", "behavioral", "opq", "character",
        "traits", "soft skills"
    ],
    "cognitive": [
        "cognitive", "aptitude", "reasoning", "ability", "iq", "intelligence",
        "numerical", "verbal", "inductive", "deductive", "g+", "verify",
        "general cognitive"
    ],
    "knowledge": [
        "knowledge", "technical", "domain", "skill", "know", "test",
        "coding", "programming"
    ],
    "simulation": [
        "simulation", "sim", "live coding", "exercise", "practice", "role play"
    ],
    "situational_judgment": [
        "situational", "sjt", "scenario", "judgment", "judgment test"
    ],
}

# ─── Constraint Keywords ──────────────────────────────────────────────────────
LANGUAGE_PATTERNS = {
    "english_us": ["english us", "american english", "us english", "english (us)", "usa"],
    "english_uk": ["english uk", "british english", "uk english"],
    "english_international": ["english international", "english"],
    "spanish": ["spanish", "espanol", "latin american spanish"],
    "french": ["french", "francais"],
    "german": ["german", "deutsch"],
    "portuguese": ["portuguese", "pt", "brazil"],
    "chinese": ["chinese", "mandarin", "simplified", "traditional"],
    "arabic": ["arabic"],
    "japanese": ["japanese"],
    "korean": ["korean"],
}


def extract_state(messages: List[Dict]) -> Dict:
    """
    Extract structured hiring state from conversation history.
    Returns a comprehensive state object.
    """
    state = {
        "role": None,
        "role_categories": [],
        "raw_role_title": None,   # Literal role name as typed by the user
        "seniority": None,
        "experience_years": None,
        "technical_skills": [],
        "soft_skills": [],
        "personality_focus": False,
        "cognitive_focus": False,
        "simulation_focus": False,
        "sjt_focus": False,
        "language_requirements": [],
        "volume": None,  # "high" or "low"
        "use_case": None,  # "selection" | "development" | "audit"
        "industry": None,
        "safety_critical": False,
        "bilingual": False,
        "excluded_assessments": [],
        "confirmed_assessments": [],
        "previous_recommendations": [],
        "comparison_request": None,
        "turn_count": 0,
        "raw_context": [],
    }

    user_text_all = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if not content:
            continue

        content_lower = content.lower()

        if role == "user":
            state["turn_count"] += 1
            user_text_all.append(content_lower)
            state["raw_context"].append({"role": "user", "text": content})

            # Extract experience years
            exp_match = re.search(r"(\d+)\+?\s*(year|yr|month|mo)s?", content_lower)
            if exp_match:
                num = int(exp_match.group(1))
                unit = exp_match.group(2)
                if unit.startswith("m"):
                    state["experience_years"] = num / 12.0
                else:
                    state["experience_years"] = float(num)
            else:
                stripped = content_lower.strip()
                if stripped.isdigit():
                    val = float(stripped)
                    if val < 40:
                        state["experience_years"] = val

            # Extract seniority
            for seniority, keywords in SENIORITY_PATTERNS.items():
                if any(kw in content_lower for kw in keywords):
                    if state["seniority"] is None:
                        state["seniority"] = seniority

            # Extract role categories
            for role_cat, keywords in ROLE_PATTERNS.items():
                if any(kw in content_lower for kw in keywords):
                    if role_cat not in state["role_categories"]:
                        state["role_categories"].append(role_cat)

            # Extract raw role title for any role not matched by patterns
            if not state["raw_role_title"]:
                _raw_role_patterns = [
                    r"(?:hiring|hire)\s+(?:for\s+)?(?:a\s+|an\s+)?([A-Za-z][A-Za-z\s\-\/]+?)(?:\s+role|\s+position|\s+with|\s+who|\s+that|[.,!?]|$)",
                    r"(?:need\s+a|need\s+an|looking\s+for\s+a|looking\s+for\s+an)\s+([A-Za-z][A-Za-z\s\-\/]+?)(?:\s+role|\s+position|\s+with|\s+who|\s+that|[.,!?]|$)",
                    r"(?:for\s+a|for\s+an)\s+([A-Za-z][A-Za-z\s\-\/]+?)(?:\s+role|\s+position|\s+with|\s+who|\s+that|[.,!?]|$)",
                    r"(?:role|position)[:\s]+([A-Za-z][A-Za-z\s\-\/]+?)(?:\s+with|\s+who|\s+that|[.,!?]|$)",
                    r"^(?:i(?:'m| am)|we(?:'re| are))\s+(?:hiring|looking)\s+(?:for\s+)?(?:a\s+)?([A-Za-z][A-Za-z\s\-\/]+?)(?:\s+role|\s+position|\s+with|\s+who|[.?!]|$)",
                ]
                for _pat in _raw_role_patterns:
                    _m = re.search(_pat, content, re.IGNORECASE)
                    if _m:
                        _candidate = _m.group(1).strip()
                        _words = _candidate.split()
                        if 1 <= len(_words) <= 5 and len(_candidate) >= 3:
                            state["raw_role_title"] = _candidate.title()
                            break

            # Extract test type focus
            for tt, keywords in TEST_TYPE_PATTERNS.items():
                if any(kw in content_lower for kw in keywords):
                    if tt == "personality":
                        state["personality_focus"] = True
                    elif tt == "cognitive":
                        state["cognitive_focus"] = True
                    elif tt == "simulation":
                        state["simulation_focus"] = True
                    elif tt == "situational_judgment":
                        state["sjt_focus"] = True

            # Volume detection — find large numbers in context of hiring/screening
            volume_match = re.search(r"(\d+)\s*(?:[-\w]*\s*){0,5}(?:candidates|people|applicants|hires|agents|staff|workers|employees)", content_lower)
            if volume_match:
                vol_num = int(volume_match.group(1))
                state["volume"] = "high" if vol_num >= 50 else "low"

            # Safety critical
            if any(kw in content_lower for kw in [
                "safety", "safe", "hazard", "risk", "compliance", "procedure",
                "chemical", "plant operator", "industrial", "manufacturing"
            ]):
                state["safety_critical"] = True

            # Language
            for lang, patterns in LANGUAGE_PATTERNS.items():
                if any(p in content_lower for p in patterns):
                    if lang not in state["language_requirements"]:
                        state["language_requirements"].append(lang)

            # Bilingual
            if "bilingual" in content_lower or "two languages" in content_lower:
                state["bilingual"] = True

            # Use case
            if any(kw in content_lower for kw in [
                "select", "hire", "hiring", "recruit", "screen", "assess", "shortlist"
            ]):
                state["use_case"] = "selection"
            elif any(kw in content_lower for kw in [
                "develop", "development", "train", "coaching", "feedback", "grow"
            ]):
                state["use_case"] = "development"
            elif any(kw in content_lower for kw in [
                "audit", "reskill", "upskill", "transformation", "survey"
            ]):
                state["use_case"] = "audit"

            # Industry
            for industry_kw in [
                ("healthcare", ["health", "medical", "hospital", "clinical", "hipaa"]),
                ("finance", ["bank", "financial services", "fintech", "investment"]),
                ("manufacturing", ["manufactur", "factory", "plant", "industrial", "chemical"]),
                ("retail", ["retail", "store", "ecommerce"]),
                ("technology", ["tech", "software", "saas", "startup"]),
                ("contact_centre", ["contact centre", "contact center", "call centre", "call center", "bpo"]),
            ]:
                ind_name, ind_keywords = industry_kw
                if any(kw in content_lower for kw in ind_keywords):
                    state["industry"] = ind_name

            # Technical skills extraction
            if "only " in content_lower:
                state["technical_skills"] = []
            tech_skills = _extract_tech_skills(content_lower)
            for skill in tech_skills:
                if skill not in state["technical_skills"]:
                    state["technical_skills"].append(skill)

            # Exclusions (drop/remove/skip)
            exclusion_patterns = [
                r"(?:drop|remove|skip|exclude|no|don't|without)\s+(?:the\s+)?([a-z0-9\+\s]+?)(?:\s+test|\s+assessment)?(?:\s*$|[,.])",
            ]
            for pat in exclusion_patterns:
                matches = re.findall(pat, content_lower)
                for m in matches:
                    m = m.strip()
                    if len(m) > 3:
                        state["excluded_assessments"].append(m)

            # Confirmations
            confirm_keywords = ["confirmed", "perfect", "great", "good", "keep", "yes", "correct", "that's what"]
            if any(kw in content_lower for kw in confirm_keywords):
                pass  # Confirmed state tracked via previous agent outputs

            # Comparison detection
            comparison_patterns = [
                r"(?:what(?:'s| is) the )?difference between (.+?) and (.+?)(?:\?|$)",
                r"compare (.+?) (?:and|with|vs\.?) (.+?)(?:\?|$)",
            ]
            for pat in comparison_patterns:
                m = re.search(pat, content_lower)
                if m:
                    state["comparison_request"] = {
                        "item_a": m.group(1).strip(),
                        "item_b": m.group(2).strip(),
                    }

        elif role == "assistant":
            state["raw_context"].append({"role": "assistant", "text": content})

    # Infer seniority from experience years if not set
    if state["experience_years"] is not None and state["seniority"] is None:
        yrs = state["experience_years"]
        if yrs >= 15:
            state["seniority"] = "executive"
        elif yrs >= 8:
            state["seniority"] = "director"
        elif yrs >= 5:
            state["seniority"] = "professional"
        elif yrs >= 2:
            state["seniority"] = "professional"
        else:
            state["seniority"] = "entry"

    # Set primary role
    if state["role_categories"]:
        state["role"] = state["role_categories"][0]

    return state


def _extract_tech_skills(text: str) -> List[str]:
    """Extract technical skill mentions from text."""
    tech_keywords = [
        "java", "python", "javascript", "typescript", "react", "angular", "vue",
        "node", "nodejs", "spring", "django", "flask", "fastapi", "rails",
        "ruby", "php", "go", "golang", "rust", "c++", "c#", "dotnet", ".net",
        "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
        "aws", "azure", "gcp", "docker", "kubernetes", "k8s",
        "terraform", "ansible", "jenkins", "ci/cd", "git",
        "linux", "bash", "shell", "networking", "tcp/ip",
        "machine learning", "ml", "ai", "tensorflow", "pytorch",
        "excel", "word", "powerpoint", "office", "salesforce",
        "sap", "tableau", "power bi",
    ]
    found = []
    for kw in tech_keywords:
        if kw in text:
            found.append(kw)
    return found


def needs_clarification(state: Dict, turn_count: int) -> bool:
    """
    Decide whether to ask clarification or recommend.
    Conservative: ask only if critical info is missing and we have turns left.
    """
    if turn_count >= 8:  # Conserve turns - recommend
        return False

    # If we have enough info to recommend, skip clarification
    has_role = bool(state["role_categories"] or state["technical_skills"] or state.get("raw_role_title"))
    has_seniority = state["seniority"] is not None or state["experience_years"] is not None
    has_context = len(state["raw_context"]) > 0

    technical_roles = ["software_engineer", "data_scientist", "data_engineer", "devops_engineer"]
    needs_tech_skills = any(r in technical_roles for r in state.get("role_categories", [])) and not state.get("technical_skills")

    if not has_role and has_context and turn_count <= 4:
        return True
    if not has_seniority and has_role and turn_count <= 4:
        return True
    if needs_tech_skills and turn_count <= 4:
        return True

    return False


def build_clarification_question(state: Dict, turn_count: int) -> str:
    """
    Build a high-information-gain clarification question.
    Ask multiple things in one go to conserve turns.
    """
    missing = []

    technical_roles = ["software_engineer", "data_scientist", "data_engineer", "devops_engineer"]

    if not state.get("role_categories") and not state.get("technical_skills"):
        missing.append("the role title and key responsibilities")
    elif any(r in technical_roles for r in state.get("role_categories", [])) and not state.get("technical_skills"):
        missing.append("the specific technical skills or programming languages required")

    if not state.get("seniority") and not state.get("experience_years"):
        missing.append("seniority level or years of experience")

    if not state.get("use_case"):
        missing.append("whether this is for selection, development, or a talent audit")

    if not state.get("personality_focus") and not state.get("cognitive_focus"):
        missing.append("whether personality or cognitive assessments are important")

    if not missing:
        return ""

    # Formatted as a numbered list
    question = "To recommend the best tests, could you tell me:\n"
    for i, part in enumerate(missing, 1):
        # Capitalize the first letter of each part
        capitalized_part = part[0].upper() + part[1:]
        question += f"{i}. {capitalized_part}\n"
    
    return question.strip()
