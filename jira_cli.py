#!/usr/bin/env python3
"""
JIRA CLI - Command line interface for JIRA operations
"""
import argparse
import json
import sys
from typing import Optional
from pathlib import Path
from jira_client import JiraClient, JiraConfig
import logging
from tabulate import tabulate
from datetime import datetime

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class JiraCLI:
    """Command line interface for JIRA operations"""
    
    def __init__(self):
        self.client = JiraClient()
        
    def create(self, args):
        """Create a new issue"""
        description = args.description
        if args.description_file:
            with open(args.description_file, 'r') as f:
                description = f.read()
        
        result = self.client.create_issue(
            summary=args.summary,
            description=description or "",
            issue_type=args.type,
            priority=args.priority,
            assignee_email=args.assignee,
            parent_key=args.parent,
            labels=args.labels
        )
        
        print(f"✅ Created issue: {result['key']}")
        print(f"🔗 URL: {self.client.config.url}/browse/{result['key']}")
        return result['key']
    
    def update(self, args):
        """Update an existing issue"""
        description = None
        if args.description:
            description = args.description
        elif args.description_file:
            with open(args.description_file, 'r') as f:
                description = f.read()
        
        success = self.client.update_issue(
            issue_key=args.key,
            summary=args.summary,
            description=description,
            priority=args.priority,
            assignee_email=args.assignee,
            labels=args.labels
        )
        
        if success:
            print(f"✅ Updated issue: {args.key}")
            print(f"🔗 URL: {self.client.config.url}/browse/{args.key}")
        else:
            print(f"❌ Failed to update issue: {args.key}")
            sys.exit(1)
    
    def get(self, args):
        """Fetch and display issue details"""
        issue = self.client.get_issue(args.key, expand=['renderedFields'])
        fields = issue['fields']
        
        print("\n" + "=" * 60)
        print(f"🎫 TICKET: {args.key}")
        print("=" * 60)
        
        details = [
            ["Type", fields['issuetype']['name']],
            ["Status", fields['status']['name']],
            ["Priority", (fields.get('priority') or {}).get('name', 'None')],
            ["Assignee", (fields.get('assignee') or {}).get('displayName', 'Unassigned')],
            ["Reporter", (fields.get('reporter') or {}).get('displayName', 'Unknown')],
            ["Created", self._format_date(fields.get('created'))],
            ["Updated", self._format_date(fields.get('updated'))],
        ]
        
        if fields.get('parent'):
            details.append(["Parent", f"{fields['parent']['key']} - {fields['parent']['fields']['summary']}"])
        
        if fields.get('labels'):
            details.append(["Labels", ', '.join(fields['labels'])])
        
        print(tabulate(details, tablefmt='simple'))
        
        print("\n📋 SUMMARY")
        print("-" * 40)
        print(fields['summary'])
        
        if 'renderedFields' in issue and issue['renderedFields'].get('description'):
            print("\n📄 DESCRIPTION")
            print("-" * 40)
            print(issue['renderedFields']['description'])
        elif fields.get('description'):
            print("\n📄 DESCRIPTION")
            print("-" * 40)
            print(self._render_adf(fields['description']))
        
        if fields.get('subtasks'):
            print("\n📝 SUBTASKS")
            print("-" * 40)
            for subtask in fields['subtasks']:
                status = subtask['fields']['status']['name']
                print(f"  • {subtask['key']}: {subtask['fields']['summary']} [{status}]")
        
        if args.json:
            print("\n📊 JSON OUTPUT")
            print("-" * 40)
            print(json.dumps(issue, indent=2))
        
        print("\n🔗 URL: " + self.client.config.url + "/browse/" + args.key)
    
    def search(self, args):
        """Search issues using JQL"""
        issues = self.client.search_issues(args.jql, max_results=args.max_results)
        
        if not issues:
            print("No issues found")
            return
        
        if args.json:
            print(json.dumps(issues, indent=2))
        else:
            table_data = []
            for issue in issues:
                fields = issue['fields']
                assignee = fields.get('assignee') or {}
                priority = fields.get('priority') or {}
                table_data.append([
                    issue['key'],
                    fields['issuetype']['name'][:10],
                    fields['status']['name'][:15],
                    priority.get('name', 'None')[:6],
                    assignee.get('displayName', 'Unassigned')[:20],
                    fields['summary'][:50] + ('...' if len(fields['summary']) > 50 else '')
                ])
            
            headers = ['Key', 'Type', 'Status', 'Priority', 'Assignee', 'Summary']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
            print(f"\nFound {len(issues)} issues")
    
    def transition(self, args):
        """Change issue status"""
        success = self.client.transition_issue(args.key, args.status)
        
        if success:
            print(f"✅ Transitioned {args.key} to {args.status}")
            print(f"🔗 URL: {self.client.config.url}/browse/{args.key}")
        else:
            print(f"❌ Failed to transition {args.key}")
            sys.exit(1)
    
    def assign(self, args):
        """Assign issue to user"""
        success = self.client.assign_issue(args.key, args.email)
        
        if success:
            print(f"✅ Assigned {args.key} to {args.email}")
            print(f"🔗 URL: {self.client.config.url}/browse/{args.key}")
        else:
            print(f"❌ Failed to assign {args.key}")
            sys.exit(1)
    
    def link(self, args):
        """Link two issues"""
        if args.epic:
            success = self.client.link_to_epic(args.from_key, args.to_key)
            link_type = "epic"
        else:
            success = self.client.link_issues(args.from_key, args.to_key, args.type)
            link_type = args.type
        
        if success:
            print(f"✅ Linked {args.from_key} to {args.to_key} ({link_type})")
        else:
            print(f"❌ Failed to link issues")
            sys.exit(1)
    
    def comment(self, args):
        """Add comment to issue"""
        comment_text = args.comment
        if args.comment_file:
            with open(args.comment_file, 'r') as f:
                comment_text = f.read()
        
        result = self.client.add_comment(args.key, comment_text)
        print(f"✅ Added comment to {args.key}")
        print(f"🔗 URL: {self.client.config.url}/browse/{args.key}")
    
    def attach(self, args):
        """Add attachment to issue"""
        result = self.client.add_attachment(args.key, args.file)
        print(f"✅ Added attachment to {args.key}")
        print(f"🔗 URL: {self.client.config.url}/browse/{args.key}")
    
    def my_issues(self, args):
        """Get my assigned issues"""
        issues = self.client.get_user_issues(args.email)
        
        if not issues:
            print("No issues assigned")
            return
        
        table_data = []
        for issue in issues:
            fields = issue['fields']
            priority = fields.get('priority') or {}
            table_data.append([
                issue['key'],
                fields['status']['name'][:15],
                priority.get('name', 'None')[:6],
                self._format_date(fields.get('updated'))[:10],
                fields['summary'][:60] + ('...' if len(fields['summary']) > 60 else '')
            ])
        
        headers = ['Key', 'Status', 'Priority', 'Updated', 'Summary']
        print(f"\n📋 Issues assigned to {args.email or 'me'}:\n")
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        print(f"\nTotal: {len(issues)} issues")
    
    def recent(self, args):
        """Get recently updated issues"""
        issues = self.client.get_recent_issues(args.days, args.project)
        
        if not issues:
            print("No recent issues found")
            return
        
        table_data = []
        for issue in issues:
            fields = issue['fields']
            assignee = fields.get('assignee') or {}
            table_data.append([
                issue['key'],
                fields['issuetype']['name'][:10],
                fields['status']['name'][:15],
                assignee.get('displayName', 'Unassigned')[:20],
                self._format_date(fields.get('updated'))[:16],
                fields['summary'][:50] + ('...' if len(fields['summary']) > 50 else '')
            ])
        
        headers = ['Key', 'Type', 'Status', 'Assignee', 'Updated', 'Summary']
        print(f"\n📅 Issues updated in last {args.days} days:\n")
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        print(f"\nTotal: {len(issues)} issues")
    
    def info(self, args):
        """Get project information"""
        if args.priorities:
            priorities = self.client.get_priorities()
            print("\n📊 Available Priorities:")
            for p in priorities:
                print(f"  • {p['name']}")
        
        if args.statuses:
            statuses = self.client.get_statuses(args.project)
            print(f"\n📊 Available Statuses for {args.project or 'default project'}:")
            for status_group in statuses:
                print(f"\n  {status_group['name']}:")
                for s in status_group.get('statuses', []):
                    print(f"    • {s['name']}")
        
        if args.types:
            types = self.client.get_issue_types(args.project)
            print(f"\n📊 Available Issue Types for {args.project or 'default project'}:")
            for t in types:
                print(f"  • {t['name']}")
        
        if not any([args.priorities, args.statuses, args.types]):
            project = self.client.get_project_info(args.project)
            print(f"\n📁 Project: {project['key']} - {project['name']}")
            print(f"Description: {project.get('description', 'No description')}")
            print(f"Lead: {project.get('lead', {}).get('displayName', 'Unknown')}")
    
    def _format_date(self, date_str: Optional[str]) -> str:
        """Format ISO date string to readable format"""
        if not date_str:
            return "N/A"
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        except:
            return date_str[:19] if len(date_str) >= 19 else date_str
    
    def _render_adf(self, adf_content):
        """Simple rendering of ADF content to text"""
        if not adf_content or not isinstance(adf_content, dict):
            return "No content"
        
        result = []
        for content in adf_content.get('content', []):
            if content['type'] == 'paragraph':
                para_text = []
                for item in content.get('content', []):
                    if item['type'] == 'text':
                        para_text.append(item.get('text', ''))
                result.append(' '.join(para_text))
            elif content['type'] == 'heading':
                level = content.get('attrs', {}).get('level', 1)
                heading_text = []
                for item in content.get('content', []):
                    if item['type'] == 'text':
                        heading_text.append(item.get('text', ''))
                result.append('#' * level + ' ' + ' '.join(heading_text))
            elif content['type'] == 'bulletList':
                for item in content.get('content', []):
                    if item['type'] == 'listItem':
                        for para in item.get('content', []):
                            if para['type'] == 'paragraph':
                                item_text = []
                                for text in para.get('content', []):
                                    if text['type'] == 'text':
                                        item_text.append(text.get('text', ''))
                                result.append('• ' + ' '.join(item_text))
        
        return '\n'.join(result) if result else "No content"


