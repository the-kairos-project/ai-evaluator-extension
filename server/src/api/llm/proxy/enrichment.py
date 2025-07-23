"""
Enrichment functionality for LLM evaluation.

This module handles the formatting of enrichment data from various sources
(LinkedIn, PDF resumes, etc.) for inclusion in LLM prompts.
"""

import json
from typing import Dict, Any


def format_enrichment_data(enrichment_data: Dict[str, Any]) -> str:
    """Format enrichment data for inclusion in the prompt.
    
    Args:
        enrichment_data: Dictionary containing enrichment data
        
    Returns:
        str: Formatted text to include in the prompt
    """
    
    formatted = "### CANDIDATE PROFILE INFORMATION\n\n"
    data_type = enrichment_data.get("type", "unknown")
    data = enrichment_data.get("data", {})
    
    if data_type == "combined":
        
        linkedin_data = data.get("linkedin", {})
        if linkedin_data:
            formatted += "## LinkedIn Profile\n"
            
            if "name" in linkedin_data:
                formatted += f"Name: {linkedin_data['name']}\n"
            
            current_position = None
            current_company = None
            if "experience" in linkedin_data and linkedin_data["experience"] and len(linkedin_data["experience"]) > 0:
                current_position = linkedin_data["experience"][0].get("title", "")
                current_company = linkedin_data["experience"][0].get("company", "")
            
            if current_position and current_company:
                formatted += f"Current Position: {current_position} at {current_company}\n"
            elif "headline" in linkedin_data:
                formatted += f"Headline: {linkedin_data['headline']}\n"
            
            if "about" in linkedin_data and linkedin_data["about"]:
                about_text = linkedin_data["about"]
                about_excerpt = about_text[:200] + "..." if len(about_text) > 200 else about_text
                formatted += f"About: {about_excerpt}\n"
            
            if "experience" in linkedin_data and linkedin_data["experience"]:
                formatted += "\n### Work Experience\n"
                for exp in linkedin_data["experience"][:3]:  # Limit to recent experiences
                    title = exp.get("title", "")
                    company = exp.get("company", "")
                    from_date = exp.get("from_date", "")
                    to_date = exp.get("to_date", "Present")
                    description = exp.get("description", "")
                    
                    formatted += f"- {title} at {company}"
                    if from_date or to_date:
                        formatted += f" ({from_date} - {to_date})"
                    formatted += "\n"
                    
                    if description:
                        desc_excerpt = description[:200] + "..." if len(description) > 200 else description
                        formatted += f"  {desc_excerpt}\n"
                
                if len(linkedin_data["experience"]) > 3:
                    formatted += f"  ... and {len(linkedin_data['experience']) - 3} more positions\n"
            
            if "education" in linkedin_data and linkedin_data["education"]:
                formatted += "\n### Education\n"
                for edu in linkedin_data["education"]:
                    degree = edu.get("degree", "")
                    institution = edu.get("institution", "")
                    formatted += f"- {degree} at {institution}\n"
                    
                    if edu.get("description"):
                        desc_excerpt = edu["description"][:150] + "..." if len(edu["description"]) > 150 else edu["description"]
                        formatted += f"  {desc_excerpt}\n"
            
            if "skills" in linkedin_data and linkedin_data["skills"]:
                formatted += "\n### Skills\n"
                skills_list = ', '.join(linkedin_data["skills"][:15])
                if len(linkedin_data["skills"]) > 15:
                    skills_list += f", and {len(linkedin_data['skills']) - 15} more"
                formatted += f"{skills_list}\n"
        
        pdf_data = data.get("pdf", {})
        parsed_resume = pdf_data.get("parsed_resume", {})
        if parsed_resume:
            formatted += "\n## PDF Resume Information\n"
            
            personal_info = parsed_resume.get("personal_info", {})
            if personal_info:
                if personal_info.get("email"):
                    formatted += f"Email: {personal_info['email']}\n"
                if personal_info.get("phone"):
                    formatted += f"Phone: {personal_info['phone']}\n"
                if personal_info.get("location"):
                    formatted += f"Location: {personal_info['location']}\n"
            
            education = parsed_resume.get("education", [])
            if education:
                formatted += "\n### Education from Resume\n"
                for edu in education[:3]:
                    institution = edu.get("institution", "")
                    degree = edu.get("degree", "")
                    period = edu.get("period", "")
                    
                    formatted += f"- {degree if degree else 'Degree not specified'} at {institution}"
                    if period:
                        formatted += f" ({period})"
                    formatted += "\n"
                    
                    if edu.get("details"):
                        formatted += f"  {edu['details']}\n"
                
                if len(education) > 3:
                    formatted += f"  ... and {len(education) - 3} more education entries\n"
            
            experience = parsed_resume.get("experience", [])
            if experience:
                formatted += "\n### Work Experience from Resume\n"
                for exp in experience[:3]:
                    title = exp.get("title", "")
                    company = exp.get("company", "")
                    period = exp.get("period", "")
                    
                    formatted += f"- {title if title else 'Role not specified'} at {company}"
                    if period:
                        formatted += f" ({period})"
                    formatted += "\n"
                    
                    responsibilities = exp.get("responsibilities", [])
                    for i, resp in enumerate(responsibilities[:2]):
                        formatted += f"  - {resp}\n"
                    
                    if len(responsibilities) > 2:
                        formatted += f"  - ... and {len(responsibilities) - 2} more responsibilities\n"
                
                if len(experience) > 3:
                    formatted += f"  ... and {len(experience) - 3} more experience entries\n"
            
            skills = parsed_resume.get("skills", [])
            if skills:
                formatted += "\n### Skills from Resume\n"
                skills_list = ', '.join(skills[:15])
                if len(skills) > 15:
                    skills_list += f", and {len(skills) - 15} more"
                formatted += f"{skills_list}\n"
            
            languages = parsed_resume.get("languages", [])
            if languages:
                formatted += "\n### Languages\n"
                for lang in languages:
                    language = lang.get("language", "")
                    proficiency = lang.get("proficiency", "")
                    if language:
                        formatted += f"- {language}"
                        if proficiency:
                            formatted += f" ({proficiency})"
                        formatted += "\n"
        
        return formatted
    
    if data_type == "linkedin":
        formatted += "## LinkedIn Profile\n"
        
        if "name" in data:
            formatted += f"Name: {data['name']}\n"
        if "headline" in data:
            formatted += f"Headline: {data['headline']}\n"
        
        if "about" in data and data["about"]:
            about_text = data["about"]
            about_excerpt = about_text[:200] + "..." if len(about_text) > 200 else about_text
            formatted += f"About: {about_excerpt}\n"
        
        if "experience" in data and data["experience"]:
            formatted += "\n### Work Experience\n"
            for exp in data["experience"][:3]:  # Limit to recent experiences
                title = exp.get("title", "Unknown Title")
                company = exp.get("company", "Unknown Company")
                from_date = exp.get("from_date", "")
                to_date = exp.get("to_date", "Present")
                
                formatted += f"- {title} at {company}"
                if from_date or to_date:
                    formatted += f" ({from_date} - {to_date})"
                formatted += "\n"
                
                if "description" in exp and exp["description"]:
                    desc_excerpt = exp["description"][:200] + "..." if len(exp["description"]) > 200 else exp["description"]
                    formatted += f"  {desc_excerpt}\n"
            
            if len(data["experience"]) > 3:
                formatted += f"  ... and {len(data['experience']) - 3} more positions\n"
        
        if "education" in data and data["education"]:
            formatted += "\n### Education\n"
            for edu in data["education"]:
                school = edu.get("institution", edu.get("school", "Unknown Institution"))
                degree = edu.get("degree", "")
                date_range = edu.get("date_range", "")
                
                formatted += f"- {degree} at {school}"
                if date_range:
                    formatted += f" ({date_range})"
                formatted += "\n"
        
        if "skills" in data and data["skills"]:
            formatted += "\n### Skills\n"
            skills_list = ', '.join(data["skills"][:15])
            if len(data["skills"]) > 15:
                skills_list += f", and {len(data['skills']) - 15} more"
            formatted += f"{skills_list}\n"
    
    elif data_type == "pdf":
        formatted += "## PDF Resume Information\n"
        
        parsed_resume = data.get("parsed_resume", {})
        
        personal_info = parsed_resume.get("personal_info", {})
        if personal_info:
            if personal_info.get("name"):
                formatted += f"Name: {personal_info['name']}\n"
            if personal_info.get("email"):
                formatted += f"Email: {personal_info['email']}\n"
            if personal_info.get("phone"):
                formatted += f"Phone: {personal_info['phone']}\n"
            if personal_info.get("location"):
                formatted += f"Location: {personal_info['location']}\n"
        
        education = parsed_resume.get("education", [])
        if education:
            formatted += "\n### Education\n"
            for edu in education[:3]:
                institution = edu.get("institution", "Unknown Institution")
                degree = edu.get("degree", "")
                period = edu.get("period", "")
                
                formatted += f"- {degree if degree else 'Degree not specified'} at {institution}"
                if period:
                    formatted += f" ({period})"
                formatted += "\n"
                
                if edu.get("details"):
                    formatted += f"  {edu['details']}\n"
            
            if len(education) > 3:
                formatted += f"  ... and {len(education) - 3} more education entries\n"
        
        experience = parsed_resume.get("experience", [])
        if experience:
            formatted += "\n### Work Experience\n"
            for exp in experience[:3]:
                company = exp.get("company", "Unknown Company")
                title = exp.get("title", "")
                period = exp.get("period", "")
                
                formatted += f"- {title if title else 'Role not specified'} at {company}"
                if period:
                    formatted += f" ({period})"
                formatted += "\n"
                
                responsibilities = exp.get("responsibilities", [])
                for resp in responsibilities[:2]:  # Limit to first 2 responsibilities
                    formatted += f"  - {resp}\n"
                
                if len(responsibilities) > 2:
                    formatted += f"  - ... and {len(responsibilities) - 2} more responsibilities\n"
            
            if len(experience) > 3:
                formatted += f"  ... and {len(experience) - 3} more experience entries\n"
        
        skills = parsed_resume.get("skills", [])
        if skills:
            formatted += "\n### Skills\n"
            skills_list = ', '.join(skills[:15])
            if len(skills) > 15:
                skills_list += f", and {len(skills) - 15} more"
            formatted += f"{skills_list}\n"
        
        languages = parsed_resume.get("languages", [])
        if languages:
            formatted += "\n### Languages\n"
            for lang in languages:
                language = lang.get("language", "")
                proficiency = lang.get("proficiency", "")
                if language:
                    formatted += f"- {language}"
                    if proficiency:
                        formatted += f" ({proficiency})"
                    formatted += "\n"
    
    else:
        formatted += f"## Data from {data_type}:\n"
        formatted += json.dumps(data, indent=2)
    
    return formatted