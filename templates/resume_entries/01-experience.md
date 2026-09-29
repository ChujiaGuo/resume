## Schemas

Use this template when adding an experience entry. Replace placeholders with supported facts; omit optional project links when they are unavailable. The `---` lines delimit valid YAML frontmatter.

### Experience: `resume_data/experience/<company-role-slug>.md`

```markdown
---
id: unique-experience-slug
company: "Company Name"
role: "Job Title"
location: "City, ST"
start_date: "YYYY-MM"
end_date: "YYYY-MM" # or "Present"
skills:
  - Skill1
  - Skill2
bullets:
  - id: exp-b1
    text: "Action verb + context + quantifiable impact."
    skills: [Skill1, Skill2]
    archetypes: [backend, distributed-systems, devops]
    strength: 5 # integer from 1 to 5; 5 = essential hero bullet
    metric: "Quantifiable metric summary"
---
```