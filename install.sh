#!/bin/bash
# JIRA Tools System-Wide Installation Script

set -e

echo "🔧 Installing JIRA Tools System-Wide..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo "Please run as root (use sudo)"
   exit 1
fi

# Check for pip and install if needed
echo "📦 Checking Python setup..."
if ! python3 -m pip --version &>/dev/null; then
    echo "Installing pip..."
    # Try to install pip based on the system
    if command -v apt-get &>/dev/null; then
        apt-get update && apt-get install -y python3-pip
    elif command -v yum &>/dev/null; then
        yum install -y python3-pip
    elif command -v dnf &>/dev/null; then
        dnf install -y python3-pip
    elif command -v zypper &>/dev/null; then
        zypper install -y python3-pip
    else
        echo "❌ Could not install pip automatically."
        echo "Please install python3-pip manually for your system, then run this script again."
        echo ""
        echo "Common commands:"
        echo "  Ubuntu/Debian: sudo apt-get install python3-pip"
        echo "  RHEL/CentOS:   sudo yum install python3-pip"
        echo "  Fedora:        sudo dnf install python3-pip"
        echo "  SUSE:          sudo zypper install python3-pip"
        exit 1
    fi
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
python3 -m pip install --break-system-packages requests python-dotenv tabulate

# Create installation directory
echo "📁 Creating installation directory..."
mkdir -p /usr/local/lib/jira-tools

# Copy Python modules
echo "📋 Copying files..."
cp jira_client.py jira_cli.py /usr/local/lib/jira-tools/

# Create executable wrapper
echo "🔗 Creating jira command..."
cat > /usr/local/bin/jira << 'EOF'
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/usr/local/lib/jira-tools')

# Check for user config first, then system config
if os.path.exists(os.path.expanduser('~/.jira.env')):
    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser('~/.jira.env'))
elif os.path.exists('/etc/jira-tools.env'):
    from dotenv import load_dotenv
    load_dotenv('/etc/jira-tools.env')

from jira_cli import main
if __name__ == '__main__':
    main()
EOF

chmod +x /usr/local/bin/jira

# Create config template
echo "⚙️ Creating configuration template..."
if [ ! -f /etc/jira-tools.env ]; then
    cp .env.example /etc/jira-tools.env
    chmod 644 /etc/jira-tools.env
    echo ""
    echo "📝 Please edit /etc/jira-tools.env with your JIRA credentials"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Usage:"
echo "  1. Edit /etc/jira-tools.env with JIRA credentials (system-wide)"
echo "  2. Or create ~/.jira.env for personal credentials"
echo "  3. Run: jira --help"
echo ""
echo "Examples:"
echo "  jira create 'New issue' -d 'Description'"
echo "  jira get GIQ-123"
echo "  jira search 'project = GIQ'"
