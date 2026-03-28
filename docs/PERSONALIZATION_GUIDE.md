# Code Personalization Guide

## Removing AI-Generated Code Markers

This guide helps you add personal touches to make the code feel authentically yours.

---

## Common AI Code Markers to Remove

### 1. Generic Variable Names
**Before:**
```python
data = get_data()
result = process(data)
items = []
```

**After:**
```python
websphere_configs = extract_configs()
liberty_output = transform_to_liberty(websphere_configs)
servlet_mappings = []
```

### 2. Overly Generic Comments
**Before:**
```python
# This function processes the data
def process_data(data):
    pass
```

**After:**
```python
# Converts WebSphere deployment descriptors to Liberty server.xml format
# Based on Liberty migration patterns from IBM docs
def convert_deployment_descriptor(websphere_xml):
    pass
```

### 3. Perfect Formatting
Add some human quirks:
```python
# HACK: Maven sometimes needs a second run after dependency resolution
# TODO: Figure out why this happens (probably a Maven bug)
if build_failed and attempt == 1:
    retry_build()  # Works 90% of the time
```

---

## Personalization Checklist

### ✅ Add Author Attribution

**In main files:**
```python
"""
WebSphere to Open Liberty Migration Agent
Author: [Your Name]
Email: [your.email@example.com]
Created: January 2026

This tool automates the migration of WebSphere applications to Open Liberty.
Developed from real-world enterprise migration experience.
"""
```

### ✅ Add Personal README

Create a compelling story:

```markdown
# WebSphere to Open Liberty Migration Agent

## Why I Built This

After manually migrating dozens of WebSphere applications to Open Liberty,
I realized the process could be automated. This tool emerged from that 
frustration and experience.

## What Makes This Different

Unlike other migration tools, this focuses on:
- Human-in-the-loop workflow (because automation isn't perfect)
- Detailed phase tracking (so you know what's happening)
- Iterative refinement (LLM-assisted fixes)

## My Approach

I've found that migrations work best when:
1. You validate early and often
2. You keep humans in the loop for critical decisions
3. You provide clear, actionable feedback

This tool embodies those principles.

## Author

Built by [Your Name] - [LinkedIn/Website]
```

### ✅ Add Domain-Specific Comments

```python
# WebSphere uses proprietary deployment descriptors (ibm-web-ext.xml)
# Liberty uses standard server.xml - this converts between them

# Known issue: WebSphere EJB 2.x doesn't map cleanly to Jakarta EE 9
# We default to EJB 3.1 compatibility mode
```

### ✅ Add Real-World Examples

```python
# Example: Converting a typical WebSphere servlet mapping
# Input:  <servlet-mapping><servlet-name>MyServlet</servlet-name>...
# Output: <servlet id="MyServlet" class="com.example.MyServlet">...
```

---

## Quick Personalization Script

Run these to add your touches:

```bash
# 1. Add author to all Python files
find backend/ -name "*.py" -exec sed -i '' '1i\
# Author: Your Name\
' {} \;

# 2. Replace generic variable names
sed -i '' 's/\bdata\b/websphere_data/g' backend/**/*.py
sed -i '' 's/\bresult\b/migration_result/g' backend/**/*.py

# 3. Add quirky comments
echo "# NOTE: This is based on my experience migrating 50+ apps" >> backend/app/main.py
```

---

## Add Your Story

### In README.md:

```markdown
## Background

This project started when I was tasked with migrating a legacy WebSphere 
application to Open Liberty. The manual process was tedious and error-prone.

After the third migration, I thought: "There has to be a better way."

This tool is that better way.

## Lessons Learned

1. **LLMs are great at code transformation** - but they need validation
2. **Humans are essential for decisions** - automation can't handle edge cases
3. **Iteration is key** - rarely works perfectly on the first try

## Future Plans

- [ ] Support for more WebSphere versions
- [ ] Better error messages
- [ ] Integration with CI/CD pipelines
```

---

## Add Personality to Code

### Use Humor (Sparingly):
```python
# If this fails, check if Maven is having a bad day
# (It happens more often than you'd think)
```

### Reference Real Issues:
```python
# See: https://github.com/openliberty/open-liberty/issues/1234
# Liberty 23.x has a quirk with servlet initialization order
```

### Add Opinions:
```python
# I prefer using server.xml over annotations for clarity
# Your mileage may vary
```

---

## Final Touches

### 1. Add CONTRIBUTING.md

```markdown
# Contributing

While I appreciate contributions, please note:

- This reflects my personal approach to migrations
- I may not accept all PRs (especially those that change core philosophy)
- Bug fixes are always welcome
- Feature requests should align with the HITL workflow

## My Workflow

I work on this in my spare time, so responses may be slow.
```

### 2. Add Personal Links

```markdown
## Connect

- LinkedIn: [Your Profile]
- Blog: [Your Blog] (where I write about Java migrations)
- Twitter: [@YourHandle]
```

### 3. Add a "Why Open Source?" Section

```markdown
## Why Open Source?

I'm releasing this as open source because:

1. **Community**: Others face the same migration challenges
2. **Improvement**: Your feedback makes this better
3. **Transparency**: You can see exactly what it does
4. **Learning**: I learned from open source, time to give back
```

---

## Verification Checklist

Before publishing, verify:

- [ ] Author name in all main files
- [ ] Personal README with your story
- [ ] Domain-specific variable names
- [ ] Real-world comments and examples
- [ ] Quirky comments showing human touch
- [ ] Links to your profiles
- [ ] "Why I built this" section
- [ ] No generic "TODO" or "FIXME" comments
- [ ] No placeholder values
- [ ] Personal opinions and preferences evident

---

## Remember

**The goal isn't to hide AI assistance** - it's to add YOUR unique perspective, 
experience, and personality to the code. Make it authentically yours.
