#!/usr/bin/env python3
"""
Module 1: Basic MCP Server - Starter Code
TODO: Implement tools for analyzing git changes and suggesting PR templates
"""
import os
import json
import subprocess
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Change to INFO for less verbosity
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# Initialize the FastMCP server
mcp = FastMCP("pr-agent")

# PR template directory (shared across all modules)
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
DEFAULT_TEMPLATES= {
    "bug.md":"Bug Fix",
    "feature.md":"Feature",
    "docs.md":"Documentation",
    "refactor.md":"Refactor",
    "test.md":"Test",
    "performance.md":"Performance",
    "security.md":"Security"
}


# TODO: Implement tool functions here
# Example structure for a tool:
# @mcp.tool()
# async def analyze_file_changes(base_branch: str = "main", include_diff: bool = True) -> str:
#     """Get the full diff and list of changed files in the current git repository.
#     
#     Args:
#         base_branch: Base branch to compare against (default: main)
#         include_diff: Include the full diff content (default: true)
#     """
#     # Your implementation here
#     pass

# Minimal stub implementations so the server runs
# TODO: Replace these with your actual implementations

TYPE_MAPPING ={
    "bug": "bug.md",
    "fix" : "bug.md",
    "feature": "feature.md",
    "enhancment": "feature.md",
    "docs": "docs.md",
    "documentation":"docs.md",
    "refractor": "refactor.md",
    "cleanup": "refractor.md",
    "test": "test.md",
    "testing":"test.md",
    "performance": "performance.md",
    "optimization" : "performance.md",
    "security": "security.md"
}

