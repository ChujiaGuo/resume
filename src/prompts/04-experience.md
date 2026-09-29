```text
Select and order the candidate's work experience for this resume. Use only the supplied experience records. Job requirements describe the employer's needs and are not evidence about the candidate. Select the most relevant roles and order them by relevance, using chronology to resolve ties. Within each selected role, choose the strongest relevant source bullets and order them by relevance. Use bullet-level skills, archetypes, and strength only as selection and ordering metadata. Include no more than three bullets per role.

Keep every selected bullet grounded in its source facts, scope, technologies, responsibilities, and metrics. Rewrite only when that meaningfully improves relevance or impact. Do not add claims, tools, responsibilities, outcomes, metrics, or causal links. If the source has no quantitative measure, retain a concrete verifiable result or scope. Preserve company, role, location, and dates accurately. Format dates as mmm yyyy or Present, with -- between start and end dates. Omit roles that add no useful information.

<requirements_json>
{{REQUIREMENTS_JSON}}
</requirements_json>

<section_data>
{{SECTION_DATA}}
</section_data>

Return one JSON object with an entries array. Each entry must contain company, dates, role, location, and bullets, where bullets is an array of at least one, but no more than three strings. Example:
{"entries":[{"company":"Company","dates":"mmm yyyy -- Present","role":"Role","location":"City, ST","bullets":["Accomplishment grounded in the source"]}]}

Return an empty entries array if no roles apply. Return strict JSON only, with no Markdown fences, explanation, or extra keys. All values must be content data; do not generate document markup or formatting syntax.
```
