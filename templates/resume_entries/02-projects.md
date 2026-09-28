## Schemas

Use these templates when adding a project record. Replace placeholders with supported facts; omit optional project links when they are unavailable. The `---` lines delimit valid YAML frontmatter.

### Project: `resume_data/projects/<project-slug>.md`

```markdown
---
id: unique-project-slug
title: "Project Name"
role: "Role / Context" # e.g., Personal Project, Open Source Contributor
url: "https://github.com/..." # optional
demo: "https://..." # optional
start_date: "YYYY-MM"
end_date: "YYYY-MM" # or "Present"
skills:
  - Skill1
  - Skill2
bullets:
  - id: proj-b1
    text: "Action verb + context + quantifiable impact."
    skills: [Skill1, Skill2]
    archetypes: [fullstack, machine-learning, cloud]
    strength: 5 # integer from 1 to 5; 5 = essential hero bullet
    metric: "Quantifiable metric summary"
---
```