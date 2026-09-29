```text
Select and order the candidate's projects for this resume. Use only the supplied project records. Job requirements describe the employer's needs and are not evidence about the candidate. Select the most relevant projects and order them by relevance, using chronology to resolve ties. Within each selected project, choose the strongest relevant source bullets and order them by relevance. Use bullet-level skills, archetypes, and strength only as selection and ordering metadata. Include no more than three bullets per project.

Keep every selected bullet grounded in its source facts, scope, technologies, responsibilities, and metrics. Rewrite only when that meaningfully improves relevance or impact. Do not add claims, tools, responsibilities, outcomes, metrics, or causal links. If the source has no quantitative measure, retain a concrete verifiable result or scope. Preserve project name, role, and dates accurately. Format dates as mmm yyyy or Present, with -- between start and end dates. Include links only when their URLs are explicitly present in the source record; each link needs a concise label and its exact URL. Omit projects that add no useful information.

<requirements_json>
{{REQUIREMENTS_JSON}}
</requirements_json>

<section_data>
{{SECTION_DATA}}
</section_data>

Return one JSON object with an entries array. Each entry must contain name, dates, role, links, and bullets. Links is an array of objects with label and url strings. Bullets is an array of at least one, but no more than three strings. Example:
{"entries":[{"name":"Project","dates":"mmm yyyy -- mmm yyyy","role":"Personal Project","links":[{"label":"GitHub","url":"https://github.com/example/project"}],"bullets":["Accomplishment grounded in the source"]}]}

Return an empty entries array if no projects apply. Return strict JSON only, with no Markdown fences, explanation, or extra keys. All values must be content data; do not generate document markup or formatting syntax.
```
