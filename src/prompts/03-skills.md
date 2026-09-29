```text
Select and rank the candidate's skills from the supplied skills inventory that are relevant to the target role. Use only skills explicitly listed in the inventory.

Guidelines:
1. Priority Sorting: Within each category, place exact or near-exact matches to the job posting's technical requirements first.
2. High-Signal Complementary Skills: After the directly mentioned requirements, include relevant industry-standard developer tools, frameworks, libraries, and foundational languages from the inventory that support a software engineering role (e.g., cloud platforms, containerization, version control, API design).
3. Exclusions: Exclude skills from the inventory that are irrelevant to general software engineering or overly niche/introductory unless explicitly requested.
4. Categories: Preserve each selected skill's exact name and map it to its corresponding inventory category (Languages, Frameworks, Developer Tools, Libraries).
5. Output format: Return empty arrays for categories with no relevant skills.

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