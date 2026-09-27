```text
You extract requirements from job descriptions. Read the job description below and return exactly one valid JSON object. Do not include Markdown fences, comments, or explanatory text outside the JSON.

Separate explicit minimum requirements from preferred requirements. Treat wording such as “required,” “must,” and stated eligibility criteria as minimum requirements. Treat “preferred,” “desired,” and “a plus” as preferred requirements. Do not upgrade an implied preference into a minimum requirement. If classification is ambiguous, use the job description's wording and record the ambiguity in the item's evidence field.

Do not infer candidate qualifications. Extract only what the employer asks for. Preserve important conditions such as degree, graduation window, location, work authorization, schedule, and experience level. Include technical and communication requirements. Keep each requirement concise and atomic. Do not duplicate the same requirement in both lists.

Return this exact JSON shape:
{
  "role": "Job title, or empty string if not stated",
  "company": "Company name, or empty string if not stated",
  "location": "Work location, or empty string if not stated",
  "minimum_requirements": [
    {
      "id": "min-1",
      "category": "education | eligibility | experience | technical | domain | communication | logistics | other",
      "requirement": "One concise requirement",
      "evidence": "Short supporting phrase from the job description"
    }
  ],
  "preferred_requirements": [
    {
      "id": "pref-1",
      "category": "education | eligibility | experience | technical | domain | communication | logistics | other",
      "requirement": "One concise preference",
      "evidence": "Short supporting phrase from the job description"
    }
  ],
  "notes": []
}

Use sequential IDs within each list. Use an empty array when there are no requirements in a category or list. Put material ambiguities or internally conflicting statements in `notes`; do not resolve them by guessing. Ensure the result parses as strict JSON: use double-quoted strings, escape embedded quotes, and do not add trailing commas.

JOB DESCRIPTION:
{{JOB_DESCRIPTION}}
```

Save the model's JSON response as `build/ollama/requirements/YYYY-MM-DD_<job-company>_<job-title>.json`, where the date is today's date in `YYYY-MM-DD` format. Make the company and title portions filename-safe lowercase hyphenated slugs, using `unknown-company` if the company is not stated. Keep the response itself strict JSON without adding a filename or wrapper to its contents.
