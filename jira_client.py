"""
JIRA Client - Robust Python implementation for JIRA operations
"""
import os
import json
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import logging
from functools import wraps
import time

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def retry_on_failure(max_retries=3, delay=1):
    """Decorator to retry failed API calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator


@dataclass
class JiraConfig:
    """Configuration for JIRA connection"""
    url: str
    email: str
    api_token: str
    project_key: str
    
    @classmethod
    def from_env(cls) -> 'JiraConfig':
        """Load configuration from environment variables"""
        url = os.getenv('JIRA_URL')
        email = os.getenv('JIRA_EMAIL')
        api_token = os.getenv('JIRA_API_TOKEN')
        project_key = os.getenv('JIRA_PROJECT_KEY', 'GIQ')
        
        if not all([url, email, api_token]):
            missing = []
            if not url: missing.append('JIRA_URL')
            if not email: missing.append('JIRA_EMAIL')
            if not api_token: missing.append('JIRA_API_TOKEN')
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return cls(url=url, email=email, api_token=api_token, project_key=project_key)


class JiraClient:
    """Main JIRA client for API operations"""
    
    def __init__(self, config: Optional[JiraConfig] = None):
        """Initialize JIRA client with configuration"""
        self.config = config or JiraConfig.from_env()
        self.session = requests.Session()
        self.session.auth = (self.config.email, self.config.api_token)
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        self.base_url = f"{self.config.url}/rest/api/3"
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to JIRA API"""
        url = f"{self.base_url}/{endpoint}"
        logger.debug(f"{method} {url}")
        
        response = self.session.request(method, url, **kwargs)
        
        if response.status_code >= 400:
            error_msg = f"API Error {response.status_code}: {response.text}"
            logger.error(error_msg)
            response.raise_for_status()
            
        return response
    
    @retry_on_failure(max_retries=3)
    def create_issue(self, 
                    summary: str, 
                    description: str = "",
                    issue_type: str = "Story",
                    priority: Optional[str] = "Medium",
                    assignee_email: Optional[str] = None,
                    parent_key: Optional[str] = None,
                    labels: Optional[List[str]] = None,
                    custom_fields: Optional[Dict] = None) -> Dict:
        """Create a new JIRA issue"""
        logger.info(f"Creating issue: {summary}")
        
        fields = {
            "project": {"key": self.config.project_key},
            "summary": summary,
            "description": self._convert_to_adf(description),
            "issuetype": {"name": issue_type}
        }
        
        # Only add priority for non-Epic types
        if priority and issue_type.lower() != 'epic':
            fields["priority"] = {"name": priority}
        
        if assignee_email:
            account_id = self._get_user_account_id(assignee_email)
            if account_id:
                fields["assignee"] = {"accountId": account_id}
        
        if parent_key:
            fields["parent"] = {"key": parent_key}
            
        if labels:
            fields["labels"] = labels
            
        if custom_fields:
            fields.update(custom_fields)
        
        response = self._make_request("POST", "issue", json={"fields": fields})
        result = response.json()
        
        logger.info(f"✅ Created issue: {result['key']}")
        return result
    
    def update_issue(self, 
                    issue_key: str,
                    summary: Optional[str] = None,
                    description: Optional[str] = None,
                    priority: Optional[str] = None,
                    assignee_email: Optional[str] = None,
                    labels: Optional[List[str]] = None,
                    custom_fields: Optional[Dict] = None) -> bool:
        """Update an existing JIRA issue"""
        logger.info(f"Updating issue: {issue_key}")
        
        fields = {}
        
        if summary:
            fields["summary"] = summary
        
        if description:
            fields["description"] = self._convert_to_adf(description)
        
        if priority:
            fields["priority"] = {"name": priority}
        
        if assignee_email:
            account_id = self._get_user_account_id(assignee_email)
            if account_id:
                fields["assignee"] = {"accountId": account_id}
        
        if labels is not None:
            fields["labels"] = labels
            
        if custom_fields:
            fields.update(custom_fields)
        
        if not fields:
            logger.warning("No fields to update")
            return False
        
        response = self._make_request("PUT", f"issue/{issue_key}", json={"fields": fields})
        
        logger.info(f"✅ Updated issue: {issue_key}")
        return response.status_code in [200, 204]
    
    def get_issue(self, issue_key: str, expand: Optional[List[str]] = None) -> Dict:
        """Fetch issue details"""
        logger.info(f"Fetching issue: {issue_key}")
        
        params = {}
        if expand:
            params['expand'] = ','.join(expand)
        
        response = self._make_request("GET", f"issue/{issue_key}", params=params)
        return response.json()
    
    def search_issues(self, jql: str, max_results: int = 50, fields: Optional[List[str]] = None) -> List[Dict]:
        """Search issues using JQL"""
        logger.info(f"Searching issues with JQL: {jql}")
        
        params = {
            "jql": jql,
            "maxResults": max_results
        }
        
        if fields:
            params["fields"] = ','.join(fields)
        
        response = self._make_request("GET", "search", params=params)
        data = response.json()
        if isinstance(data, dict):
            return data.get('issues', [])
        return []
    
    def transition_issue(self, issue_key: str, status: str) -> bool:
        """Transition issue to a new status"""
        logger.info(f"Transitioning {issue_key} to {status}")
        
        transitions_response = self._make_request("GET", f"issue/{issue_key}/transitions")
        transitions = transitions_response.json().get('transitions', [])
        
        transition_id = None
        for transition in transitions:
            if transition['to']['name'].lower() == status.lower():
                transition_id = transition['id']
                break
        
        if not transition_id:
            available = [t['to']['name'] for t in transitions]
            logger.error(f"Status '{status}' not available. Available: {available}")
            return False
        
        response = self._make_request(
            "POST", 
            f"issue/{issue_key}/transitions",
            json={"transition": {"id": transition_id}}
        )
        
        logger.info(f"✅ Transitioned {issue_key} to {status}")
        return response.status_code in [200, 204]
    
    def assign_issue(self, issue_key: str, assignee_email: str) -> bool:
        """Assign issue to a user"""
        logger.info(f"Assigning {issue_key} to {assignee_email}")
        
        account_id = self._get_user_account_id(assignee_email)
        if not account_id:
            logger.error(f"Could not find user: {assignee_email}")
            return False
        
        response = self._make_request(
            "PUT",
            f"issue/{issue_key}/assignee",
            json={"accountId": account_id}
        )
        
        logger.info(f"✅ Assigned {issue_key} to {assignee_email}")
        return response.status_code in [200, 204]
    
    def link_issues(self, inward_issue: str, outward_issue: str, link_type: str = "Relates") -> bool:
        """Link two issues together"""
        logger.info(f"Linking {inward_issue} to {outward_issue} with type {link_type}")
        
        response = self._make_request(
            "POST",
            "issueLink",
            json={
                "type": {"name": link_type},
                "inwardIssue": {"key": inward_issue},
                "outwardIssue": {"key": outward_issue}
            }
        )
        
        logger.info(f"✅ Linked {inward_issue} to {outward_issue}")
        return response.status_code in [200, 201]
    
    def add_comment(self, issue_key: str, comment: str) -> Dict:
        """Add a comment to an issue"""
        logger.info(f"Adding comment to {issue_key}")
        
        response = self._make_request(
            "POST",
            f"issue/{issue_key}/comment",
            json={"body": self._convert_to_adf(comment)}
        )
        
        logger.info(f"✅ Added comment to {issue_key}")
        return response.json()
    
    def add_attachment(self, issue_key: str, file_path: str) -> Dict:
        """Add attachment to an issue"""
        logger.info(f"Adding attachment to {issue_key}: {file_path}")
        
        with open(file_path, 'rb') as f:
            files = {'file': (Path(file_path).name, f)}
            
            temp_headers = self.session.headers.copy()
            del temp_headers['Content-Type']
            
            response = self.session.post(
                f"{self.base_url}/issue/{issue_key}/attachments",
                files=files,
                headers={'X-Atlassian-Token': 'no-check'}
            )
        
        response.raise_for_status()
        logger.info(f"✅ Added attachment to {issue_key}")
        return response.json()
    
    def get_project_info(self, project_key: Optional[str] = None) -> Dict:
        """Get project information"""
        key = project_key or self.config.project_key
        logger.info(f"Getting project info for {key}")
        
        response = self._make_request("GET", f"project/{key}")
        return response.json()
    
    def get_issue_types(self, project_key: Optional[str] = None) -> List[Dict]:
        """Get available issue types for project"""
        key = project_key or self.config.project_key
        project = self.get_project_info(key)
        return project.get('issueTypes', [])
    
    def get_priorities(self) -> List[Dict]:
        """Get available priorities"""
        response = self._make_request("GET", "priority")
        return response.json()
    
    def get_statuses(self, project_key: Optional[str] = None) -> List[Dict]:
        """Get available statuses for project"""
        key = project_key or self.config.project_key
        response = self._make_request("GET", f"project/{key}/statuses")
        return response.json()
    
    def _get_user_account_id(self, email: str) -> Optional[str]:
        """Get user account ID from email"""
        try:
            response = self._make_request("GET", "user/search", params={"query": email})
            users = response.json()
            
            if users:
                return users[0]['accountId']
            
            logger.warning(f"User not found: {email}")
            return None
        except Exception as e:
            logger.error(f"Error finding user {email}: {e}")
            return None
    
    def _convert_to_adf(self, text: str) -> Dict:
        """Convert plain text or markdown to Atlassian Document Format"""
        if not text:
            return {
                "type": "doc",
                "version": 1,
                "content": []
            }
        
        content = []
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            
            if paragraph.startswith('#'):
                level = len(paragraph) - len(paragraph.lstrip('#'))
                text_content = paragraph.lstrip('#').strip()
                content.append({
                    "type": "heading",
                    "attrs": {"level": min(level, 6)},
                    "content": [{"type": "text", "text": text_content}]
                })
            elif paragraph.startswith('- ') or paragraph.startswith('* '):
                list_items = []
                for line in paragraph.split('\n'):
                    if line.startswith('- ') or line.startswith('* '):
                        item_text = line[2:].strip()
                        list_items.append({
                            "type": "listItem",
                            "content": [{
                                "type": "paragraph",
                                "content": [{"type": "text", "text": item_text}]
                            }]
                        })
                if list_items:
                    content.append({
                        "type": "bulletList",
                        "content": list_items
                    })
            elif paragraph.startswith('```'):
                lines = paragraph.split('\n')
                code_lines = []
                in_code = False
                for line in lines:
                    if line.startswith('```'):
                        in_code = not in_code
                    elif in_code:
                        code_lines.append(line)
                if code_lines:
                    content.append({
                        "type": "codeBlock",
                        "content": [{"type": "text", "text": '\n'.join(code_lines)}]
                    })
            else:
                content.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": paragraph.strip()}]
                })
        
        return {
            "type": "doc",
            "version": 1,
            "content": content
        }
    
    def create_epic(self, summary: str, description: str = "", **kwargs) -> Dict:
        """Create an Epic"""
        return self.create_issue(summary, description, issue_type="Epic", **kwargs)
    
    def link_to_epic(self, story_key: str, epic_key: str) -> bool:
        """Link a story to an epic"""
        logger.info(f"Linking {story_key} to epic {epic_key}")
        return self.update_issue(story_key, custom_fields={"parent": {"key": epic_key}})
    
    def bulk_create_issues(self, issues: List[Dict]) -> List[Dict]:
        """Create multiple issues in bulk"""
        results = []
        for issue_data in issues:
            try:
                result = self.create_issue(**issue_data)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to create issue: {e}")
                results.append({"error": str(e), "data": issue_data})
        return results
    
    def get_issue_changelog(self, issue_key: str) -> List[Dict]:
        """Get changelog/history for an issue"""
        response = self._make_request("GET", f"issue/{issue_key}", params={"expand": "changelog"})
        data = response.json()
        return data.get('changelog', {}).get('histories', [])
    
    def get_user_issues(self, assignee_email: Optional[str] = None) -> List[Dict]:
        """Get issues assigned to a user"""
        email = assignee_email or self.config.email
        jql = f"assignee = '{email}' ORDER BY updated DESC"
        return self.search_issues(jql)
    
    def get_recent_issues(self, days: int = 7, project_key: Optional[str] = None) -> List[Dict]:
        """Get recently updated issues"""
        key = project_key or self.config.project_key
        jql = f"project = {key} AND updated >= -{days}d ORDER BY updated DESC"
        return self.search_issues(jql)