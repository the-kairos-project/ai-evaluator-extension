"""
PDF resume parsing functionality.

This module handles parsing resume text into structured data.
"""

import re
from typing import List

from src.utils.logging import get_structured_logger

from .models import ResumeData, PersonalInfo, Education, Experience, Project, Language
from .extractor import extract_section

logger = get_structured_logger(__name__)


def parse_resume_text(text: str) -> ResumeData:
    """Parse resume text into structured data.
    
    Args:
        text: Extracted text from PDF
        
    Returns:
        ResumeData: Structured resume data
    """
    # Initialize resume data
    resume_data = ResumeData()
    
    # Extract personal information
    resume_data.personal_info = extract_personal_info(text)
    
    # Extract education
    resume_data.education = extract_education(text)
    
    # Extract experience
    resume_data.experience = extract_experience(text)
    
    # Extract skills
    resume_data.skills = extract_skills(text)
    
    # Extract projects
    resume_data.projects = extract_projects(text)
    
    # Extract languages
    resume_data.languages = extract_languages(text)
    
    return resume_data


def extract_personal_info(text: str) -> PersonalInfo:
    """Extract personal information from resume text.
    
    Args:
        text: Resume text
        
    Returns:
        PersonalInfo: Personal information
    """
    personal_info = PersonalInfo()
    
    # Extract name from the first few lines
    lines = text.split('\n')
    if lines:
        # Assume the name is in the first non-empty line
        for line in lines[:5]:
            if line.strip() and not any(x in line.lower() for x in ['@', 'http', '.com', 'resume', 'cv']):
                personal_info.name = line.strip()
                break
    
    # Extract email using regex
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_matches = re.findall(email_pattern, text)
    if email_matches:
        personal_info.email = email_matches[0]
    
    # Extract phone using regex
    phone_pattern = r'\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    phone_matches = re.findall(phone_pattern, text)
    if phone_matches:
        personal_info.phone = phone_matches[0]
    
    # Extract location - look for common location patterns
    location_section = extract_section(text, "location") or extract_section(text, "address")
    if location_section:
        personal_info.location = location_section.strip()
    else:
        # Try to find location in the header
        header_text = '\n'.join(lines[:10])
        # Look for city, state format (e.g., "San Francisco, CA")
        location_pattern = r'\b[A-Z][a-zA-Z\s]+,\s+[A-Z]{2}\b'
        location_matches = re.findall(location_pattern, header_text)
        if location_matches:
            personal_info.location = location_matches[0]
    
    return personal_info


def extract_education(text: str) -> List[Education]:
    """Extract education information from resume text.
    
    Args:
        text: Resume text
        
    Returns:
        List[Education]: Education entries
    """
    education_entries = []
    
    # Get education section
    education_section = extract_section(text, "education")
    if not education_section:
        return education_entries
    
    # Split into entries
    entries = split_into_entries(education_section)
    
    for entry in entries:
        if len(entry.strip()) < 10:  # Skip very short entries
            continue
            
        education = Education()
        
        lines = entry.split('\n')
        if not lines:
            continue
            
        # First line is usually institution
        education.institution = lines[0].strip()
        
        # Look for degree
        degree_patterns = [
            r'(?:Bachelor|Master|Ph\.?D\.?|B\.S\.|M\.S\.|M\.B\.A\.|B\.A\.|M\.A\.|B\.Tech|M\.Tech)[\s\.]+'
            r'(?:of|in|on)?[\s\.]+'
            r'(?:Science|Arts|Engineering|Business|Administration|Technology|Computer Science|[A-Za-z\s]+)',
            r'(?:BS|MS|BA|MA|MBA|PhD)[\s\.]+'
            r'(?:in|on)?[\s\.]+'
            r'(?:[A-Za-z\s]+)'
        ]
        
        for pattern in degree_patterns:
            degree_match = re.search(pattern, entry, re.IGNORECASE)
            if degree_match:
                education.degree = degree_match.group(0).strip()
                break
        
        # If no degree found, try second line
        if not education.degree and len(lines) > 1:
            education.degree = lines[1].strip()
        
        # Look for dates
        date_pattern = r'(?:19|20)\d{2}\s*(?:-|–|to)\s*(?:(?:19|20)\d{2}|present|current|now)'
        date_match = re.search(date_pattern, entry, re.IGNORECASE)
        if date_match:
            education.period = date_match.group(0).strip()
        
        # Add any remaining text as details
        if len(lines) > 2:
            details = []
            for line in lines[2:]:
                if line.strip() and not (education.period and education.period in line):
                    details.append(line.strip())
            if details:
                education.details = ' '.join(details)
        
        education_entries.append(education)
    
    return education_entries


