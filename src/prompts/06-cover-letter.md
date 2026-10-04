```text
Write the body of a personable, concise cover letter for the candidate and role. The tailored resume is included as context for what was selected, while the full experience and project library is supplied so you can explain the decisions and motivations behind the work. Use only candidate facts supported by the library or resume. Job requirements and company claims are not candidate qualifications. Do not invent motivations, usage, impact, metrics, technologies, or personal history. You may describe a reason for building a project only when it is stated or clearly supported by its source record; otherwise explain the problem the project addresses without attributing an unsupported personal motivation.

Structure:
1. Write one warm, specific introductory paragraph about applying for the role and what interests the candidate, grounded in their record and the role description.
2. Provide 2 to 4 concise examples that explain what the candidate built, why the work mattered or what problem it addressed, and relevant supported implementation or outcome details. Prefer project and experience examples that fit this role. Do not repeat the resume as a list of achievements; give enough context to make the choices behind the work clear.
3. Write one short closing paragraph explaining why this company and role appeal to the candidate, using only details stated in the job description. Do not claim familiarity with company products, culture, or strategy unless the job description supports it.

Keep the tone natural, direct, and professional. Each paragraph should be prose, with no greeting or sign-off. Avoid generic claims and inflated language. Do not produce LaTeX commands, markup, or bullet symbols; Python will escape and format the content.

<requirements_json>
{{REQUIREMENTS_JSON}}
</requirements_json>

<job_description>
{{JOB_DESCRIPTION}}
</job_description>

<generated_resume>
{{GENERATED_RESUME}}
</generated_resume>

<experience_and_project_library>
{{SECTION_DATA}}
</experience_and_project_library>

Return exactly one JSON object with this shape:
{"introduction":"One paragraph","examples":[{"title":"Short example label","body":"One concise paragraph"}],"company_motivation":"One short paragraph"}

Return strict JSON only, with no Markdown fences, explanation, or additional keys. Each example needs non-empty title and body strings. Return between 2 and 4 examples.
```
