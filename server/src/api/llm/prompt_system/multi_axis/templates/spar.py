"""
Multi-axis template for SPAR research program evaluation.

This template evaluates candidates for the SPAR research program across various
dimensions relevant to AI safety research and policy.
"""

from ..base import MultiAxisTemplate, AxisTemplate

GENERAL_PROMISE_AXIS = AxisTemplate(
    name="General Promise",
    description="Overall fit and potential for success in the SPAR research program",
    ranking_keyword="GENERAL_PROMISE_RATING",
    prompt_section="""## General Promise
This criterion measures the candidate's overall fit and potential for success in the SPAR research program, an AI safety and policy research program, based on their relevant technical or policy background, motivation, and concrete track record. Prioritize demonstrated achievements over abstract statements or general knowledge.

Note that "AI safety" refers to the mitigation of risks, particularly large-scale or catastrophic, from advanced AI (think AGI or ASI), including but not limited to, loss of control risks, catastrophic misuse risks, risks from digital minds, large-scale unemployment, and AI-assisted coups. SPAR offers a diverse set of projects across AI safety, security and policy, but they all have theories of change related to these risks.

What to Look For:

* General academic and technical background
  * Advanced, relevant degrees (e.g., ML/CS PhD, technical MSc, or policy-related MA/PhD)
  * Strong mathematical, research, or programming skills.
  * Strong policy research skills, or strong skills from adjacent fields (public policy, law, international relations, economics, etc.)
  * Cybersecurity skills, especially those relevant to AI security: Securing model weights at frontier labs, evaluating cyber offense-defense capabilities, or working on compute governance (for example, hardware-enabled guarantees.
  * Experience with areas relevant to large-scale misuse risks from AI (particularly CBRN and cyber).
  * Studies at a top university, especially in the top #100 worldwide.
* Experience specific to AI safety
  * Participation in highly selective research programs (e.g., MATS, GovAI, RAND TASP, Horizon, or the IAPS Fellowship)
  * Participation in introductory research programs (e.g., SPAR, AI Safety Camp, MARS, Pivotal Fellowship, Future Impact Group, or ERA)
  * Participation in ML upskilling programs (e.g. ARENA and MLAB)
  * Participation in introductory courses or fellowships (e.g., Bluedot's AI Safety Fundamentals, or CAIS's AI Safety, Ethics, and Society, both of which are ~8-14 weeks). Note that many groups around the world run reading groups based on BlueDot's AISF curriculum (formerly known as AGISF), these should be counted similarly.
  * Short self-guided introductions to AI safety (e.g, Future of AI by BlueDot, which is two hours) or consumption of AI safety videos, articles, or newsletters (e.g., the AI 2027 report, the CAIS newsletter, LessWrong posts, or a Rob Miles video)
  * Independent research or significant project output.
* Research/Publication Record:
  * Quantity, quality, and notability of research outputs (papers, blogs, open-source projects).
* Professional Experience:
  * Substantial work at relevant organizations (industry, academia, civil society, government).
* Red Flags:
  * Generic, vague, or obviously AI-generated answers.
  * "Troll" applications (irrelevant, unserious, or copy-paste responses).
  * Responses that suggest the candidate does not care or is dismissive about existential or catastrophic risks or large-scale societal impacts from advanced AI.

**Scoring Guide (1-5):**

* **1 — Poor Fit / Red Flags:**
  * Software engineer with one-sentence answers, no AI safety engagement, applying because "AI is the future"
  * Copy-pasted generic ChatGPT responses without personal details
  * Argues AI safety concerns are overblown, should focus only on current bias
  * Completely unrelated background (sales, hospitality) with no research connection
  * Joke/troll responses

* **2 — Minimal Relevant Background:**
  * CS undergrad, decent GPA, watched Rob Miles, only standard coursework on CV
  * Data analyst who took 2-hour Future of AI course, interested but no concrete steps
  * Recent grad following AI safety Twitter but no technical projects or research
  * ML engineer treating SPAR as generic ML opportunity
  * Policy student conflating AI governance with privacy/data protection

* **3 — Solid Foundation with Engagement:**
  * Strong CS undergrad from top-50 university, completed AISF
  * Physics PhD with strong math background, starting to learn about AI safety through ARENA
  * Software engineer (3 years experience), recently completed AISF, genuine interest in transition
  * Policy researcher at think tank, completed BlueDot governance course
  * ML master's student with good technical skills, participated in university AI safety reading group

* **4 — Strong Track Record:**
  * Strong CS undergrad from top-50 university, completed AISF, built interpretability project, active in reading group
  * Previous SPAR participant with resulting blog post on Alignment Forum
  * ML engineer at tech company, AI Safety Camp alumnus, working on safety side projects
  * Policy PhD on AI governance, published relevant papers, completed governance fellowship
  * Ex-quant (3 years), MARS graduate, actively transitioning to safety

* **5 — Exceptional Candidate:**
  * MATS graduate, NeurIPS paper on interpretability, Anthropic offers
  * GovAI Fellow, lead author on influential governance paper, UK AISI researcher
  * ML PhD from top-5, 3 ICML/NeurIPS papers, DeepMind safety internship
  * Former OpenAI safety researcher (2 years), led scalable oversight project
  * Senior policy advisor on AI chip controls, RAND TASP alumnus

**Notes:**
- Focus on specific evidence of achievement or fit for the program, not generic enthusiasm or "what should be done" claims.
- Ignore statements about the world unless clearly tied to the applicant's own work.
- Consider: Would a top AI safety researcher be excited to mentor this person?

Before giving your score, explain your reasoning step by step.
Provide your analysis and then state '{ranking_keyword} = ' followed by an integer from 1-5."""
)

