"""
Multi-axis template for SPAR research program evaluation.

This template evaluates candidates for the SPAR research program across various
dimensions relevant to AI safety research and policy.
"""

from ..base import MultiAxisTemplate, AxisTemplate

# General Promise axis
GENERAL_PROMISE_AXIS = AxisTemplate(
    name="General Promise",
    description="Overall fit and potential for success in the SPAR research program",
    ranking_keyword="GENERAL_PROMISE_RATING",
    prompt_section="""## General Promise
This criterion measures the candidate’s overall fit and potential for success in the SPAR research program, an AI safety and policy research program, based on their relevant technical or policy background, motivation, and concrete track record. Prioritize demonstrated achievements over abstract statements or general knowledge. Note that “AI safety” refers to the mitigation of risks, particularly large-scale or catastrophic, from advanced AI.

What to Look For:

* General academic and technical background
  * Advanced, relevant degrees (e.g., ML/CS PhD, technical MSc, or policy-related MA/PhD)
  * Strong mathematical, research, or programming skills.
  * Strong policy research skills, or strong skills from adjacent fields (public policy, law, international relations, economics, etc.)
* Experience specific to AI safety
  * Participation in major research programs (e.g., MATS, ARENA, MLAB, GovAI, IAPS Fellowship)
  * Participation in introductory research programs (e.g., SPAR, AI Safety Camp, or ERA)
  * Participation in introductory courses (e.g., AI Safety Fundamentals or CAIS’s AI Safety, Ethics, and Society)
  * Short self-guided introductions to AI safety (e.g, Future of AI by BlueDot or the Stampy project) or consumption of AI safety videos, articles, or newsletters (e.g., AI 2027 report, the CAIS newsletter, or a Rob Miles video)
  * Independent research or significant project output.
* Research/Publication Record:
  * Quantity, quality, and notability of research outputs (papers, blogs, open-source projects).
* Professional Experience:
  * Substantial work at relevant organizations (industry, academia, policy/governance).
* Red Flags:
  * Generic, vague, or obviously AI-generated answers.
  * “Troll” applications (irrelevant, unserious, or copy-paste responses).

Red Flags:
- Generic, vague, or obviously AI-generated answers.
- "Troll" applications (irrelevant, unserious, or copy-paste responses).


**Scoring Guide (1-5):**

* **1 — No meaningful engagement.** Generic responses, major technical errors, or irrelevant background.
* **2 — Basic foundation** (e.g., completed an intro course or self-study, but no real application or outputs).
* **3 — Demonstrated engagement:** completed technical courses, produced concrete outputs (blog posts, small projects, or detailed analysis), and shows technical/mathematical strength.
* **4 — Established track record:** completed substantial research projects, published analyses or code, implemented algorithms, or contributed to major policy research projects.
* **5 — Significant expertise:** led or authored notable published research, demonstrated technical or policy depth, contributed to high-impact projects or teams.

Focus on specific evidence of achievement or fit for the program, not generic enthusiasm or "what should be done" claims.
Ignore statements about the world unless clearly tied to the applicant's own work.
Before giving your score, explain your reasoning step by step.

Provide your analysis and then state '{ranking_keyword} = ' followed by an integer from 1-5."""
)

# ML Skills axis
ML_SKILLS_AXIS = AxisTemplate(
    name="ML Skills",
    description="Practical and theoretical machine learning expertise",
    ranking_keyword="ML_SKILLS_RATING",
    prompt_section="""## ML Skills
This criterion evaluates the candidate’s practical and theoretical machine learning expertise, including implementation, mathematical understanding, and applied work. Consider both classic and deep learning, coding skills, and breadth/depth of experience.

**What to look for:**

* Hands-on experience designing and training ML models, especially transformers or other foundation models (e.g., coding and training an LLM, doing mechanistic interpretability on a vision model or replicating an ML safety paper)

* Completed courses or degrees in ML, AI, statistics, or related fields

* Contributions to ML research projects (including ML Safety or interpretability projects), competition prizes (Kaggle, DrivenData, etc.), or significant contributions to ML open-source repositories

* Published research or technical reports in ML (either as a pre-print or in a journal)

* Demonstrated strong understanding of ML and Deep Learning concepts

**Scoring Guide (1–5):**

* **1 — Minimal ML Experience:**
    No relevant coursework, projects, or practical work in ML.

* **2 — Basic ML Foundation:**
    Has completed an intro ML or AI class (online or university), but little or no hands-on application.

* **3 — Demonstrated Application:**
    Has built, trained, and evaluated basic or toy ML models (e.g., coded and trained basic transformer)—has some real-world or coursework projects.

* **4 — Advanced Practical Experience:**
    Has contributed to several substantial ML research projects, published ML pre-prints or papers, or won ML competitions (Kaggle, etc.)

* **5 — ML Expertise:**
    Has published at a top ML conference/journal (e.g. ICML or NeurIPS), substantially contributed to major open-source ML libraries (e.g. pytorch or nnsight) ; or has significant, innovative ML engineering experience at a top-tier company or research lab (e.g. Google DeepMind or Nvidia).


Focus on specific ML achievements and concrete experience.
Before giving your score, explain your reasoning step by step.

Provide your analysis and then state '{ranking_keyword} = ' followed by an integer from 1-5."""
)

