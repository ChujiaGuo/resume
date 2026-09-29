```text
Select the candidate's education records that are useful for this role. Use only facts in the supplied records. Job requirements describe the employer's needs and are not evidence about the candidate. Do not invent coursework, honors, grades, credentials, or dates. Include relevant degrees without implying completion when the source end date is Present. Preserve the institution, location, degree and field, and dates accurately. Format dates as mmm yyyy or Present, with -- between a start and end date. Omit records that add no useful information. Include ongoing education in roles that would expect current education, such as Internships and upcoming New Grad roles. Omit ongoing education for roles that expect education to be completed, such as for Early Career or existing New Grad roles.

<requirements_json>
{{REQUIREMENTS_JSON}}
</requirements_json>

<section_data>
{{SECTION_DATA}}
</section_data>

Return one JSON object with exactly this shape:
{"entries":[{"institution":"...","location":"...","degree_and_field":"...","dates":"mmm yyyy -- mmm yyyy"}]}

The entries value is an array of selected education records. Return an empty array when none apply. Return strict JSON only, with no Markdown fences, explanation, or extra keys.
```