# ML Skills axis
ML_SKILLS_AXIS = AxisTemplate(
    name="ML Skills",
    description="Practical and theoretical machine learning expertise",
    ranking_keyword="ML_SKILLS_RATING",
    prompt_section="""## ML Skills
This criterion evaluates the candidate's practical and theoretical machine learning expertise, including implementation, mathematical understanding, and applied work. Consider both classic and deep learning, coding skills, and breadth/depth of experience.

**What to look for:**
* Hands-on experience designing and training ML models, especially transformers or other foundation models
* Completed courses or degrees in ML, AI, statistics, or related fields
* Contributions to ML research projects, competition prizes, or ML open-source repositories
* Published research or technical reports in ML
* Demonstrated understanding of ML and Deep Learning concepts

**Scoring Guide (1–5):**

* **1 — Minimal ML Experience:**
    No relevant coursework, projects, or practical work in ML.

* **2 — Basic ML Foundation:**
    Completed intro ML/AI class (online or university), but little hands-on application.
    Can explain basic concepts (regression, classification) but no real projects.

* **3 — Demonstrated Application:**
    Built and trained models beyond sklearn tutorials (e.g., fine-tuned a pretrained model, implemented a paper)
    Has real coursework projects or personal experiments with neural networks
    Understands core DL concepts (backprop, architectures, training dynamics)

* **4 — Advanced Practical Experience:**
    Multiple substantial ML projects with evidence of iteration and debugging
    Published ML papers/pre-prints OR won ML competitions OR significant OS contributions to libraries relevant to ML (e.g. nnsight)
    Can implement papers from scratch, debug training issues, optimize performance
    Industry ML experience or research lab involvement

* **5 — ML Expertise:**
    Published at top venues (NeurIPS, ICML, ICLR) as key author
    Major contributions to widely-used ML libraries (PyTorch, HuggingFace, etc.)
    Senior ML role at top-tier company or a non-senior ML role at a frontier AI lab
    Demonstrated novel research contributions or breakthrough implementations

Focus on specific ML achievements and concrete experience.
Before giving your score, explain your reasoning step by step.

Provide your analysis and then state '{ranking_keyword} = ' followed by an integer from 1-5."""
)