# Software Engineer Skills axis
SOFTWARE_ENGINEERING_AXIS = AxisTemplate(
    name="Software Engineering Skills",
    description="Software engineering ability, especially in Python and ML frameworks",
    ranking_keyword="SOFTWARE_ENGINEERING_RATING",
    prompt_section="""## Software Engineering Skills
This axis measures the candidate’s software engineering ability, with a bonus for experience relevant to ML-focused contexts (e.g., Python, PyTorch, TensorFlow, JAX, etc). Consider both quality and depth of professional experience. You should be willing to trade off less experience specific to ML engineering if a candidate has excellent general SWE experience.

**What to look for:**

* Strong Python skills; ability to build, debug, and maintain complex codebases

* Experience with relevant ML frameworks (PyTorch, TensorFlow, JAX, etc.)

* Evidence of writing production-quality software (not just notebooks or scripts)

* Real-world software engineering experience at a company or research lab (preferably as a full employee, not only internships)

* Experience or awareness of good software practices (testing, version control, code review, CI/CD, etc)

**Scoring Guide (1–5):**

* **1 — Minimal Software Experience:**
    Little or no experience coding beyond basic scripts.

* **2 — Basic Python Scripting:**
    Can write small Python scripts or notebooks, but has limited exposure to real software engineering practices. They may have taken an intro to programming class or course.

* **3 — Practical Coding Experience:**
    Has built small to medium-sized Python projects, contributed to minor open-source projects, or obtained internship-level software engineering experience. If their experience is relevant to ML, a person at this level might have replicated a few ML papers or passed several college classes about ML or ML engineering.

* **4 — Professional Engineering Experience:**
    Has worked as a full-time software engineer in a company or research group (not just as an intern), or contributed to large, production codebases. If their experience is ML specific, this person has substantial experience with ML engineering, for example, having worked as an ML engineer professionally or made important contributions to several published ML projects.

* **5 — Expert Software or ML Engineer:**
    Demonstrated leadership in software engineering (e.g., major open-source maintainer, tech lead, or senior engineer at a top-tier company, like FAANG or a frontier lab). Alternatively, shows deep expertise with relevant ML tooling, having e.g. contributed to top open source ML libraries, contributed as an engineer to research projects published at a top ML journal, or worked as a professional ML engineer at a top-tier company.

Focus on professional engineering experience, codebase scale, and toolset expertise (especially Python/ML).
Before giving your score, explain your reasoning step by step.

Provide your analysis and then state '{ranking_keyword} = ' followed by an integer from 1-5."""
)

# Policy Experience axis
POLICY_EXPERIENCE_AXIS = AxisTemplate(
    name="Policy Experience",
    description="Experience in policy research related to technology, governance, or AI",
    ranking_keyword="POLICY_EXPERIENCE_RATING",
    prompt_section="""## Policy Experience
This criterion evaluates the candidate’s experience in policy research—especially if the experience might prove relevant to AI policy, whether domestic or international. The focus is on work involving the systematic study, analysis, or development of public policy, regulatory frameworks, or governmental decision-making. **Note:** We do *not* count routine company policy writing (e.g., privacy policies), nor do we focus on traditional political advocacy or campaign work, except where it includes substantial research or policy analysis.

**What to look for:**

* Direct involvement in policy research (e.g., government white papers, think tank analysis, academic studies on public policy)

* Experience in designing, evaluating, or analyzing laws, regulations, or public sector strategies

* Participation in government policy advisory groups, committees, or public consultation projects

* Contributions to policy-focused publications, reports, or peer-reviewed articles

* Relevant advanced study in public policy, law, international relations, or adjacent fields (especially with research output)

**Scoring Guide (1–5):**

* **1 — No Policy Research Experience:**
    No relevant policy research work, analysis, or studies. May have only routine corporate/governance experience.

* **2 — Limited Exposure:**
    Some engagement with policy research topics, or is pursuing a relevant undergraduate degree, but without real research output or practical involvement.

* **3 — Early Research Involvement:**
    Has participated as a junior analyst, intern, or contributor on policy research projects (e.g., think tanks, academic projects), or produced substantial extracurricular policy analysis (e.g., whitepapers, policy blogs).

* **4 — Experienced Policy Researcher:**
    Has authored/co-authored policy research reports, academic publications, or led significant research in a think tank, university, or governmental setting.

* **5 — Leading Policy Researcher:**
    Extensive track record of major policy research impact—e.g., lead author on key government reports, high-profile think tank studies, or has shaped national/international policy through rigorous research and analysis.


Focus on concrete policy research outputs, depth of analysis, and real-world impact—not general advocacy or campaign participation.
Before giving your score, explain your reasoning step by step.

Provide your analysis and then state '{ranking_keyword} = ' followed by an integer from 1-5."""
)

