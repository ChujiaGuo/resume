```text
You tailor the candidate's Technical Skills section to the job requirements using only skills explicitly listed in the supplied skills inventory. Requirements describe the employer's needs; they do not prove that the candidate has a skill. Do not infer proficiency, add synonyms that imply unlisted tools, or add skills from project or experience records.

<requirements_json>
{{REQUIREMENTS_JSON}}
</requirements_json>

<section_data>
{{SECTION_DATA}}
</section_data>

<section_template>
{{SECTION_TEMPLATE}}
</section_template>

Fill the supplied complete Skills section template. Preserve its section heading, list structure, macros, and category labels exactly. Replace only the category contents with selected skills; do not rebuild the section using a different LaTeX structure. Select and order listed skills by relevance to the role, while keeping the four existing categories: Languages, Frameworks, Developer Tools, and Libraries. Place skills only in the category where the inventory lists them. Keep names accurate. Remove a category line if it has no selected skills, and remove its trailing line break as needed so the LaTeX remains valid. If no listed skill is useful, return an empty array.

Escape LaTeX special characters in inserted text, including &, %, $, #, _, {, and }.

JSON AND LATEX OUTPUT RULES:
Return valid JSON. Inside the JSON string, double every LaTeX backslash, for example `\\section` and `\\begin`. Fill the supplied template while preserving its exact commands and nesting. In particular, preserve `\\small{\\item{...}}`; do not turn `\\small` into a `\\begin{small}` environment, and do not add square brackets or braces. Escape LaTeX text characters as `\\&`, `\\%`, `\\#`, `\\_`, `\\$`, `\\{`, and `\\}`. Do not output HTML entities such as `&amp;`.

OUTPUT SHAPE (the example is valid JSON; return the actual complete filled section):
["\\section{Technical Skills} ..."]

When skills are selected, return exactly one string containing the complete filled Skills section. If no listed skill is useful, return `[]`. Return only the top-level JSON array. Do not return an object, named field such as `skills`, Markdown, or text outside the array.
```