# Software Engineering axis - SUGGESTED IMPROVEMENTS
SOFTWARE_ENGINEERING_AXIS = AxisTemplate(
    name="Software Engineering Skills",
    description="Software engineering ability, especially in Python and ML frameworks",
    ranking_keyword="SOFTWARE_ENGINEERING_RATING",
    prompt_section="""## Software Engineering Skills
This axis measures software engineering ability, with emphasis on Python and ML frameworks (PyTorch, TensorFlow, JAX). Strong general SWE experience can compensate for less ML-specific experience.

**What to look for:**
* Python proficiency - not just notebooks but proper software engineering
* Experience with ML frameworks and infrastructure
* Evidence of having worked on production-quality code (testing, documentation, maintainability)
* Real-world software engineering experience
* Good engineering practices (git, code review, debugging complex systems, CI/CD)

**Scoring Guide (1–5):**

* **1 — Minimal Software Experience:**
    Little or no coding beyond basic scripts or homework.

* **2 — Basic Python Scripting:**
    Can write Python scripts/notebooks for analysis
    Completed intro programming courses
    Limited experience with software engineering practices

* **3 — Practical Coding Experience:**
    Built Python projects beyond coursework (web apps, tools, data pipelines)
    Comfortable with git, debugging, package management
    Some experience with ML frameworks (even if just for learning)
    Internship-level experience OR significant open-source contributions

* **4 — Professional Engineering Experience:**
    Full-time SWE role (1+ years) OR extensive ML engineering experience
    Can architect systems, not just implement features
    Proficient with ML infrastructure (training pipelines, model serving)
    Writes maintainable, well-tested code

* **5 — Expert Software/ML Engineer:**
    Senior/Staff engineer at recognized company, or a non-senior software engineer at a FAANG or FAANG-equivalent companies of 3+ years
    Led significant technical projects or teams
    Deep expertise in Python/ML tooling ecosystem
    Major open-source maintainer or core contributor
    Can debug and optimize complex ML systems

**Note:** Strong SWE without ML experience can still score 4+ if engineering skills are excellent.

Focus on code quality and engineering maturity, not just years of experience.
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
This criterion evaluates the candidate's depth of understanding of technical AI safety—specifically, issues related to AI alignment, interpretability, and existential risks from advanced AI systems. Only technical AI safety knowledge should be counted here; general AI ethics, fairness, privacy, or regulatory work does NOT qualify unless strictly related to existential risks from AI.

**What You Can Actually Observe in SPAR Applications:**

* **From "How have you engaged with AI safety?":**
  * Specific programs, courses, or resources mentioned (and level of detail)
  * Whether they name specific research agendas, papers, or researchers
  * How they characterize their engagement (passive consumption vs. active participation)
  * Use of terminology - correct, incorrect, or generic

* **From "Career interests/study plans" and "How SPAR contributes":**
  * Whether they connect SPAR to specific AI safety problems or research areas
  * Specificity about which aspects of AI safety they want to work on
  * Whether they conflate AI safety with AI ethics/bias/fairness
  * Level of concreteness about safety-relevant goals

* **From CV/LinkedIn:**
  * AI safety-relevant projects, papers, or blog posts
  * Courses taken (distinguishing AI safety from general ML/AI ethics)
  * Research experience with safety-adjacent topics
  * Participation in safety programs or communities
  * Any published work where you can verify understanding quality

* **From "Relevant skills" section:**
  * Whether they highlight safety-specific techniques (interpretability, adversarial training, etc.)
  * How they frame their ML/policy skills relative to safety
  * Mention of implementing safety-relevant methods

**Red Flags Indicating Confusion:**
* Conflates AI safety with traditional AI ethics/bias/fairness
* Only discusses near-term ML safety issues (robustness, adversarial examples) without connection to AGI/TAI risks
* Repeats surface-level talking points without deeper comprehension
* Misuses technical terms or makes conceptual errors

**Scoring Guide (1-5):**

* **1 — No Evidence of AI Safety Understanding:**
  **Example profiles:**
  * ML engineer whose "AI safety engagement" discusses making models more accurate and less biased against minorities
  * Undergraduate who lists "AI Ethics" course focused on facial recognition bias and algorithmic fairness
  * Application mentions being concerned about "AI taking jobs" or "privacy violations" as main safety concerns
  * Career interests focus on "responsible AI deployment" but only discusses current model limitations, not advanced AI risks
  * Empty or irrelevant response to "How have you engaged with AI safety?" (e.g., "I haven't yet" or "I use ChatGPT safely")

* **2 — Minimal Exposure, Understanding Unclear:**
  **Example profiles:**
  * Says they've "watched Rob Miles videos and read about alignment on LessWrong" but provides no specifics
  * Completed 2-hour Future of AI course, mentions worries about "transformative AI" or "large-scale misuse"
  * Software developer who recently discovered AI safety, follows newsletters, but CV shows no related projects or deeper engagement
  * States "I'm concerned about AGI alignment" but career interests remain focused on general ML applications
  * Lists "The Alignment Problem" or "Superintelligence" in interests but no evidence of applying concepts

* **3 — Clear Engagement, Likely Foundational Understanding:**
  **Example profiles:**
  * Completed 8-week AISF course, participates in local AI safety reading group, CV shows end of AISF project on "Literature review on improvements to RLHF"
  * Undergrad which in their career interests, specifically mentions wanting to work on "mechanistic interpretability to understand model deception"
  * Policy student who writes about "verification regimes for frontier models" and completed governance-focused AISF track
  * Person that has been casually engaged with AI Safety through LessWrong for several years and now wants to pivot their career into it

* **4 — Strong Evidence of Technical Understanding:**
  **Example profiles:**
  * SPAR alumnus whose CV includes "Research on activation steering methods with [known safety researcher]"
  * Data scientist who completed ARENA, blog post on "Reproducing key results from the goal misgeneralization paper"
  * Engagement describes "contributing to the open-source library for SAE interpretability research"
  * ML engineer who completed AI Safety Camp, published technical blog post on "Implementing debate as an alignment strategy"
  * GitHub shows multiple repos implementing safety papers (e.g., "my implementation of influence functions for attribution")

* **5 — Advanced Engagement:**
  **Example profiles:**
  * MATS graduate with paper "Discovering Deceptive Behaviors in Language Models" on arXiv, cited by other researchers
  * Current role: "Research Engineer at Redwood Research working on adversarial training"
  * GovAI Fellow whose publications include "Compute Governance Mechanisms for Frontier AI" in policy journal
  * Career interests discuss "bridging the gap between prosaic alignment and agent foundations" with specific and coherent technical proposals
  * CV shows progression: AISF → MARS → research internship at Anthropic

**Key Indicators to Watch For:**

* **Terminology usage in limited text:**
  * Red flag: Confusing "AI safety" with "AI ethics/bias"
  * Yellow flag: Only surface-level use of terms without context
  * Green flag: Specific technical concepts used appropriately

* **Specificity in "How does SPAR contribute?":**
  * Weak: "To learn about AI safety"
  * Strong: "To investigate whether reward hacking persists in RLHF fine-tuned models" or "to obtain career capital to work on CBRN AI evaluations"

**Important Evaluation Notes:**
- You're inferring from limited information - be conservative when uncertain
- Weight verifiable CV items more than self-descriptions
- If someone has strong safety engagement but poor articulation, consider that the application format doesn't test understanding directly
- Distinguish between "took an ML course that mentioned safety" and "took a course specifically on AI safety"
- If they link to work (GitHub, blog, papers), that can provide much stronger signal

Focus on observable proxies: what they've done, what they've produced, and whether they make obvious errors in the limited text they provide.

Before giving your score, explain your reasoning step by step.

Provide your analysis and then state '{ranking_keyword} = ' followed by an integer from 1-5."""
)

