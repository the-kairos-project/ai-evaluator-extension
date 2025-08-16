# PDF Resume Parser Plugin

This plugin extracts text and structured data from PDF resumes. It uses a dual approach:
1. First tries direct extraction with pdfminer.six
2. Falls back to LLM-based parsing if direct extraction misses key sections

## Features

- Downloads PDF files from URLs
- Extracts text using pdfminer.six
- Parses structured data from resumes:
  - Personal information (name, email, phone, location)
  - Education history
  - Work experience
  - Skills
  - Projects
  - Languages
- Falls back to LLM for more accurate parsing when direct extraction fails
- Integrates with the MCP evaluation workflow

## Installation

The plugin requires the following dependencies:
- pdfminer.six
- requests

Install the dependencies:

```bash
pip install -r requirements-pdf-plugin.txt
```

## Usage

The plugin is automatically loaded by the MCP server and used when a PDF URL is detected in the `source_url` parameter of an evaluation request.

### Direct API Usage

```python
from src.plugins.pdf_resume_plugin import PDFResumePlugin
from src.core.plugin_system.plugin_interface import PluginRequest

# Initialize plugin
plugin = PDFResumePlugin()
await plugin.initialize()

# Create request
request = PluginRequest(
    request_id="test_request",
    action="parse_resume",
    parameters={
        "pdf_url": "https://example.com/resume.pdf",
        "use_llm_fallback": True,
        "llm_provider": "anthropic",
        "llm_model": "claude-3-5-sonnet-20241022"
    }
)

# Execute plugin
response = await plugin.execute(request)

# Process response
if response.status == "success":
    parsed_resume = response.data["parsed_resume"]
    raw_text = response.data["raw_text"]
    print(f"Name: {parsed_resume['personal_info']['name']}")
    print(f"Skills: {', '.join(parsed_resume['skills'])}")
else:
    print(f"Error: {response.error}")
```

### Testing

Use the test script to test the plugin with a sample resume:

```bash
python test_pdf_resume_parser.py --pdf-url https://example.com/resume.pdf
```

To disable LLM fallback:

```bash
python test_pdf_resume_parser.py --pdf-url https://example.com/resume.pdf --no-llm-fallback
```

## Output Format

The plugin returns structured data in the following format:

```json
{
  "parsed_resume": {
    "personal_info": {
      "name": "John Doe",
      "email": "john.doe@example.com",
      "phone": "(123) 456-7890",
      "location": "San Francisco, CA"
    },
    "education": [
      {
        "institution": "Stanford University",
        "degree": "Master of Science in Computer Science",
        "period": "2018-2020",
        "details": "GPA: 3.9/4.0"
      }
    ],
    "experience": [
      {
        "company": "Google",
        "title": "Software Engineer",
        "period": "2020-Present",
        "responsibilities": [
          "Developed and maintained backend services",
          "Optimized database queries",
          "Led a team of 5 engineers"
        ]
      }
    ],
    "skills": [
      "Python", "JavaScript", "SQL", "Machine Learning", "AWS"
    ],
    "projects": [
      {
        "name": "Personal Website",
        "description": "Built a personal website using React and Node.js"
      }
    ],
    "languages": [
      {
        "language": "English",
        "proficiency": "Native"
      },
      {
        "language": "Spanish",
        "proficiency": "Fluent"
      }
    ]
  },
  "raw_text": "John Doe\njohn.doe@example.com\n...",
  "text_length": 5000,
  "source_url": "https://example.com/resume.pdf"
}
```

## LLM Fallback

The plugin uses LLM fallback when direct extraction fails to extract key sections. In practice, direct extraction via `pdfminer.six` frequently misses structured sections for many resume formats, so the plugin will often fall back to the LLM parser — this is the common path for many resumes. LLM fallback is enabled by default but can be disabled by setting `use_llm_fallback` to `false` in the request parameters.

When fallback is used, the LLM parses the raw text extracted from the PDF and fills in missing sections. You can configure which LLM provider and model are used via the request parameters. If you have a high volume of PDFs and want to reduce API usage, consider preprocessing PDFs (OCR, text normalization) or selectively disabling LLM fallback for known-good sources.