"""
Data models for PDF resume parsing.

This module defines the data models used by the PDF resume parser.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PersonalInfo(BaseModel):
    """Personal information from a resume."""
    
    name: Optional[str] = Field(None, description="Full name of the candidate")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[str] = Field(None, description="Location or address")


class Education(BaseModel):
    """Education entry from a resume."""
    
    institution: Optional[str] = Field(None, description="Name of the educational institution")
    degree: Optional[str] = Field(None, description="Degree earned or program of study")
    period: Optional[str] = Field(None, description="Time period of study")
    details: Optional[str] = Field(None, description="Additional details about the education")


class Experience(BaseModel):
    """Work experience entry from a resume."""
    
    company: Optional[str] = Field(None, description="Company name")
    title: Optional[str] = Field(None, description="Job title")
    period: Optional[str] = Field(None, description="Employment period")
    responsibilities: List[str] = Field(default_factory=list, description="Job responsibilities")


class Skill(BaseModel):
    """Skill entry from a resume."""
    
    name: str = Field(..., description="Skill name")
    level: Optional[str] = Field(None, description="Skill level or proficiency")


class Project(BaseModel):
    """Project entry from a resume."""
    
    name: Optional[str] = Field(None, description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    technologies: List[str] = Field(default_factory=list, description="Technologies used")
    url: Optional[str] = Field(None, description="Project URL")


class Language(BaseModel):
    """Language proficiency entry from a resume."""
    
    language: str = Field(..., description="Language name")
    proficiency: Optional[str] = Field(None, description="Proficiency level")


class ResumeData(BaseModel):
    """Structured resume data."""
    
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo, description="Basic contact information")
    education: List[Education] = Field(default_factory=list, description="Education history")
    experience: List[Experience] = Field(default_factory=list, description="Work experience")
    skills: List[str] = Field(default_factory=list, description="Skills")
    projects: List[Project] = Field(default_factory=list, description="Projects")
    languages: List[Language] = Field(default_factory=list, description="Languages")