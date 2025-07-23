"""
PDF Resume Parser Plugin for MCP Server.

This plugin extracts text and structured data from PDF resumes.
It uses a dual approach:
1. First tries direct extraction with pdfminer.six
2. Falls back to LLM-based parsing if direct extraction misses key sections
"""

from .plugin import PDFResumePlugin
from .models import ResumeData, PersonalInfo, Education, Experience, Skill, Project, Language

__all__ = [
    "PDFResumePlugin",
    "ResumeData",
    "PersonalInfo",
    "Education",
    "Experience",
    "Skill",
    "Project",
    "Language"
]