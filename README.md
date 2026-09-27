# Resume Tailoring

This project tailors a LaTeX resume to a job description using a local Ollama model. Resume facts are stored in a reusable content library, and the workflow selects and formats relevant education, skills, experience, and projects for each application.

## Requirements

- Python 3.10 or newer
- [Ollama](https://ollama.com/) installed and running locally
- The `gemma4:12b` model pulled into Ollama (or another compatible model selected with `--model`)
- `latexmk` and a LaTeX installation with the packages used by the resume template

For the default model, install it with:

```sh
ollama pull gemma4:12b
```

Start Ollama before running the workflow. Its default API address is `http://localhost:11434`.

## Generate a tailored resume

1. Put the target job description in `Job_Description.txt`, or provide a different text file with `--job-description`.
2. From the project root, run:

   ```sh
   python main.py
   ```

The workflow extracts requirements from the job description, asks Ollama to generate each resume section, assembles the LaTeX source, archives the previous root resume, and compiles the new source with `latexmk`.

To use a different model, Ollama server, or job-description file:

```sh
python main.py --model <installed-model> --ollama-url http://localhost:11434 \
  --job-description path/to/job-description.txt
```

The model and server URL can also be set with `OLLAMA_MODEL` and `OLLAMA_URL`. Command-line options take precedence over those environment variables. Use `python main.py --help` to see the available options.

To record console output, rendered prompts, and complete Ollama API responses in `debug.log` while also printing them to the console:

```sh
python main.py --debug
```

## Output files

- `Chujia_Guo_Software_Engineering_Resume.tex` — the newly tailored LaTeX source.
- The compiled PDF is copied to the project root by the `latexmk` configuration.
- `build/ollama/requirements/` — extracted job requirements in JSON, named with the run date, company, and role.
- `build/ollama/resume/` — timestamped copies of prior resume sources. Existing archive files are preserved; a suffix is added if needed to avoid overwriting one.
- `build/latexmk/` — LaTeX build intermediates.
- `debug.log` — created or updated when running with `--debug`.

Generated build files and the debug log are excluded from version control.

## Project layout

```text
resume_data/
  education/       Education records
  experience/      Role records and reusable achievement bullets
  projects/        Project records and reusable achievement bullets
  skills.md        Overall skills inventory
templates/         LaTeX document base, section templates, and snippets
src/
  prompts/       Ollama prompts for requirements and resume sections
  workflow.py    Workflow implementation
main.py            Command-line entry point
Job_Description.txt Default job description input
```

## Maintaining resume content

Add each role, project, or education entry as a Markdown file in its corresponding `resume_data/` directory. Follow the YAML frontmatter schema and examples in [AGENTS.md](AGENTS.md). Keep record IDs unique within each type, assign stable IDs to bullets, and include no more than three bullets per role or project. Update the single skills inventory in `resume_data/skills.md`.

Content must reflect candidate-provided facts. Do not add qualifications, results, or metrics based on the job description. The `skills`, `archetypes`, and `strength` fields help select and order reusable bullets; they are metadata, not claims to append to the resume. Job-specific choices belong in the generated resume, so the underlying content library remains reusable.

The workflow reads the base document from `templates/00-resume-template.tex`, uses the numbered section prompts in `src/prompts/`, and formats results with the corresponding templates in `templates/`. Skills returns a complete section; the other section prompts return entry snippets that the workflow places inside section and list wrappers.
