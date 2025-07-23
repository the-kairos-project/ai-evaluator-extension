"""
Multi-axis template for academic evaluation.

This template evaluates candidates across multiple dimensions relevant to academic
and research contexts, with a focus on AI/ML capabilities.
"""

from ..base import MultiAxisTemplate, AxisTemplate

# General premise axis
GENERAL_PREMISE_AXIS = AxisTemplate(
    name="General Premise",
    description="Overall quality and fit of the application",
    ranking_keyword="GENERAL_PREMISE_RATING",
    prompt_section="""## General Premise
Evaluate the overall quality of the application and how well the candidate aligns with our goals.
Consider their motivation, alignment, and overall potential.
Provide your analysis and then state '{ranking_keyword} = ' followed by an integer from 1-5."""
)

# ML Skills axis
ML_SKILLS_AXIS = AxisTemplate(
    name="ML Skills",
    description="Technical machine learning skills and experience",
    ranking_keyword="ML_SKILLS_RATING",
    prompt_section="""## ML Skills
Assess the candidate's machine learning skills, technical background, and relevant experience.
Consider their projects, academic background, and demonstrated technical abilities.
Provide your analysis and then state '{ranking_keyword} = ' followed by an integer from 1-5."""
)

# Policy experience axis
POLICY_EXPERIENCE_AXIS = AxisTemplate(
    name="Policy Experience",
    description="Experience in AI policy or governance",
    ranking_keyword="POLICY_EXPERIENCE_RATING",
    prompt_section="""## Policy Experience
Evaluate the candidate's experience in AI policy, governance, or regulatory matters.
Consider their work in policy formulation, understanding of regulatory frameworks, and engagement with policy institutions.
Provide your analysis and then state '{ranking_keyword} = ' followed by an integer from 1-5."""
)

# AI Safety axis
AI_SAFETY_AXIS = AxisTemplate(
    name="Understanding of AI Safety",
    description="Knowledge and understanding of AI safety concepts",
    ranking_keyword="AI_SAFETY_RATING",
    prompt_section="""## Understanding of AI Safety
Assess the candidate's understanding of AI safety concepts, alignment, and technical safety considerations.
Consider their demonstrated knowledge, relevant work, and their approach to safety challenges.
Provide your analysis and then state '{ranking_keyword} = ' followed by an integer from 1-5."""
)

# Path to impact axis
PATH_TO_IMPACT_AXIS = AxisTemplate(
    name="Path to Impact",
    description="Clarity and feasibility of their planned impact",
    ranking_keyword="PATH_TO_IMPACT_RATING",
    prompt_section="""## Path to Impact
Evaluate the clarity and feasibility of the candidate's planned path to making a positive impact in the field.
Consider the specificity of their goals, the practicality of their approach, and the potential significance of their impact.
Provide your analysis and then state '{ranking_keyword} = ' followed by an integer from 1-5."""
)

# Research experience axis
RESEARCH_EXPERIENCE_AXIS = AxisTemplate(
    name="Research Experience",
    description="Academic or industry research experience",
    ranking_keyword="RESEARCH_EXPERIENCE_RATING",
    prompt_section="""## Research Experience
Assess the candidate's research experience, whether in academia or industry.
Consider the quality and relevance of their research, publications, and demonstrated research abilities.
Provide your analysis and then state '{ranking_keyword} = ' followed by an integer from 1-5."""
)

# Define the complete multi-axis template
ACADEMIC_MULTI_AXIS_TEMPLATE = MultiAxisTemplate(
    id="multi_axis_academic",
    name="Multi-Axis Academic Evaluation",
    description="Comprehensive evaluation across multiple axes of academic and research potential",
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
        GENERAL_PREMISE_AXIS,
        ML_SKILLS_AXIS,
        POLICY_EXPERIENCE_AXIS,
        AI_SAFETY_AXIS,
        PATH_TO_IMPACT_AXIS,
        RESEARCH_EXPERIENCE_AXIS
    ]
)