@mcp.tool()
async def analyze_file_changes(base_branch: str = "main", include_diff: bool = True,max_diff_lines: int = 500,
                               working_directory :Optional[str]= None) -> str:
    """Get the full diff and list of changed files in the current git repository.
    
    Args:
        base_branch: Base branch to compare against (default: main)
        include_diff: Include the full diff content (default: true)
    """
    # TODO: Implement this tool
    # IMPORTANT: MCP tools have a 25,000 token response limit!
    # Large diffs can easily exceed this. Consider:
    # - Adding a max_diff_lines parameter (e.g., 500 lines)
    # - Truncating large outputs with a message
    # - Returning summary statistics alongside limited diffs
    
    # NOTE: Git commands run in the server's directory by default!
    # To run in Claude's working directory, use MCP roots:
    try:
        if working_directory is None:
            try:
                logger.info("Trying to get working_directory from MCP roots")
                context = mcp.get_context()
                roots_result = await context.session.list_roots()
                root = roots_result.roots[0]
                working_directory = root.uri.path
                logger.info(f"Found working_directory from roots: {working_directory}")
            except Exception as e:
                logger.warning(f"Could not get roots, falling back to os.getcwd(): {e}")
        
        cwd = working_directory if working_directory else os.getcwd()
        logger.info(f"Using cwd: {cwd}")

        debug_info = {
            "provided_working_directory": working_directory,
            "actual_cwd": cwd,
            "server_process_cwd": os.getcwd(),
            "server_file_location": str(Path(__file__).parent),
            "roots_check": None
        }
        try:
            logger.info("Checking roots for debug_info")
            context = mcp.get_context()
            roots_result = await context.session.list_roots()
            debug_info['roots_check'] = {
                "found": True,
                "count": len(roots_result.roots),
                "roots": [str(root.uri) for root in roots_result.roots]
            }
        except Exception as e:
            logger.warning(f"Could not check roots for debug_info: {e}")
            debug_info["roots_check"] = {
                "found": False,
                "error": str(e)
            }

        logger.info("Running git diff --name-status")
        files_result = subprocess.run(
            ["git", "diff", "--name-status", f"{base_branch}...HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd
        )
        logger.info("Running git diff --stat")
        stat_result = subprocess.run(
            ["git", "diff", "--stat", f"{base_branch}...HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd
        )
        diff_content = ""
        truncated = False
        if include_diff:
            logger.info("Running git diff for full diff")
            diff_result = subprocess.run(
                ["git", "diff", f"{base_branch}..HEAD"],
                capture_output=True,
                text=True,
                cwd=cwd
            )
            diff_lines = diff_result.stdout.split('\n')
            logger.debug(f"Total diff lines: {len(diff_lines)}")
            if len(diff_lines) > max_diff_lines:
                logger.info("Diff is too large, truncating output")
                diff_content = '\n'.join(diff_lines[:max_diff_lines])
                diff_content += f"\n\n... Output truncated. Showing {max_diff_lines} of {len(diff_lines)} lines ..."
                diff_content += "\n... Use max_diff_lines parameter to see more ..."
                truncated = True
            else:
                diff_content = diff_result.stdout

        logger.info("Running git log --oneline")
        commits_result = subprocess.run(
            ["git", "log", "--oneline", f"{base_branch}..HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd
        )
        analysis = {
            "base_branch": base_branch,
            "files_changed": files_result.stdout,
            "statistics": stat_result.stdout,
            "commits": commits_result.stdout,
            "diff": diff_content if include_diff else "Diff not included (set include_diff=true to see full diff)",
            "truncated": truncated,
            "total_diff_lines": len(diff_lines) if include_diff else 0,
            "_debug": debug_info
        }
        logger.info("Analysis complete, returning result")
        return json.dumps(analysis, indent=2)
    except subprocess.CalledProcessError as e:
        logger.error(f"Git error: {e.stderr}")
        return json.dumps({"error": f"Git error: {e.stderr}"})
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return json.dumps({"error": str(e)})
@mcp.tool()
async def get_pr_templates() -> str:
    """List available PR templates with their content."""
    # TODO: Implement this tool
    try:
        templates = [
            {
                "filename": filename,
                "type": template_type,
                "content": (TEMPLATES_DIR / filename).read_text()
            }
            for filename, template_type in DEFAULT_TEMPLATES.items()
        ]
        return json.dumps(templates, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def suggest_template(changes_summary: str, change_type: str) -> str:
    """Let Claude analyze the changes and suggest the most appropriate PR template.
    
    Args:
        changes_summary: Your analysis of what the changes do
        change_type: The type of change you've identified (bug, feature, docs, refactor, test, etc.)
    """
    # TODO: Implement this tool
    try:
        templates_response=await get_pr_templates()
        templates= json.loads(templates_response)
        template_file = TYPE_MAPPING.get(change_type.lower(),"feature.md")
        print("====================")
        print(template_file)
        print(templates)
        selected_template =next(
            (t for t in templates if t["filename"] == template_file),
            templates[0]
        )
       
        suggestion ={
            "recommended_template": selected_template,
            "reasoning": f"Based on your analysis: '{changes_summary}', this appears to be a {change_type} change.",
            "template_content": selected_template["content"],
            "usage_hint": "Claude can help you fill out this template based on the specific changes in your PR."
        }
        
        return json.dumps(suggestion,indent=2)
    
    except Exception as e:
       return json.dumps({"error": str(e)})

# Example: Simple utility tool
@mcp.tool()
async def get_repository_info(working_directory: Optional[str] = None) -> str:
    """Get basic information about the current git repository.
    
    Args:
        working_directory: Directory to run git commands in (optional)
    """
    try:
        cwd = working_directory if working_directory else os.getcwd()
        
        # Get repository name
        remote_result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=cwd
        )
        
        # Get current branch
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            cwd=cwd
        )
        
        # Get last commit info
        commit_result = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%H|%s|%an|%ad", "--date=short"],
            capture_output=True,
            text=True,
            cwd=cwd
        )
        
        info = {
            "repository_url": remote_result.stdout.strip() if remote_result.returncode == 0 else "Not available",
            "current_branch": branch_result.stdout.strip() if branch_result.returncode == 0 else "Not available",
            "last_commit": commit_result.stdout.strip() if commit_result.returncode == 0 else "Not available",
            "working_directory": cwd
        }
        
        return json.dumps(info, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

# Example: Tool with file operations
@mcp.tool()
async def create_custom_template(template_name: str, template_content: str) -> str:
    """Create a custom PR template file.
    
    Args:
        template_name: Name of the template file (e.g., 'custom.md')
        template_content: Content of the template
    """
    try:
        # Ensure template name ends with .md
        if not template_name.endswith('.md'):
            template_name += '.md'
        
        template_path = TEMPLATES_DIR / template_name
        
        # Create templates directory if it doesn't exist
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        
        # Write the template
        template_path.write_text(template_content)
        
        result = {
            "success": True,
            "template_path": str(template_path),
            "message": f"Template '{template_name}' created successfully"
        }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

# Example: Tool that processes data
@mcp.tool()
async def analyze_commit_messages(base_branch: str = "main", working_directory: Optional[str] = None) -> str:
    """Analyze commit messages to understand the types of changes made.
    
    Args:
        base_branch: Base branch to compare against (default: main)
        working_directory: Directory to run git commands in (optional)
    """
    try:
        cwd = working_directory if working_directory else os.getcwd()
        
        # Get commit messages
        commits_result = subprocess.run(
            ["git", "log", "--pretty=format:%s", f"{base_branch}..HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd
        )
        
        if commits_result.returncode != 0:
            return json.dumps({"error": "Failed to get commit messages"})
        
        commit_messages = commits_result.stdout.strip().split('\n') if commits_result.stdout.strip() else []
        
        # Analyze commit types
        commit_types = {
            "feature": 0,
            "bug": 0,
            "docs": 0,
            "refactor": 0,
            "test": 0,
            "performance": 0,
            "security": 0,
            "other": 0
        }
        
        for message in commit_messages:
            message_lower = message.lower()
            categorized = False
            
            for commit_type in commit_types.keys():
                if commit_type in message_lower:
                    commit_types[commit_type] += 1
                    categorized = True
                    break
            
            if not categorized:
                commit_types["other"] += 1
        
        # Find the most common commit type
        suggested_template = "feature"  # default
        if commit_messages:
            max_count = 0
            for commit_type, count in commit_types.items():
                if count > max_count:
                    max_count = count
                    suggested_template = commit_type
        
        analysis = {
            "total_commits": len(commit_messages),
            "commit_types": commit_types,
            "commit_messages": commit_messages,
            "suggested_template": suggested_template
        }
        
        return json.dumps(analysis, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run()
    