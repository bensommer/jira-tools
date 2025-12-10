# Known Issues and Limitations

## Blockquotes Not Supported ⚠️

**Issue:** Blockquote markdown (`> quoted text`) fails when creating or updating JIRA issues.

**Status:** JIRA API Limitation (cannot be fixed in tool)

**Details:**
- JIRA's REST API returns `400 INVALID_INPUT` when blockquote ADF nodes are included
- This affects single-level and nested blockquotes
- Error occurs even with properly formatted ADF
- Tested on JIRA Cloud API v3

**Workaround:**
- Use bold or italic text for emphasis instead of blockquotes
- Use code blocks for quoted content
- Use horizontal rules to separate quoted sections

**Example - Won't Work:**
```markdown
> This is a quote
> with multiple lines
```

**Alternative - Will Work:**
```markdown
**Important Note:**
This is emphasized text that works.

---

Alternative formatting with horizontal rule separation.
```

**Affected Commands:**
- `jira create` with blockquotes in description
- `jira update` with blockquotes in description
- `jira comment` with blockquotes

**All other markdown features work correctly!**

---

## Other Limitations

### Images
**Status:** Not Implemented

Images display as `[Image: alt text]` placeholders. Full image support would require:
- File upload implementation
- JIRA media API integration
- Binary data handling

### Interactive Checkboxes
**Status:** JIRA API Limitation

Task lists (`- [ ]` and `- [x]`) display as text, not interactive checkboxes. JIRA's `taskItem`/`taskList` ADF nodes are not reliably supported by the API.

### Definition Lists
**Status:** No ADF Equivalent

Markdown definition lists have no equivalent in Atlassian Document Format.

### Inline HTML
**Status:** By Design (Security)

Raw HTML is stripped from markdown. ADF doesn't support inline HTML for security reasons.

---

## Test Issue

See GSDIE-4087 for comprehensive markdown stress testing showing all working features.
