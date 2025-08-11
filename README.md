# JIRA Tools - Robust Python Implementation

A comprehensive Python-based JIRA client with CLI interface for all common JIRA operations.

## Features

- ✅ Full CRUD operations for JIRA issues
- 🔐 Secure environment-based configuration
- 🔄 Retry logic for API reliability
- 📊 Rich CLI output with tables and formatting
- 🔗 Epic and issue linking
- 💬 Comments and attachments
- 🔍 JQL search support
- 📝 Markdown to Atlassian Document Format conversion

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

4. Edit `.env` with your JIRA credentials:
```
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token-here
JIRA_PROJECT_KEY=YOUR_PROJECT_KEY
```

Generate API token at: https://id.atlassian.com/manage-profile/security/api-tokens

## Usage

### CLI Commands

#### Create Issue
```bash
# Basic story creation
python jira_cli.py create "Story title" -d "Story description"

# With priority and assignee
python jira_cli.py create "Bug title" -t Bug -p High -a user@example.com

# Create subtask
python jira_cli.py create "Subtask title" --parent PROJ-123

# Create epic
python jira_cli.py create "Epic title" -t Epic

# With labels
python jira_cli.py create "Feature" -l backend api performance
```

#### Update Issue
```bash
# Update summary
python jira_cli.py update PROJ-123 -s "New summary"

# Update description from file
python jira_cli.py update PROJ-123 -f description.md

# Change priority and assignee
python jira_cli.py update PROJ-123 -p Critical -a user@example.com
```

#### Get Issue Details
```bash
# View issue
python jira_cli.py get PROJ-123

# Get as JSON
python jira_cli.py get PROJ-123 --json
```

#### Search Issues
```bash
# Search with JQL
python jira_cli.py search "project = PROJ AND status = 'In Progress'"

# Limit results
python jira_cli.py search "assignee = currentUser()" -m 10
```

#### Change Status
```bash
python jira_cli.py transition PROJ-123 "In Progress"
python jira_cli.py transition PROJ-123 "Done"
```

#### Assign Issue
```bash
python jira_cli.py assign PROJ-123 user@example.com
```

#### Link Issues
```bash
# Standard link
python jira_cli.py link PROJ-123 PROJ-124

# Link to epic
python jira_cli.py link PROJ-123 EPIC-1 --epic

# Custom link type
python jira_cli.py link PROJ-123 PROJ-124 -t "Blocks"
```

#### Add Comment
```bash
# Inline comment
python jira_cli.py comment PROJ-123 "This is a comment"

# From file
python jira_cli.py comment PROJ-123 -f comment.md
```

#### Add Attachment
```bash
python jira_cli.py attach PROJ-123 /path/to/file.pdf
```

#### View My Issues
```bash
# Your issues
python jira_cli.py my-issues

# Someone else's issues
python jira_cli.py my-issues -e other@example.com
```

#### Recent Issues
```bash
# Last 7 days (default)
python jira_cli.py recent

# Last 30 days for specific project
python jira_cli.py recent -d 30 -p PROJ
```

#### Project Information
```bash
# Project details
python jira_cli.py info -p PROJ

# List priorities
python jira_cli.py info --priorities

# List statuses
python jira_cli.py info --statuses

# List issue types
python jira_cli.py info --types
```

### Python API Usage

```python
from jira_client import JiraClient

# Initialize client (uses .env automatically)
client = JiraClient()

# Create issue
issue = client.create_issue(
    summary="New feature",
    description="Implement new feature",
    issue_type="Story",
    priority="High"
)
print(f"Created: {issue['key']}")

# Update issue
client.update_issue(
    "PROJ-123",
    description="Updated description",
    priority="Critical"
)

# Get issue
issue = client.get_issue("PROJ-123")
print(issue['fields']['summary'])

# Search issues
issues = client.search_issues("project = PROJ AND status = 'To Do'")
for issue in issues:
    print(f"{issue['key']}: {issue['fields']['summary']}")

# Transition status
client.transition_issue("PROJ-123", "In Progress")

# Link to epic
client.link_to_epic("PROJ-123", "EPIC-1")

# Add comment
client.add_comment("PROJ-123", "Working on this now")
```

## Features Comparison

| Operation | Old Shell Scripts | New Python Implementation |
|-----------|------------------|---------------------------|
| Environment Config | Hardcoded credentials | `.env` file support |
| Error Handling | Basic | Comprehensive with retries |
| Output Format | Plain text | Tables, JSON, formatted |
| Markdown Support | Limited | Full ADF conversion |
| Bulk Operations | Not supported | Supported |
| User Lookup | Hardcoded mapping | Dynamic API lookup |
| Logging | None | Configurable logging |
| Validation | None | Input validation |

## Architecture

- `jira_client.py` - Core JIRA API client with all operations
- `jira_cli.py` - Command-line interface
- `.env` - Environment configuration (not in repo)
- `requirements.txt` - Python dependencies

## Error Handling

- Automatic retry on API failures (3 attempts)
- Detailed error messages
- Validation of required fields
- Graceful handling of missing users/projects

## Security

- API tokens stored in environment variables
- No credentials in code
- `.env` file excluded from version control

## Requirements

- Python 3.7+
- JIRA Cloud account with API access
- API token (not password)

## License

MIT