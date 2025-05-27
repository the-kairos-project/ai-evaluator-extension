// Type definitions for help content
export interface HelpContent {
  purpose: string;
  setup?: string;
  examples?: string[];
  bestPractices?: string[];
  consequences?: string;
}

// Comprehensive help content for all fields
// This file contains all the help text and can be easily updated without touching component logic
export const HELP_CONTENT: Record<string, HelpContent> = {
  applicantTable: {
    purpose: 'Select the table containing applicant responses and application data',
    setup:
      'Choose the table where applicant submissions are stored. This is typically where form responses or application data is collected.',
    examples: ['Applications table', 'Course Applications 2024', 'Job Candidates'],
    bestPractices: [
      'Use a dedicated table for applications rather than mixing with other data',
      'Ensure the table has consistent field naming across applications',
    ],
    consequences: 'Changing this will reset your field selections and view settings',
  },
  applicantView: {
    purpose:
      'Choose which view of applicants to evaluate (filters and sorts applicants)',
    setup: 'Select a view to control which applicants get evaluated and in what order.',
    examples: [
      'All Applications (to evaluate everyone)',
      'Pending Review (to evaluate only unprocessed applications)',
      "This Week's Applications (to evaluate recent submissions)",
    ],
    bestPractices: [
      'Use filtered views to avoid re-evaluating already processed applicants',
      'Create views that exclude test submissions or incomplete applications',
      'Consider sorting by submission date for consistent processing order',
    ],
    consequences: 'Only applicants visible in this view will be evaluated',
  },
  sourceField: {
    purpose: 'Maps application response fields to evaluation inputs',
    setup:
      'Select the field from your applicant table that contains the response you want to evaluate.',
    examples: [
      'Why do you want to join this program?',
      'Describe your relevant experience',
      'What are your career goals?',
    ],
    bestPractices: [
      'Select fields with substantial text responses for better AI evaluation',
      'Avoid fields with just names, emails, or other basic data',
      'Choose fields that are relevant to your evaluation criteria',
    ],
    consequences:
      'The AI will only see the content from selected fields when making evaluations',
  },
  questionName: {
    purpose: 'Override the field name with a clearer question for the AI evaluator',
    setup:
      'Provide a clear, descriptive name that helps the AI understand what this field represents.',
    examples: ['Motivation Statement', 'Relevant Experience', 'Career Goals'],
    bestPractices: [
      "Use clear, descriptive names that explain the field's purpose",
      'Keep names concise but informative',
      'Use consistent naming conventions across fields',
    ],
    consequences:
      'The AI will see this name instead of the original field name, affecting how it interprets the content',
  },
  evaluationTable: {
    purpose: 'Select where evaluation results and scores will be stored',
    setup:
      'Choose the table where AI-generated evaluations, scores, and analysis will be saved.',
    examples: ['Evaluation Results', 'AI Scores', 'Application Analysis'],
    bestPractices: [
      'Use a separate table from applications for cleaner data organization',
      'Ensure the table has proper field types for storing scores and text',
      'Set up proper relationships between applicant and evaluation tables',
    ],
    consequences:
      'All evaluation results will be written to this table. Changing this resets field selections.',
  },
  outputField: {
    purpose: 'Select the field where AI evaluation scores will be stored',
    setup:
      "Choose a numeric field (Number, Percent, or Rating) where the AI's score for this criteria will be saved.",
    examples: [
      'Technical Skills Score (1-10)',
      'Communication Rating',
      'Cultural Fit Percentage',
    ],
    bestPractices: [
      'Use consistent scoring scales across all evaluation fields',
      'Choose appropriate field types: Number for raw scores, Rating for 1-5 scales, Percent for 0-100%',
      'Name fields clearly to indicate what aspect is being evaluated',
    ],
    consequences:
      'AI scores will be written to this field. Existing values may be overwritten.',
  },
  evaluationCriteria: {
    purpose: 'Define what the AI should evaluate and how to score responses',
    setup:
      'Write clear instructions for the AI evaluator, including what to look for and scoring scale.',
    examples: [
      'Rate technical skills 1-10 based on depth of experience and specific technologies mentioned',
      'Score communication ability 1-5: 1=poor grammar/unclear, 5=excellent written communication',
      'Evaluate motivation 0-100%: Consider passion, understanding of role, alignment with goals',
    ],
    bestPractices: [
      'Be specific about scoring criteria and scale (1-5, 1-10, 0-100%)',
      'Include examples of what constitutes high vs low scores',
      'Focus on measurable aspects rather than subjective preferences',
      'Keep criteria focused on one aspect per field',
    ],
    consequences:
      'Vague criteria lead to inconsistent scoring. Clear criteria improve AI accuracy and reliability.',
  },
  dependencyField: {
    purpose: 'Only evaluate if the selected input field contains a response',
    setup:
      'Choose an input field that must have content before this evaluation runs. Useful for conditional evaluations.',
    examples: [
      "Only score 'Technical Experience' if they answered the programming questions",
      "Only evaluate 'Leadership Skills' if they described leadership experience",
      "Only assess 'Research Background' if they mentioned research work",
    ],
    bestPractices: [
      "Use for optional sections that don't apply to all applicants",
      'Helps avoid unnecessary API calls and improves processing speed',
      'Useful for multi-stage applications with conditional sections',
    ],
    consequences:
      'Evaluation is skipped if the dependency field is empty, saving processing time and costs',
  },
  applicantField: {
    purpose: 'Links evaluation records back to the original applicant',
    setup:
      "Select the field that creates the relationship between evaluations and applicants. Usually a 'Link to another record' field.",
    examples: ['Applicant', 'Candidate', 'Application'],
    bestPractices: [
      'Ensure this field links to your applicant table',
      'Use the same field for all evaluations to maintain consistency',
      'This field is crucial for tracking which evaluation belongs to which applicant',
    ],
    consequences:
      "Without this link, you won't know which evaluation belongs to which applicant",
  },
  logsField: {
    purpose: 'Store detailed AI reasoning and decision process for transparency',
    setup:
      "Optional: Choose a long text field to store the AI's complete thought process and reasoning.",
    examples: ['AI Analysis', 'Evaluation Notes', 'Decision Logs'],
    bestPractices: [
      'Use Long Text or Rich Text fields for adequate space',
      'Helpful for understanding AI decisions and improving criteria',
      'Useful for manual review and quality assurance',
      'Can be disabled to save space if not needed',
    ],
    consequences:
      "Without logs, you won't see the AI's reasoning process. With logs, records will be larger but more transparent.",
  },
};
