# JIRA Tools Quick Reference

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with JIRA credentials
```

## Common Operations

### Create Issues
```bash
# Story
python jira_cli.py create "Title" -d "Description" -p High -a user@email.com

# Bug
python jira_cli.py create "Bug title" -t Bug -p Critical

# Subtask
python jira_cli.py create "Subtask" --parent GIQ-123

# Epic
python jira_cli.py create "Epic title" -t Epic
```

### Update Issues
```bash
# Update description
python jira_cli.py update GIQ-123 -d "New description"

# Update from file
python jira_cli.py update GIQ-123 -f description.md

# Change priority/assignee
python jira_cli.py update GIQ-123 -p High -a user@email.com
```

### Query Issues
```bash
# Get issue
python jira_cli.py get GIQ-123

# Search
python jira_cli.py search "project = GIQ AND status = 'To Do'"

# My issues
python jira_cli.py my-issues

# Recent updates
python jira_cli.py recent -d 7
```

### Workflow
```bash
# Change status
python jira_cli.py transition GIQ-123 "In Progress"

# Assign
python jira_cli.py assign GIQ-123 user@email.com

# Link to epic
python jira_cli.py link GIQ-123 GIQ-100 --epic

# Add comment
python jira_cli.py comment GIQ-123 "Comment text"
```

## Python API
```python
from jira_client import JiraClient

client = JiraClient()

# Create
issue = client.create_issue("Title", "Description", priority="High")

# Update
client.update_issue("GIQ-123", description="New desc")

# Transition
client.transition_issue("GIQ-123", "Done")

# Search
issues = client.search_issues("assignee = currentUser()")
```

## Environment Variables
Required in `.env`:
- `JIRA_URL` - Atlassian URL
- `JIRA_EMAIL` - User email  
- `JIRA_API_TOKEN` - API token (not password)
- `JIRA_PROJECT_KEY` - Default project (optional)

## Issue Types
- Story
- Bug
- Task
- Epic
- Sub-task

## Priorities
- Highest, High, Medium, Low, Lowest

## Common Statuses
- To Do
- In Progress
- In Review
- Done