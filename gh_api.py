"""
GitHub API integration for team membership verification using PyGithub.

This module provides functions to interact with the GitHub API to verify
team memberships and retrieve team information.
"""
import os
import logging
from urllib.parse import urlparse
from github import Github, GithubException, UnknownObjectException

logger = logging.getLogger(__name__)

def get_github_client():
    """Get a GitHub client using the API token from environment variables."""
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        logger.warning("GITHUB_TOKEN environment variable not set")
        return None
    
    # Log the token length for debugging (without exposing the actual token)
    logger.info(f"GitHub token length: {len(token)}")
    
    try:
        logger.info("Initializing GitHub client...")
        client = Github(token)
        
        # Test the connection by getting the authenticated user
        user = client.get_user().login
        logger.info(f"Successfully authenticated as: {user}")
        
        return client
    except GithubException as e:
        logger.error(f"Failed to initialize GitHub client: {e}")
        # Check if it's an authentication error
        if hasattr(e, 'status') and e.status == 401:
            logger.error("Authentication error. Please check if your token is valid and has not expired.")
        return None

def parse_team_url(team_url):
    """
    Parse a GitHub team URL into organization and team slug components.
    
    Example:
    https://github.com/orgs/my-org/teams/my-team => ('my-org', 'my-team')
    """
    if not team_url:
        return None, None
    
    try:
        parts = urlparse(team_url).path.strip('/').split('/')
        if len(parts) >= 4 and parts[0] == 'orgs' and parts[2] == 'teams':
            return parts[1], parts[3]  # org, team
        elif len(parts) == 2:
            return parts[0], parts[1]
    except Exception as e:
        logger.error(f"Error parsing team URL: {e}")
    
    logger.error(f"Invalid GitHub team URL format: {team_url}")
    return None, None

def get_team_info(org_name, team_slug):
    """Get information about a GitHub team."""
    client = get_github_client()
    if not client:
        return None
    
    try:
        org = client.get_organization(org_name)
        # Try to find the team by slug
        for team in org.get_teams():
            if team.slug == team_slug:
                return {
                    'id': team.id,
                    'name': team.name,
                    'slug': team.slug,
                    'description': team.description,
                    'privacy': team.privacy,
                    'url': team.url
                }
        
        logger.error(f"Team {team_slug} not found in organization {org_name}")
        return None
    except GithubException as e:
        logger.error(f"Failed to get team info: {e}")
        return None

def list_teams(org_name):
    """List all teams in an organization."""
    client = get_github_client()
    if not client:
        return []
    
    try:
        org = client.get_organization(org_name)
        teams = []
        for team in org.get_teams():
            teams.append({
                'id': team.id,
                'name': team.name,
                'slug': team.slug,
                'description': team.description,
                'privacy': team.privacy
            })
        return teams
    except GithubException as e:
        logger.error(f"Failed to list teams: {e}")
        return []

def list_team_members(org_name, team_slug):
    """List all members of a GitHub team."""

    
    client = get_github_client()
    if not client:
        logger.error("Failed to get GitHub client. Check if GITHUB_TOKEN is set properly.")
        return []
    
    try:
        # Try to determine if org_name is a team itself
        if '/' in org_name:
            parts = org_name.split('/')
            if len(parts) == 2:
                org_name, team_slug = parts
                logger.info(f"Split input into org_name={org_name}, team_slug={team_slug}")
        
        logger.info(f"Attempting to get organization: {org_name}")
        org = client.get_organization(org_name)
        
        # Find the team by slug
        logger.info(f"Looking for team with slug: {team_slug}")
        target_team = None
        for team in org.get_teams():
            logger.info(f"Found team: {team.name} (slug: {team.slug})")
            if team.slug == team_slug:
                target_team = team
                break
        
        if not target_team:
            logger.error(f"Team {team_slug} not found in organization {org_name}")
            return []
        
        # Get team members
        members = []
        for member in target_team.get_members():
            members.append({
                'login': member.login,
                'id': member.id,
                'name': member.name,
                'email': member.email,
                'avatar_url': member.avatar_url,
                'url': member.url
            })
        logger.info(f"Found {len(members)} members in team {org_name}/{team_slug}")
        
        
        return members
    except GithubException as e:
        logger.error(f"Failed to list team members: {e}")
        return []
