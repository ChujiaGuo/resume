```text
Select the candidate's skills that are relevant to the job requirements. Use only skills explicitly listed in the supplied skills inventory. The requirements describe the employer's needs; they do not prove that the candidate has a skill. Do not infer proficiency, add synonyms that imply unlisted tools, or add skills from other records. Preserve each selected skill's name and category. Order skills within each category by relevance to this role. Return empty arrays for categories with no relevant listed skills.

<requirements_json>
{{REQUIREMENTS_JSON}}
</requirements_json>

<section_data>
{{SECTION_DATA}}
</section_data>

Return exactly one JSON object with four arrays of strings:
{"languages":["..."],"frameworks":["..."],"developer_tools":["..."],"libraries":["..."]}

Return strict JSON only, with no Markdown fences, explanation, or additional keys. Do not include skills that do not appear in the supplied inventory.
```