# AI Safety Understanding axis
AI_SAFETY_UNDERSTANDING_AXIS = AxisTemplate(
    name="Understanding of AI Safety",
    description="Depth of understanding of technical AI safety concepts and research",
    ranking_keyword="AI_SAFETY_UNDERSTANDING_RATING",
    prompt_section="""## Understanding of AI Safety
This criterion evaluates the candidate’s depth of understanding of technical AI safety—specifically, issues related to AI alignment, interpretability, and existential risks from advanced AI systems. Only technical AI safety knowledge should be counted here; general AI ethics, fairness, privacy, or regulatory work does *not* qualify unless it is strictly related to existential risks from AI.

**What to look for:**

* Knowledge of core concepts in technical AI safety (e.g., alignment, value learning, robustness, interpretability, existential risk)

* Ability to discuss current technical research agendas, methodologies, and risks

* Participation in technical AI safety projects, open-source contributions, or research

* Authorship or significant contributions to AI safety papers, blog posts, or reports

* *Exclude* work that is solely about AI ethics, fairness, privacy, or governance unless it is clearly and directly relevant to addressing risks from advanced AI.

**Scoring Guide (1–5):**

* **1 — No core understanding of AI safety:**
    No evidence of understanding technical AI safety; may mention general ML or vague ethics/morals/discrimination topics.

* **2 — Casual Awareness:**
    Has consumed basic content (e.g., watched videos by Rob Miles, read AI 2027 or has kept up with relevant newsletters) but would not typically be able to articulate specific technical concepts or agendas. Might have taken a very short introductory course to AI safety, like the Future of AI course by BlueDot Impact (which is 2 hours).

* **3 — Engaged Understanding:**
    Can explain particular technical research agendas or approaches they find important, with clear reasoning; demonstrates meaningful engagement with technical safety topics. Might have taken a relatively long introductory course to AI safety, like AI Safety Fundamentals (which is 8 weeks).

* **4 — Practical Involvement:**
    Has worked on a project in technical AI safety, published minor articles or posts coherently discussing AI safety, or made minor contributions to research efforts directly related to AI alignment, policy or safety. May have participated in a program like SPAR, MARS, or AI Safety Camp in the past.

* **5 — Expert Level:**
    Has authored technical papers or substantial blog posts on AI safety; would be capable of working on a technical safety team at a top lab (DeepMind, OpenAI, Anthropic, etc.) or a relevant AI safety org (e.g., METR, ARC, MIRI, Redwood Research, etc); can discuss and critique methods at a high level. May have participated in a selective research program like MATS or GovAI.

Focus on technical AI safety/AI alignment experience and understanding only; do not count general ethics, privacy, or governance work.
Before giving your score, explain your reasoning step by step.

Provide your analysis and then state '{ranking_keyword} = ' followed by an integer from 1-5."""
)