def extract_experience(text: str) -> List[Experience]:
    """Extract work experience from resume text.
    
    Args:
        text: Resume text
        
    Returns:
        List[Experience]: Work experience entries
    """
    experience_entries = []
    
    # Get experience section
    experience_section = extract_section(text, "experience") or extract_section(text, "employment") or extract_section(text, "work")
    if not experience_section:
        return experience_entries
    
    # Split into entries
    entries = split_into_entries(experience_section)
    
    for entry in entries:
        if len(entry.strip()) < 10:  # Skip very short entries
            continue
            
        experience = Experience()
        
        lines = entry.split('\n')
        if not lines:
            continue
            
        # First line is usually company
        experience.company = lines[0].strip()
        
        # Look for job title
        title_patterns = [
            r'(?:Senior|Junior|Lead|Principal|Staff|Chief|Director|Manager|Engineer|Developer|Analyst|Consultant|Intern|Associate)\s+'
            r'(?:[A-Za-z\s]+)'
        ]
        
        for pattern in title_patterns:
            title_match = re.search(pattern, entry, re.IGNORECASE)
            if title_match:
                experience.title = title_match.group(0).strip()
                break
        
        # If no title found, try second line
        if not experience.title and len(lines) > 1:
            experience.title = lines[1].strip()
        
        # Look for dates
        date_pattern = r'(?:19|20)\d{2}\s*(?:-|–|to)\s*(?:(?:19|20)\d{2}|present|current|now)'
        date_match = re.search(date_pattern, entry, re.IGNORECASE)
        if date_match:
            experience.period = date_match.group(0).strip()
        
        # Extract responsibilities (bullet points)
        responsibilities = []
        bullet_pattern = r'[•\-*]\s*(.*?)(?=(?:[•\-*]|\n\n|\Z))'
        bullet_matches = re.findall(bullet_pattern, entry, re.DOTALL)
        if bullet_matches:
            for match in bullet_matches:
                clean_resp = match.strip()
                if clean_resp:
                    responsibilities.append(clean_resp)
        
        # If no bullet points, try to extract sentences
        if not responsibilities:
            # Find the text after title and dates
            main_text = entry
            if experience.title:
                main_text = main_text.replace(experience.title, '', 1)
            if experience.period:
                main_text = main_text.replace(experience.period, '', 1)
            if experience.company:
                main_text = main_text.replace(experience.company, '', 1)
                
            # Split by sentences
            sentences = re.split(r'(?<=[.!?])\s+', main_text)
            for sentence in sentences:
                clean_sent = sentence.strip()
                if clean_sent and len(clean_sent) > 20:  # Only include meaningful sentences
                    responsibilities.append(clean_sent)
        
        experience.responsibilities = responsibilities
        experience_entries.append(experience)
    
    return experience_entries


def extract_skills(text: str) -> List[str]:
    """Extract skills from resume text.
    
    Args:
        text: Resume text
        
    Returns:
        List[str]: Skills
    """
    skills = []
    
    # Get skills section
    skills_section = extract_section(text, "skills") or extract_section(text, "technical skills")
    if not skills_section:
        return skills
    
    # Try bullet points first
    bullet_pattern = r'[•\-*]\s*(.*?)(?=(?:[•\-*]|\n\n|\Z))'
    bullet_matches = re.findall(bullet_pattern, skills_section, re.DOTALL)
    if bullet_matches:
        for match in bullet_matches:
            clean_skill = match.strip()
            if clean_skill:
                skills.append(clean_skill)
    
    # If no bullet points, try comma separation
    if not skills:
        # Remove the section title
        section_text = re.sub(r'^.*?:', '', skills_section, 1, re.IGNORECASE)
        # Split by commas
        comma_skills = [s.strip() for s in section_text.split(',')]
        skills.extend([s for s in comma_skills if s])
    
    # If still no skills, try line by line
    if not skills:
        lines = skills_section.split('\n')
        for line in lines:
            clean_line = line.strip()
            if clean_line and not re.match(r'^skills|^technical\s+skills', clean_line, re.IGNORECASE):
                skills.append(clean_line)
    
    return skills


