# Resume tailoring project

This project maintains a structured library of resume experience and project content and uses it to tailor `Chujia_Guo_Software_Engineering_Resume.tex` to the job description in `Job_Description.txt`.

## Content library

- Store each role as one Markdown file under `resume_data/experience/`.
- Store each project as one Markdown file under `resume_data/projects/`.
- Store each education entry as one Markdown file under `resume_data/education/`.
- Store the overall skills inventory as one Markdown list in `resume_data/skills.md`; skills do not need individual files.
- Keep reusable LaTeX templates directly under `templates/`. `00-resume-template.tex` is the document base; `01-education-template.tex`, `03-experience-template.tex`, and `04-projects-template.tex` are entry snippets; `02-skills-template.tex` is the complete skills section.
- Keep reusable Ollama prompt drafts under `src/prompts/`: extract role requirements to JSON first, then ask separately for structured Education, Skills, Experience, and Projects data using the corresponding `resume_data/` content. Python renders those results through the LaTeX templates and appends them to the document base.
- Section prompts use the exact tokens `{{REQUIREMENTS_JSON}}` and `{{SECTION_DATA}}` inside a fenced prompt body. They ask Ollama for strict structured JSON content only; Python validates the data, escapes LaTeX text, and renders each section with the templates.
- Each file starts and ends its YAML frontmatter with `---` and follows the corresponding schema used by the existing records. Keep IDs unique within each record type, and give each bullet a stable ID.
- Preserve the candidate's stated facts and metrics. Do not add qualifications, outcomes, or metrics that are not supported by the source resume or candidate-provided information.
- Treat `skills`, `archetypes`, and `strength` as metadata for selecting and ordering bullets. Strength is an integer from 1 (supporting) to 5 (essential).

## Schemas

Use these templates when adding records. Replace placeholders with supported facts; omit optional project links when they are unavailable. The `---` lines delimit valid YAML frontmatter.

### Experience: `resume_data/experience/<company-role-slug>.md`

```markdown
---
id: unique-experience-slug
company: "Company Name"
role: "Job Title"
location: "City, ST"
start_date: "YYYY-MM"
end_date: "YYYY-MM" # or "Present"
skills:
  - Skill1
  - Skill2
bullets:
  - id: exp-b1
    text: "Action verb + context + quantifiable impact."
    skills: [Skill1, Skill2]
    archetypes: [backend, distributed-systems, devops]
    strength: 5 # integer from 1 to 5; 5 = essential hero bullet
    metric: "Quantifiable metric summary"
---
```

### Project: `resume_data/projects/<project-slug>.md`

```markdown
---
id: unique-project-slug
title: "Project Name"
role: "Role / Context" # e.g., Personal Project, Open Source Contributor
url: "https://github.com/..." # optional
demo: "https://..." # optional
start_date: "YYYY-MM"
end_date: "YYYY-MM" # or "Present"
skills:
  - Skill1
  - Skill2
bullets:
  - id: proj-b1
    text: "Action verb + context + quantifiable impact."
    skills: [Skill1, Skill2]
    archetypes: [fullstack, machine-learning, cloud]
    strength: 5 # integer from 1 to 5; 5 = essential hero bullet
    metric: "Quantifiable metric summary"
---
```

### Education: `resume_data/education/<institution-degree-slug>.md`

```markdown
---
id: unique-education-slug
institution: "Institution Name"
location: "City, ST"
degree: "Degree Name"
field: "Field of Study"
start_date: "YYYY-MM"
end_date: "YYYY-MM" # or "Present"
---
```

Add no more than three bullets to any one experience or project entry. Each entry template is a LaTeX snippet; the workflow adds section headings and list wrappers around all sections except Skills.

## Tailoring workflow

Run the workflow from the project root with `python main.py`. Ollama must be running locally and the `gemma4:12b` model must already be installed. The local Ollama URL defaults to `http://localhost:11434`; override the model and URL with `--model` / `OLLAMA_MODEL` and `--ollama-url` / `OLLAMA_URL`. Pass `--debug` to write all console output, rendered prompts, and complete Ollama API responses to the root `debug.log` file as well as the console.

1. Read `Job_Description.txt` (or the path supplied with `--job-description`) and extract requirements with `src/prompts/01-extract-job-requirements.md`.
2. Save the JSON response to `build/ollama/requirements/YYYY-MM-DD_<job-company>_<job-title>.json`. Use the current date in ISO format (`YYYY-MM-DD`) and lowercase hyphenated filename-safe slugs for the company and job title; use `unknown-company` if the company is not stated.
3. For each section, send its numbered prompt, the requirements JSON, that section's `resume_data/` content, and its LaTeX entry template to Ollama. The expected prompts are `02-education.md`, `03-skills.md`, `04-experience.md`, and `05-projects.md` in `src/prompts/`; each returns a JSON array of filled LaTeX snippets. The workflow appends each array to `templates/00-resume-template.tex`, adds section/list wrappers except for Skills, and closes the document.
4. Before replacing the root resume, move the existing `Chujia_Guo_Software_Engineering_Resume.tex` to `build/ollama/resume/YYYY-MM-DD_Chujia_Guo_Software_Engineering_Resume.tex`, using the same date as the requirements file. Do this only after the replacement source is ready to write. If that archive path already exists, preserve it and choose a non-overwriting suffix for the additional copy.
5. Write the newly tailored source to the project root as `Chujia_Guo_Software_Engineering_Resume.tex`, then compile it with `latexmk Chujia_Guo_Software_Engineering_Resume.tex`.

Do not treat requirements or preferences in a job description as candidate qualifications. Keep the content library reusable across applications; job-specific selection belongs in the resume output.