# Path to Impact axis
PATH_TO_IMPACT_AXIS = AxisTemplate(
    name="Path to Impact",
    description="Likelihood of making meaningful contributions to technical AI safety",
    ranking_keyword="PATH_TO_IMPACT_RATING",
    prompt_section="""## Path to Impact
This criterion assesses the likelihood that the candidate will make a significant, long-term contribution to AI safety, based on their demonstrated commitment, concrete actions taken, and career trajectory. Focus on commitment to technical AI safety, AI security, or AI policy related to catastrophic risks—not general AI ethics or ML work.

**Scoring Guide (1-5):**

* **1 — No Path Toward AI Safety:**
  * Explicitly states no intention to work on AI safety professionally
  * ML engineer using SPAR for general career advancement
  * Plans to stay in unrelated field (generic SWE, data science)
  * Only interested as a side topic or hobby

* **2 — Exploratory Interest:**
  * "AI safety is one option I'm considering among others"
  * Curious about the field but no concrete steps taken
  * Career plan mentions "maybe transitioning eventually"
  * Treating SPAR as exploration without commitment
  * No specific orgs or roles identified

* **3 — Clear Commitment:**
  * "AI safety is my primary career focus going forward"
  * Names specific orgs/programs as next steps (MATS, Anthropic, Redwood)
  * 3+ months of self-study (courses, papers, projects)
  * Active in AI safety community/events
  * Has realistic timeline: "Applying to X after finishing Y"

* **4 — Active Transition:**
  * Already applied to AI safety orgs/programs
  * Previous SPAR/MARS/AI Safety Camp participant continuing the path
  * Left previous career to focus on safety transition
  * Graduate student with published AI safety research
  * Created substantial safety content (research, code, blogs)
  * 6+ months consistent engagement with concrete outputs

* **5 — Already Contributing:**
  * Currently in AI safety role (even junior/intern)
  * Working on x-risk policy at government/think tank
  * PhD with safety-focused advisor and clear post-grad plans
  * Completed MATS/GovAI with upcoming safety position
  * Senior role enabling safety work (grantmaking, program management)

**Quick Indicators:**
* Strong: Specific technical areas identified ("mechanistic interpretability at Anthropic")
* Weak: "Interested in beneficial AI"
* Weak: Only mentions general ML/AI ethics roles

**Note:** Focus on commitment and actions, not talent (covered in other axes). Career pivots take time—credit meaningful progress.

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
