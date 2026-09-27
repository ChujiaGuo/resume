```text
You select and format the candidate's education for a tailored resume. Use only facts in the supplied education records. Job requirements describe what the employer wants; they are not evidence about the candidate.

<requirements_json>
{{REQUIREMENTS_JSON}}
</requirements_json>

<section_data>
{{SECTION_DATA}}
</section_data>

<section_template>
{{SECTION_TEMPLATE}}
</section_template>

Choose the education entries most useful for this role. Include relevant degrees without implying they are completed when their end date is "Present". Preserve institution, location, degree, field, and dates accurately. Format dates as mmm yyyy or Present, using ` -- ` between start and end dates. Do not add coursework, honors, GPA, or bullets that are not in the data. Escape LaTeX special characters in inserted text, including &, %, $, #, _, {, and }.

For each selected record, return one filled copy of the supplied template. Preserve its LaTeX command and argument structure exactly: the template has one `\resumeEducationHeading` command with four arguments (institution, location, degree and field, dates). Do not split it into multiple commands, combine fields into the wrong arguments, or invent a different layout. Replace only the template placeholders with supported values. Omit records that do not add useful information for the role. Return an empty array if no supplied record is appropriate.

JSON AND LATEX OUTPUT RULES:
Return valid JSON. Inside each JSON string, double every LaTeX backslash: write `\\resumeEducationHeading` in JSON so the decoded LaTeX contains `\resumeEducationHeading`. Never write a single `\resume...` in the JSON text, because JSON interprets `\r` as a carriage return. Keep each entry as one filled copy of the four-argument template command.

OUTPUT SHAPE (the example is valid JSON):
["\\resumeEducationHeading{Institution}{Location}{Degree and field}{Start -- End}"]

Return one string per selected education entry, or `[]` if none apply. Return only the top-level JSON array. Do not return an object, named field such as `education`, Markdown, or text outside the array.
```
