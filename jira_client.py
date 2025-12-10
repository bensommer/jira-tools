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
import re
from markdown_it import MarkdownIt

# Load environment variables from multiple possible locations
load_dotenv()  # Load from .env in current directory
load_dotenv(Path.home() / '.jira.env')  # Load from user home directory
load_dotenv('/etc/jira-tools.env')  # Load from system-wide config

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
        
        # Clean URL - remove trailing slash if present
        if url and url.endswith('/'):
            url = url.rstrip('/')
            
        # Validate URL format
        if url and not (url.startswith('http://') or url.startswith('https://')):
            raise ValueError(f"JIRA_URL must start with http:// or https://, got: {url}")
        
        if not all([url, email, api_token]):
            missing = []
            if not url: missing.append('JIRA_URL')
            if not email: missing.append('JIRA_EMAIL')
            if not api_token: missing.append('JIRA_API_TOKEN')
            
            # Provide helpful configuration guidance
            config_locations = [
                "Current directory: .env",
                "User home: ~/.jira.env",
                "System-wide: /etc/jira-tools.env"
            ]
            
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Configuration can be set in:\n" +
                "\n".join([f"  - {loc}" for loc in config_locations])
            )
        
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
            'Content-Type': 'application/json',
            'X-Atlassian-Token': 'no-check'  # Required for some operations
        })
        self.base_url = f"{self.config.url}/rest/api/3"
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to JIRA API"""
        url = f"{self.base_url}/{endpoint}"
        logger.debug(f"{method} {url}")
        
        # Add timeout if not specified
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30
            
        response = self.session.request(method, url, **kwargs)
        
        if response.status_code >= 400:
            error_details = ""
            try:
                error_json = response.json()
                if 'errorMessages' in error_json:
                    error_details = "; ".join(error_json['errorMessages'])
                elif 'errors' in error_json:
                    error_details = "; ".join([f"{k}: {v}" for k, v in error_json['errors'].items()])
            except:
                error_details = response.text[:200]  # Limit error text length
                
            error_msg = f"API Error {response.status_code}: {error_details}"
            logger.error(error_msg)
            
            # Provide more specific error messages for common issues
            if response.status_code == 401:
                logger.error("Authentication failed. Check your API token and email.")
            elif response.status_code == 403:
                logger.error("Permission denied. Check your JIRA permissions.")
            elif response.status_code == 404:
                logger.error(f"Resource not found: {endpoint}")
                
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
        
        # Add priority - some JIRA configurations allow priority on all issue types
        if priority:
            try:
                fields["priority"] = {"name": priority}
            except:
                # If priority fails, continue without it
                logger.warning(f"Could not set priority {priority} for issue type {issue_type}")
        
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
            "maxResults": min(max_results, 1000),  # JIRA has limits
            "startAt": 0
        }
        
        if fields:
            params["fields"] = ','.join(fields)
        else:
            # Include essential fields by default
            params["fields"] = "summary,status,priority,assignee,reporter,issuetype,created,updated,labels,parent"
        
        try:
            # Use the new search/jql endpoint
            response = self._make_request("GET", "search/jql", params=params)
            data = response.json()
            if isinstance(data, dict):
                issues = data.get('issues', [])
                total = data.get('total', len(issues))
                if total > len(issues):
                    logger.info(f"Retrieved {len(issues)} of {total} total issues")
                return issues
            return []
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def transition_issue(self, issue_key: str, status: str) -> bool:
        """Transition issue to a new status"""
        logger.info(f"Transitioning {issue_key} to {status}")
        
        try:
            transitions_response = self._make_request("GET", f"issue/{issue_key}/transitions")
            transitions = transitions_response.json().get('transitions', [])
            
            transition_id = None
            # Try exact match first
            for transition in transitions:
                if transition['to']['name'].lower() == status.lower():
                    transition_id = transition['id']
                    break
            
            # Try partial match if exact match fails
            if not transition_id:
                for transition in transitions:
                    if status.lower() in transition['to']['name'].lower():
                        transition_id = transition['id']
                        logger.info(f"Using partial match: '{transition['to']['name']}'")
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
        except Exception as e:
            logger.error(f"Failed to transition issue: {e}")
            return False
    
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
        
        try:
            # Try new format first
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
        except Exception as e:
            logger.error(f"Failed to link issues: {e}")
            # Try alternative linking approach
            try:
                response = self._make_request(
                    "POST",
                    "issueLink",
                    json={
                        "linkType": {"name": link_type},
                        "fromIssueKey": inward_issue,
                        "toIssueKey": outward_issue
                    }
                )
                return response.status_code in [200, 201]
            except Exception as e2:
                logger.error(f"Alternative linking also failed: {e2}")
                return False
    
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
        try:
            # Try project-specific statuses first
            response = self._make_request("GET", f"project/{key}/statuses")
            return response.json()
        except:
            # Fallback to global statuses
            try:
                response = self._make_request("GET", "status")
                return response.json()
            except Exception as e:
                logger.error(f"Could not get statuses: {e}")
                return []
    
    def _get_user_account_id(self, email: str) -> Optional[str]:
        """Get user account ID from email"""
        try:
            # Try the newer user/search endpoint first
            response = self._make_request("GET", "user/search", params={"query": email, "maxResults": 1})
            users = response.json()
            
            if users and len(users) > 0:
                return users[0]['accountId']
            
            # Fallback: try user lookup by email directly
            try:
                response = self._make_request("GET", "user", params={"expand": "groups,applicationRoles", "accountId": email})
                user = response.json()
                return user.get('accountId')
            except:
                pass
                
            # Final fallback: try user picker search
            try:
                response = self._make_request("GET", "user/picker", params={"query": email, "maxResults": 1})
                data = response.json()
                users = data.get('users', [])
                if users:
                    return users[0]['accountId']
            except:
                pass
            
            logger.warning(f"User not found: {email}")
            return None
        except Exception as e:
            logger.error(f"Error finding user {email}: {e}")
            return None
    
    def _convert_to_adf(self, text: str) -> Dict:
        """Convert markdown to Atlassian Document Format using markdown-it-py"""
        if not text:
            return {
                "type": "doc",
                "version": 1,
                "content": []
            }

        # Initialize markdown parser with common extensions
        md = MarkdownIt("commonmark", {"typographer": True})
        md.enable(['table', 'strikethrough'])

        # Parse markdown to tokens
        tokens = md.parse(text)

        # Convert tokens to ADF
        adf_content = self._tokens_to_adf(tokens)

        return {
            "type": "doc",
            "version": 1,
            "content": adf_content
        }

    def _tokens_to_adf(self, tokens: List, level: int = 0) -> List[Dict]:
        """Recursively convert markdown-it tokens to ADF nodes"""
        adf_nodes = []
        i = 0

        while i < len(tokens):
            token = tokens[i]

            # Heading
            if token.type == 'heading_open':
                level_num = int(token.tag[1])  # h1 -> 1, h2 -> 2, etc.
                i += 1  # Move to inline token
                inline_content = self._process_inline(tokens[i]) if i < len(tokens) else []
                adf_nodes.append({
                    "type": "heading",
                    "attrs": {"level": level_num},
                    "content": inline_content
                })
                i += 2  # Skip inline and heading_close

            # Paragraph
            elif token.type == 'paragraph_open':
                i += 1  # Move to inline token
                inline_content = self._process_inline(tokens[i]) if i < len(tokens) else []
                if inline_content:  # Only add non-empty paragraphs
                    adf_nodes.append({
                        "type": "paragraph",
                        "content": inline_content
                    })
                i += 2  # Skip inline and paragraph_close

            # Bullet list
            elif token.type == 'bullet_list_open':
                i += 1
                list_items = []
                while i < len(tokens) and tokens[i].type != 'bullet_list_close':
                    if tokens[i].type == 'list_item_open':
                        i += 1
                        # Collect token range for this list item
                        item_start = i
                        while i < len(tokens) and tokens[i].type != 'list_item_close':
                            i += 1
                        item_end = i
                        # Process all tokens in this list item
                        item_content = self._tokens_to_adf(tokens[item_start:item_end], level + 1)

                        # Note: Task lists (checkboxes) are kept as regular lists with checkbox text
                        # JIRA's API doesn't reliably support taskItem/taskList ADF nodes
                        list_items.append({
                            "type": "listItem",
                            "content": item_content
                        })
                        i += 1  # Skip list_item_close
                    else:
                        i += 1

                adf_nodes.append({
                    "type": "bulletList",
                    "content": list_items
                })
                i += 1  # Skip bullet_list_close

            # Ordered list
            elif token.type == 'ordered_list_open':
                i += 1
                list_items = []
                while i < len(tokens) and tokens[i].type != 'ordered_list_close':
                    if tokens[i].type == 'list_item_open':
                        i += 1
                        # Collect token range for this list item
                        item_start = i
                        while i < len(tokens) and tokens[i].type != 'list_item_close':
                            i += 1
                        item_end = i
                        # Process all tokens in this list item
                        item_content = self._tokens_to_adf(tokens[item_start:item_end], level + 1)
                        list_items.append({
                            "type": "listItem",
                            "content": item_content
                        })
                        i += 1  # Skip list_item_close
                    else:
                        i += 1
                adf_nodes.append({
                    "type": "orderedList",
                    "content": list_items
                })
                i += 1  # Skip ordered_list_close

            # Code block
            elif token.type == 'fence' or token.type == 'code_block':
                code_block = {
                    "type": "codeBlock",
                    "content": [{"type": "text", "text": token.content.rstrip('\n')}]
                }
                if token.info:  # Language specified
                    code_block["attrs"] = {"language": token.info.strip()}
                adf_nodes.append(code_block)
                i += 1

            # Blockquote
            elif token.type == 'blockquote_open':
                i += 1
                quote_content = []
                while i < len(tokens) and tokens[i].type != 'blockquote_close':
                    quote_nodes = self._tokens_to_adf([tokens[i]], level + 1)
                    quote_content.extend(quote_nodes)
                    i += 1
                adf_nodes.append({
                    "type": "blockquote",
                    "content": quote_content
                })
                i += 1  # Skip blockquote_close

            # Horizontal rule
            elif token.type == 'hr':
                adf_nodes.append({"type": "rule"})
                i += 1

            # Table
            elif token.type == 'table_open':
                i += 1
                table_rows = []
                is_header_row = True

                while i < len(tokens) and tokens[i].type != 'table_close':
                    if tokens[i].type == 'thead_open' or tokens[i].type == 'tbody_open':
                        i += 1
                        continue
                    elif tokens[i].type == 'thead_close' or tokens[i].type == 'tbody_close':
                        if tokens[i].type == 'thead_close':
                            is_header_row = False
                        i += 1
                        continue
                    elif tokens[i].type == 'tr_open':
                        i += 1
                        cells = []
                        while i < len(tokens) and tokens[i].type != 'tr_close':
                            if tokens[i].type in ['th_open', 'td_open']:
                                i += 1
                                cell_content = []
                                if i < len(tokens) and tokens[i].type == 'inline':
                                    cell_inline = self._process_inline(tokens[i])
                                    if cell_inline:
                                        cell_content = [{
                                            "type": "paragraph",
                                            "content": cell_inline
                                        }]
                                    i += 1

                                cell_type = "tableHeader" if is_header_row else "tableCell"
                                cells.append({
                                    "type": cell_type,
                                    "content": cell_content if cell_content else []
                                })
                                i += 1  # Skip th_close or td_close
                            else:
                                i += 1

                        if cells:
                            table_rows.append({
                                "type": "tableRow",
                                "content": cells
                            })
                        i += 1  # Skip tr_close
                    else:
                        i += 1

                if table_rows:
                    adf_nodes.append({
                        "type": "table",
                        "content": table_rows
                    })
                i += 1  # Skip table_close

            # HTML block or inline HTML (ignore for ADF)
            elif token.type in ['html_block', 'html_inline']:
                i += 1

            else:
                i += 1

        return adf_nodes

    def _process_inline(self, token) -> List[Dict]:
        """Process inline tokens to ADF text nodes with marks"""
        if not token or token.type != 'inline' or not token.children:
            return []

        adf_content = []
        current_text = ""
        current_marks = []

        for child in token.children:
            if child.type == 'text':
                if current_marks:
                    # Flush any accumulated text with marks
                    if current_text:
                        adf_content.append({
                            "type": "text",
                            "text": current_text,
                            "marks": current_marks.copy()
                        })
                        current_text = ""
                    # Add new text with current marks
                    adf_content.append({
                        "type": "text",
                        "text": child.content,
                        "marks": current_marks.copy()
                    })
                else:
                    # No marks, just accumulate text
                    current_text += child.content

            elif child.type == 'code_inline':
                # Flush any accumulated plain text
                if current_text:
                    adf_content.append({"type": "text", "text": current_text})
                    current_text = ""
                # Add code with mark
                adf_content.append({
                    "type": "text",
                    "text": child.content,
                    "marks": [{"type": "code"}]
                })

            elif child.type == 'strong_open':
                # Flush any accumulated plain text
                if current_text:
                    adf_content.append({"type": "text", "text": current_text})
                    current_text = ""
                current_marks.append({"type": "strong"})

            elif child.type == 'strong_close':
                current_marks = [m for m in current_marks if m.get('type') != 'strong']

            elif child.type == 'em_open':
                if current_text:
                    adf_content.append({"type": "text", "text": current_text})
                    current_text = ""
                current_marks.append({"type": "em"})

            elif child.type == 'em_close':
                current_marks = [m for m in current_marks if m.get('type') != 'em']

            elif child.type == 's_open':  # Strikethrough
                if current_text:
                    adf_content.append({"type": "text", "text": current_text})
                    current_text = ""
                current_marks.append({"type": "strike"})

            elif child.type == 's_close':
                current_marks = [m for m in current_marks if m.get('type') != 'strike']

            elif child.type == 'link_open':
                if current_text:
                    adf_content.append({"type": "text", "text": current_text})
                    current_text = ""
                # Get the href attribute
                href = None
                for attr in child.attrs:
                    if attr[0] == 'href':
                        href = attr[1]
                        break
                if href:
                    current_marks.append({"type": "link", "attrs": {"href": href}})

            elif child.type == 'link_close':
                current_marks = [m for m in current_marks if m.get('type') != 'link']

            elif child.type == 'image':
                # Flush any accumulated text
                if current_text:
                    adf_content.append({"type": "text", "text": current_text})
                    current_text = ""

                # Extract image attributes
                src = None
                alt = child.content or ""
                title = None

                for attr in child.attrs:
                    if attr[0] == 'src':
                        src = attr[1]
                    elif attr[0] == 'title':
                        title = attr[1]

                if src:
                    # ADF media node structure
                    media_node = {
                        "type": "mediaGroup",
                        "content": [{
                            "type": "media",
                            "attrs": {
                                "type": "external",
                                "url": src,
                                "alt": alt
                            }
                        }]
                    }
                    # Images need to be at block level, not inline
                    # For now, add as text placeholder
                    adf_content.append({
                        "type": "text",
                        "text": f"[Image: {alt or src}]"
                    })

            elif child.type == 'softbreak':
                current_text += '\n'

            elif child.type == 'hardbreak':
                if current_text:
                    adf_content.append({"type": "text", "text": current_text})
                    current_text = ""
                adf_content.append({"type": "hardBreak"})

        # Flush any remaining text
        if current_text:
            adf_content.append({"type": "text", "text": current_text})

        return adf_content
    
    def create_epic(self, summary: str, description: str = "", **kwargs) -> Dict:
        """Create an Epic"""
        return self.create_issue(summary, description, issue_type="Epic", **kwargs)
    
    def link_to_epic(self, story_key: str, epic_key: str) -> bool:
        """Link a story to an epic"""
        logger.info(f"Linking {story_key} to epic {epic_key}")
        try:
            # Try updating parent field first
            success = self.update_issue(story_key, custom_fields={"parent": {"key": epic_key}})
            if success:
                return True
        except:
            pass
            
        # Fallback: use Epic Link custom field (common field name)
        try:
            # Get project to find Epic Link field
            response = self._make_request("GET", f"issue/{story_key}/editmeta")
            meta = response.json()
            
            epic_link_field = None
            for field_id, field_info in meta.get('fields', {}).items():
                if field_info.get('name', '').lower() in ['epic link', 'epic name']:
                    epic_link_field = field_id
                    break
            
            if epic_link_field:
                return self.update_issue(story_key, custom_fields={epic_link_field: epic_key})
        except Exception as e:
            logger.error(f"Failed to link to epic: {e}")
            
        return False
    
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