# Path to Impact axis
PATH_TO_IMPACT_AXIS = AxisTemplate(
    name="Path to Impact",
    description="Likelihood of making meaningful contributions to technical AI safety",
    ranking_keyword="PATH_TO_IMPACT_RATING",
    prompt_section="""## Path to Impact
This criterion assesses the likelihood that the candidate will make a significant, long-term contribution to AI safety, based on their stated plans, concrete actions, and demonstrated commitment. The focus is on technical AI safety, AI policy related to existential risks from AI, or direct support roles to AI safety efforts—not general AI ethics, governance, or ML work.

**What to look for:**

* Clear, explicit intentions to pursue a career in AI safety or AI policy relevant to existential risks from AI (or adjacent highly technical support roles)

* Concrete plans: mentions of specific programs, companies, or research groups they aim to join

* Evidence of taking active steps towards a career shift (e.g., self-study, job applications, networking)

* Already working in technical AI safety or a senior supporting role (e.g., managing a technical AI safety team, or doing large-scale grantmaking for AI safety)

* In general, indicators that suggest the person is likely to make a significant contribution to the field. For example, the person might be particularly agentic or accomplished, or might have studied at a top university.

* *Do not count* general ML, AI ethics/governance, or “safety consciousness” in generic ML roles, unless the person is clearly mission-aligned with reducing risks from advanced AI.

**Scoring Guide (1–5):**

* **1 — No Path Toward AI Safety:**
    Actively states no intention to work on AI safety or AI policy. Only interested as a side topic, or plans to remain in unrelated fields (e.g., generic data science/software engineering/ML roles).

* **2 — Vague or Indecisive Plan:**
    Considers AI safety as one option among many, or has a loosely defined career plan to “maybe” get into AI safety. No specific steps or commitments shown.

* **3 — Clear, Concrete Plan:**
    Has a well-defined plan to pursue AI safety or AI policy—names specific organizations, programs, or research groups they want to join. Seems to care about existential or catastrophic risks from AI in particular. Seems reasonably talented.

* **4 — Active Transition:**
    Has already taken substantial, tangible steps towards an AI safety career (e.g., participated in a research program like MATS, SPAR, ERA, GovAI, or AI Safety Camp, done safety-related internships, etc). Seems like quite promising talent.

* **5 — Already in Technical AI Safety, AI Policy, or Supporting Senior Role:**
    Currently works on technical AI safety at an impactful organization (either an AI safety org, like METR, MIRI, or Redwood Research, or a frontier lab), works on x-risk relevant AI policy at an important think tank or government institute (like the European Commission, the UK AISI, CNA,S or RAND), or has a senior role supporting fieldbuilding efforts at a mission-aligned organization (e.g,. BlueDot, MATS, GovAI, 80,000 hours).
    *Note:* Working on general ML/AI ethics/governance does **not** count.


Focus only on career trajectories or roles relevant to reducing catastrophic risks from advanced AI. Don’t weigh adjacent ML or AI ethics experience.
Before giving your score, explain your reasoning step by step.

Provide your analysis and then state '{ranking_keyword} = ' followed by an integer from 1-5."""
)

# Research Experience axis
RESEARCH_EXPERIENCE_AXIS = AxisTemplate(
    name="Research Experience",
    description="Experience with academic or applied research",
    ranking_keyword="RESEARCH_EXPERIENCE_RATING",
    prompt_section="""## Research Experience
This axis assesses the candidate’s general experience with academic or applied research. Count peer-reviewed papers, substantial technical blog posts, open-source research contributions, and independent investigations (e.g., at a university or through competitions).

**What to look for:**

* Authorship or co-authorship of research papers (academic conferences/journals)

* Technical blogging, whitepapers, or major open-source research contributions

* Independent or school/university research projects (with tangible outputs)

* Participation in research competitions (e.g., Kaggle, AI challenges)

* Evidence of investigative/analytical thinking and research taste

**Scoring Guide (1–5):**

* **1 — No Research Experience:**
    No evidence of research, academic writing, or technical investigation.

* **2 — Limited Research Exposure:**
    Participated in a school/university research project or contributed to an open-source research repo, but without significant outputs or authorship.

* **3 — Developed Research Experience:**
    Has written or co-authored technical blog posts, whitepapers, or non-peer-reviewed reports; may have significant contributions to group projects or smaller research publications.

* **4 — Substantial Research Track Record:**
    Authored or co-authored peer-reviewed research papers, contributed to major open-source research projects, or led substantial research efforts at school/university.

* **5 — High-Impact Researcher:**
    Lead author on multiple peer-reviewed papers at a top journal, or major recognized open-source research contributions; strong evidence of independent or innovative research ability.

Focus on the quality, quantity, and impact of research outputs.
Before giving your score, explain your reasoning step by step.

Provide your analysis and then state '{ranking_keyword} = ' followed by an integer from 1-5."""
)

# Define the complete multi-axis template
SPAR_MULTI_AXIS_TEMPLATE = MultiAxisTemplate(
    id="multi_axis_spar",
    name="SPAR Research Program Evaluation",
    description="Evaluation for candidates applying to the SPAR research program",
    system_intro="""Evaluate the application above, based on the following criteria: {criteria_string}

You will evaluate the applicant across multiple dimensions, providing a separate rating for each.
You should ignore general statements or facts about the world, and focus on what the applicant themselves has achieved.

IMPORTANT RATING CONSTRAINTS:
- Your rating for EACH AXIS MUST be an integer (whole number only)
- Your rating for EACH AXIS MUST be between 1 and 5 (inclusive)
- DO NOT use ratings above 5 or below 1
- If the rubric mentions different scale values, convert them to the 1-5 scale

First explain your reasoning thinking step by step. Then provide a separate rating for each axis:""",
    system_outro="""After evaluating all axes, provide an overall summary of the candidate's strengths and weaknesses.{additional_instructions}""",
    axes=[
        GENERAL_PROMISE_AXIS,
        ML_SKILLS_AXIS,
        SOFTWARE_ENGINEERING_AXIS,
        POLICY_EXPERIENCE_AXIS,
        AI_SAFETY_UNDERSTANDING_AXIS,
        PATH_TO_IMPACT_AXIS,
        RESEARCH_EXPERIENCE_AXIS
    ]
)