def main():
    parser = argparse.ArgumentParser(description='JIRA CLI Tool')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new issue')
    create_parser.add_argument('summary', help='Issue summary')
    create_parser.add_argument('-d', '--description', help='Issue description')
    create_parser.add_argument('-f', '--description-file', help='Read description from file')
    create_parser.add_argument('-t', '--type', default='Story', help='Issue type (default: Story)')
    create_parser.add_argument('-p', '--priority', default='Medium', help='Priority (default: Medium)')
    create_parser.add_argument('-a', '--assignee', help='Assignee email')
    create_parser.add_argument('--parent', help='Parent issue key (for subtasks/epics)')
    create_parser.add_argument('-l', '--labels', nargs='+', help='Labels to add')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update an existing issue')
    update_parser.add_argument('key', help='Issue key')
    update_parser.add_argument('-s', '--summary', help='New summary')
    update_parser.add_argument('-d', '--description', help='New description')
    update_parser.add_argument('-f', '--description-file', help='Read description from file')
    update_parser.add_argument('-p', '--priority', help='New priority')
    update_parser.add_argument('-a', '--assignee', help='New assignee email')
    update_parser.add_argument('-l', '--labels', nargs='+', help='New labels')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get issue details')
    get_parser.add_argument('key', help='Issue key')
    get_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search issues with JQL')
    search_parser.add_argument('jql', help='JQL query')
    search_parser.add_argument('-m', '--max-results', type=int, default=50, help='Max results')
    search_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Transition command
    transition_parser = subparsers.add_parser('transition', help='Change issue status')
    transition_parser.add_argument('key', help='Issue key')
    transition_parser.add_argument('status', help='New status')
    
    # Assign command
    assign_parser = subparsers.add_parser('assign', help='Assign issue to user')
    assign_parser.add_argument('key', help='Issue key')
    assign_parser.add_argument('email', help='Assignee email')
    
    # Link command
    link_parser = subparsers.add_parser('link', help='Link two issues')
    link_parser.add_argument('from_key', help='Source issue key')
    link_parser.add_argument('to_key', help='Target issue key')
    link_parser.add_argument('-t', '--type', default='Relates', help='Link type (default: Relates)')
    link_parser.add_argument('--epic', action='store_true', help='Link as epic child')
    
    # Comment command
    comment_parser = subparsers.add_parser('comment', help='Add comment to issue')
    comment_parser.add_argument('key', help='Issue key')
    comment_parser.add_argument('comment', nargs='?', help='Comment text')
    comment_parser.add_argument('-f', '--comment-file', help='Read comment from file')
    
    # Attach command
    attach_parser = subparsers.add_parser('attach', help='Add attachment to issue')
    attach_parser.add_argument('key', help='Issue key')
    attach_parser.add_argument('file', help='File to attach')
    
    # My issues command
    my_parser = subparsers.add_parser('my-issues', help='Get my assigned issues')
    my_parser.add_argument('-e', '--email', help='User email (default: from config)')
    
    # Recent command
    recent_parser = subparsers.add_parser('recent', help='Get recently updated issues')
    recent_parser.add_argument('-d', '--days', type=int, default=7, help='Days back (default: 7)')
    recent_parser.add_argument('-p', '--project', help='Project key')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Get project/system information')
    info_parser.add_argument('-p', '--project', help='Project key')
    info_parser.add_argument('--priorities', action='store_true', help='Show priorities')
    info_parser.add_argument('--statuses', action='store_true', help='Show statuses')
    info_parser.add_argument('--types', action='store_true', help='Show issue types')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        cli = JiraCLI()
        
        if args.command == 'create':
            cli.create(args)
        elif args.command == 'update':
            cli.update(args)
        elif args.command == 'get':
            cli.get(args)
        elif args.command == 'search':
            cli.search(args)
        elif args.command == 'transition':
            cli.transition(args)
        elif args.command == 'assign':
            cli.assign(args)
        elif args.command == 'link':
            cli.link(args)
        elif args.command == 'comment':
            cli.comment(args)
        elif args.command == 'attach':
            cli.attach(args)
        elif args.command == 'my-issues':
            cli.my_issues(args)
        elif args.command == 'recent':
            cli.recent(args)
        elif args.command == 'info':
            cli.info(args)
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()