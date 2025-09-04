# JIRA Tools Usage Guide

## Installation & Setup

```bash
# Install system-wide (requires sudo)
sudo ./install.sh

# Configuration - choose one:
# System-wide: edit /etc/jira-tools.env
# Per-user: create ~/.jira.env

# Required environment variables:
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_api_token
JIRA_PROJECT_KEY=GIQ  # optional default project
```

## Issue Management

### Create Issues
```bash
# Basic story
jira create "Implement user authentication"

# With description and priority
jira create "Fix login bug" -d "Users can't login on mobile" -p High

# From file
jira create "New feature" -f requirements.txt -t Story -a user@company.com

# Bug with assignee
jira create "API returns 500" -t Bug -p Critical -a dev@company.com

# Subtask under parent
jira create "Write tests" --parent GIQ-123 -t Sub-task

# Epic
jira create "User Management Epic" -t Epic

# With labels
jira create "Performance issue" -l performance backend urgent
```

### Update Issues
```bash
# Update description
jira update GIQ-123 -d "Updated requirements"

# Update from file
jira update GIQ-123 -f new-description.md

# Change priority and assignee
jira update GIQ-123 -p High -a newowner@company.com

# Update summary
jira update GIQ-123 -s "New ticket title"

# Add labels
jira update GIQ-123 -l frontend bug critical
```

### View Issues
```bash
# Get issue details
jira get GIQ-123

# Get as JSON
jira get GIQ-123 --json
```

## Search & Query

### Search Issues
```bash
# Basic JQL search
jira search "project = GIQ AND status = 'To Do'"

# Complex query
jira search "assignee = currentUser() AND status != Done"

# Limit results
jira search "project = GIQ" -m 10

# JSON output
jira search "priority = High" --json
```

### Quick Queries
```bash
# My assigned issues
jira my-issues

# Specific user's issues
jira my-issues -e user@company.com

# Recent updates (last 7 days)
jira recent

# Recent in specific project (last 14 days)
jira recent -p GIQ -d 14
```

## Workflow Operations

### Status Transitions
```bash
# Move to In Progress
jira transition GIQ-123 "In Progress"

# Move to Done
jira transition GIQ-123 "Done"

# Common statuses: "To Do", "In Progress", "In Review", "Done"
```

### Assignments
```bash
# Assign to user
jira assign GIQ-123 user@company.com

# Assign to yourself (use your email from config)
jira assign GIQ-123 your.email@company.com
```

### Issue Linking
```bash
# Link as related
jira link GIQ-123 GIQ-124

# Link with specific type
jira link GIQ-123 GIQ-124 -t "Blocks"

# Link to epic
jira link GIQ-123 GIQ-100 --epic

# Common link types: "Relates", "Blocks", "Clones", "Duplicates"
```

## Comments & Attachments

### Comments
```bash
# Add comment
jira comment GIQ-123 "This is working now"

# Comment from file
jira comment GIQ-123 -f status-update.md
```

### Attachments
```bash
# Add attachment
jira attach GIQ-123 screenshot.png

# Add document
jira attach GIQ-123 requirements.pdf
```

## Project Information

### Get Project Details
```bash
# Project info
jira info

# Specific project
jira info -p GIQ

# Available priorities
jira info --priorities

# Available statuses
jira info --statuses

# Available issue types
jira info --types

# For specific project
jira info -p GIQ --statuses --types
```

## Common Workflows

### Bug Workflow
```bash
# 1. Create bug
jira create "Login fails on mobile" -t Bug -p High -a dev@company.com

# 2. Developer takes ownership
jira transition GIQ-456 "In Progress"

# 3. Add investigation notes
jira comment GIQ-456 "Issue is in authentication module"

# 4. Link related issues
jira link GIQ-456 GIQ-123 -t "Relates"

# 5. Mark as fixed
jira transition GIQ-456 "Done"
```

### Epic Management
```bash
# 1. Create epic
jira create "User Authentication Epic" -t Epic

# 2. Create stories under epic
jira create "Login page" --parent GIQ-100
jira create "Password reset" --parent GIQ-100

# 3. Link existing issues to epic
jira link GIQ-123 GIQ-100 --epic
```

### Daily Standup Prep
```bash
# My current work
jira my-issues

# Recent activity
jira recent -d 1

# High priority items
jira search "assignee = currentUser() AND priority = High"
```

## Issue Types
- **Story**: User stories and features
- **Bug**: Defects and issues
- **Task**: General work items  
- **Epic**: Large features spanning multiple stories
- **Sub-task**: Work items under parent issues

## Priorities
- **Highest**: Critical/blocking issues
- **High**: Important items
- **Medium**: Normal priority (default)
- **Low**: Nice to have
- **Lowest**: Future considerations

## Common JQL Examples
```bash
# My open work
jira search "assignee = currentUser() AND status != Done"

# Team's work
jira search "project = GIQ AND status = 'In Progress'"

# Recent bugs
jira search "type = Bug AND created >= -7d"

# High priority unassigned
jira search "priority = High AND assignee is EMPTY"

# Epic progress
jira search "parent = GIQ-100"

# Recently updated by others
jira search "updated >= -1d AND updatedBy != currentUser()"
```

## Tips & Best Practices

1. **Always use quotes** for multi-word arguments:
   ```bash
   jira create "Multi word title" -d "Multi word description"
   ```

2. **Use files for long content**:
   ```bash
   jira create "Story title" -f requirements.md
   jira comment GIQ-123 -f status-update.md
   ```

3. **Check available options** before using:
   ```bash
   jira info --types --priorities --statuses
   ```

4. **Use JQL for complex searches**:
   ```bash
   jira search "project = GIQ AND fixVersion = '1.2.0'"
   ```

5. **JSON output for integration**:
   ```bash
   jira get GIQ-123 --json | jq '.fields.status.name'
   ```

## Configuration Files

### System-wide: `/etc/jira-tools.env`
```bash
JIRA_URL=https://company.atlassian.net
JIRA_EMAIL=team@company.com
JIRA_API_TOKEN=system_token
JIRA_PROJECT_KEY=MAIN
```

### Per-user: `~/.jira.env`
```bash
JIRA_URL=https://company.atlassian.net  
JIRA_EMAIL=john.doe@company.com
JIRA_API_TOKEN=personal_token
JIRA_PROJECT_KEY=GIQ
```

## Troubleshooting

- **Command not found**: Ensure `/usr/local/bin` is in PATH
- **Authentication errors**: Check API token and email in config
- **Permission errors**: Verify JIRA project access
- **Status transitions fail**: Check available transitions with `jira info --statuses`
- **Verbose output**: Add `-v` flag for detailed error messages

## Python API Integration
```python
from jira_client import JiraClient

client = JiraClient()
issue = client.create_issue("Title", "Description", priority="High")
print(f"Created: {issue['key']}")
```