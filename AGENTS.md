# Resume tailoring project

This project maintains a structured library of resume experience and project content and uses it to tailor a LaTex `.tex` resume to the job description in `Job_Description.txt`.

## Content library

- Store each role as one Markdown file under `resume_data/experience/`.
- Store each project as one Markdown file under `resume_data/projects/`.
- Store each education entry as one Markdown file under `resume_data/education/`.
- Store the overall skills inventory as one Markdown list in `resume_data/skills.md`; skills do not need individual files.
- Keep reusable LaTeX templates directly under `templates/`. 
  `00-resume-template.tex` is the document base;
  `01-education-template.tex`, `03-experience-template.tex`, and `04-projects-template.tex` are entry snippets;
  `02-skills-template.tex` is the complete skills section.
- Keep reusable Ollama prompt drafts under `src/prompts/`: extract role requirements to JSON first, then ask separately for structured Education, Skills, Experience, and Projects data using the corresponding `resume_data/` content. Python renders those results through the LaTeX templates and appends them to the document base.
- Section prompts use the exact tokens `{{REQUIREMENTS_JSON}}` and `{{SECTION_DATA}}` inside a fenced prompt body. They ask Ollama for strict structured JSON content only; Python validates the data, escapes LaTeX text, and renders each section with the templates.
- Each file starts and ends its YAML frontmatter with `---` and follows the corresponding schema used by the existing records. Keep IDs unique within each record type, and give each bullet a stable ID.
- Preserve the candidate's stated facts and metrics. Do not add qualifications, outcomes, or metrics that are not supported by the source resume or candidate-provided information.

## Tailoring workflow

Run the workflow from the project root with `python main.py`. Ollama must be running locally and the `gemma4:12b` model must already be installed. The local Ollama URL defaults to `http://localhost:11434`; override the model and URL with `--model` / `OLLAMA_MODEL` and `--ollama-url` / `OLLAMA_URL`. Pass `--debug` to write all console output, rendered prompts, and complete Ollama API responses to the root `debug.log` file as well as the console.

1. Read `Job_Description.txt` (or the path supplied with `--job-description`) and extract requirements with `src/prompts/01-extract-job-requirements.md`.
2. Save the JSON response to `build/ollama/requirements/YYYY-MM-DD_<job-company>_<job-title>.json`. Use the current date in ISO format (`YYYY-MM-DD`) and lowercase hyphenated filename-safe slugs for the company and job title; use `unknown-company` if the company is not stated.
3. For each section, send its numbered prompt, the requirements JSON, that section's `resume_data/` content, and its LaTeX entry template to Ollama. The expected prompts are `02-education.md`, `03-skills.md`, `04-experience.md`, and `05-projects.md` in `src/prompts/`; each returns a JSON array of filled LaTeX snippets. The workflow appends each array to `templates/00-resume-template.tex`, adds section/list wrappers except for Skills, and closes the document.
4. Choose the output path from `--output` when supplied; otherwise use `<first-name>_<last-name>_<job-company>_<job-title>.tex` in the project root. The default candidate name comes from the base LaTeX template; the company and job title are converted to lowercase hyphenated slugs, using `unknown-company` when the company is not stated. Relative `--output` paths are resolved from the project root, and output paths must end in `.tex`.
5. Before replacing the selected output file, move its existing source to `build/ollama/resume/YYYY-MM-DD_<job-company>_<job-title>.tex`, using the same date as the requirements file and metadata from the archived source when available. Do this only after the replacement source is ready to write. If that archive path already exists, preserve it and choose a non-overwriting suffix for the additional copy. Generated resumes in the archive and project root can be reused as caches when their recorded company and job title match the job description.
6. Write the newly tailored source to the selected output path, then compile it with `latexmk`.

Do not treat requirements or preferences in a job description as candidate qualifications. Keep the content library reusable across applications; job-specific selection belongs in the resume output.