def extract_projects(text: str) -> List[Project]:
    """Extract projects from resume text.
    
    Args:
        text: Resume text
        
    Returns:
        List[Project]: Projects
    """
    project_entries = []
    
    # Get projects section
    projects_section = extract_section(text, "projects")
    if not projects_section:
        return project_entries
    
    # Split into entries
    entries = split_into_entries(projects_section)
    
    for entry in entries:
        if len(entry.strip()) < 10:  # Skip very short entries
            continue
            
        project = Project()
        
        lines = entry.split('\n')
        if not lines:
            continue
            
        # First line is usually project name
        project.name = lines[0].strip()
        
        # Look for URL
        url_pattern = r'https?://[^\s]+'
        url_match = re.search(url_pattern, entry)
        if url_match:
            project.url = url_match.group(0).strip()
        
        # Extract description
        if len(lines) > 1:
            description_lines = []
            for line in lines[1:]:
                if line.strip() and not (project.url and project.url in line):
                    description_lines.append(line.strip())
            if description_lines:
                project.description = ' '.join(description_lines)
        
        # Extract technologies
        tech_pattern = r'(?:Technologies|Tech Stack|Tools|Built with):\s*(.*?)(?=\n\n|\Z)'
        tech_match = re.search(tech_pattern, entry, re.IGNORECASE | re.DOTALL)
        if tech_match:
            tech_text = tech_match.group(1).strip()
            technologies = [t.strip() for t in tech_text.split(',')]
            project.technologies = [t for t in technologies if t]
        
        project_entries.append(project)
    
    return project_entries


def extract_languages(text: str) -> List[Language]:
    """Extract languages from resume text.
    
    Args:
        text: Resume text
        
    Returns:
        List[Language]: Languages
    """
    language_entries = []
    
    # Get languages section
    languages_section = extract_section(text, "languages")
    if not languages_section:
        return language_entries
    
    # Try bullet points first
    bullet_pattern = r'[•\-*]\s*(.*?)(?=(?:[•\-*]|\n\n|\Z))'
    bullet_matches = re.findall(bullet_pattern, languages_section, re.DOTALL)
    if bullet_matches:
        for match in bullet_matches:
            clean_lang = match.strip()
            if clean_lang:
                if ':' in clean_lang:
                    lang, prof = clean_lang.split(':', 1)
                    language_entries.append(Language(language=lang.strip(), proficiency=prof.strip()))
                else:
                    language_entries.append(Language(language=clean_lang))
    
    # If no bullet points, try line by line
    if not language_entries:
        lines = languages_section.split('\n')
        for line in lines:
            clean_line = line.strip()
            if clean_line and not re.match(r'^languages', clean_line, re.IGNORECASE):
                if ':' in clean_line:
                    lang, prof = clean_line.split(':', 1)
                    language_entries.append(Language(language=lang.strip(), proficiency=prof.strip()))
                elif '-' in clean_line:
                    lang, prof = clean_line.split('-', 1)
                    language_entries.append(Language(language=lang.strip(), proficiency=prof.strip()))
                elif '(' in clean_line and ')' in clean_line:
                    match = re.match(r'(.*?)\s*\((.*?)\)', clean_line)
                    if match:
                        language_entries.append(Language(language=match.group(1).strip(), proficiency=match.group(2).strip()))
                else:
                    language_entries.append(Language(language=clean_line))
    
    return language_entries


def split_into_entries(section_text: str) -> List[str]:
    """Split a section into individual entries.
    
    Args:
        section_text: Text of a section
        
    Returns:
        List[str]: List of entries
    """
    # Remove the section heading
    section_text = re.sub(r'^.*?:', '', section_text, 1, re.IGNORECASE)
    
    # Try to split by double newlines (paragraph breaks)
    entries = re.split(r'\n\s*\n', section_text)
    
    # If we only got one entry, try to split by years (common in resumes)
    if len(entries) <= 1:
        # Look for year patterns like "2018-2022" or "2018 - Present"
        year_pattern = r'\n(?=.*\b(19|20)\d{2}\b)'
        entries = re.split(year_pattern, section_text)
    
    # If we still only got one entry, try to split by bullet points
    if len(entries) <= 1:
        # Look for bullet point patterns
        bullet_pattern = r'\n(?=[•\-*])'
        entries = re.split(bullet_pattern, section_text)
    
    return [e.strip() for e in entries if e.strip()]