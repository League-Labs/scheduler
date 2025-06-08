#!/usr/bin/env python
"""
CLI tool for working with GitHub teams in the scheduler application.

Usage:
    python cli.py teams [org_name]                   List teams in an organization
    python cli.py members [org_name] [team_slug]     List members of a team
    python cli.py cache -s                           Show cache status
    python cli.py cache -i                           Invalidate cache
    python cli.py cache -r                           Refresh cache
    python cli.py team <team_name> -d                Delete all selection records for a team
    python cli.py team <team_name> -u                List all users who contributed to a team calendar
"""
import os
import sys
import logging
import click
from urllib.parse import urlparse
from dotenv import load_dotenv
from gh_api import parse_team_url, list_teams, list_team_members
from mongo import get_cache_status, invalidate_team_cache, cache_team_members



@click.group()
def cli():
    """CLI commands for scheduler application."""
    pass

@cli.command()
@click.argument('org_name', required=False)
def teams(org_name=None):
    """List teams available in the GitHub organization."""
    # If org_name is not provided, try to get it from GITHUB_TEAM env var
    if not org_name:
        org_name, team_name = parse_team_url(os.environ.get('GITHUB_TEAM', ''))
            
    if not org_name:
        click.echo("Error: Organization name required. Provide as argument or via GITHUB_TEAM env var.")
        sys.exit(1)
    
    click.echo(f"Listing teams for organization: {org_name}")
    
    teams = list_teams(org_name)
    if not teams:
        click.echo("No teams found or error occurred. Check your token permissions.")
        return
    
    click.echo(f"Found {len(teams)} teams:")
    for team in teams:
        click.echo(f"  - {team['name']} (slug: {team['slug']})")
        click.echo(f"    URL: https://github.com/orgs/{org_name}/teams/{team['slug']}")

@cli.command()
@click.argument('org_or_team', required=False)
@click.argument('team_slug', required=False)
def members(org_or_team=None, team_slug=None):
    """List members of a GitHub team.
    
    You can provide either:
    - org_name and team_slug as separate arguments
    - a single argument in the format 'org_name/team_slug'
    """
    # If input is in format "org/team"
    if org_or_team and '/' in org_or_team and not team_slug:
        parts = org_or_team.split('/')
        if len(parts) == 2:
            org_name, team_slug = parts
            click.echo(f"Parsed input as organization: {org_name}, team: {team_slug}")
        else:
            org_name = org_or_team
    else:
        org_name = org_or_team
        
    # If org_name and team_slug are not provided, try to get them from GITHUB_TEAM env var
    if not (org_name and team_slug):
          
        parsed_org, parsed_team = parse_team_url(os.environ.get('GITHUB_TEAM', ''))
     
        if org_name and team_slug:
           
            org_name = org_name or parsed_org
            team_slug = team_slug or parsed_team
    
    if not (org_name and team_slug):
        click.echo("Error: Organization name and team slug required.")
        click.echo("Provide as arguments or via GITHUB_TEAM env var.")
        click.echo("You can use either:")
        click.echo("  - python cli.py members org_name team_slug")
        click.echo("  - python cli.py members org_name/team_slug")
        sys.exit(1)
    
    click.echo(f"Listing members for team: {org_name}/{team_slug}")
    
    members = list_team_members(org_name, team_slug)
    if not members:
        click.echo("No members found or error occurred. Check your token permissions.")
        return
    
    click.echo(f"Found {len(members)} members:")
    for member in members:
        click.echo(f"  - {member['login']}")

@cli.command()
@click.option('-s', '--status', is_flag=True, help='Show cache status')
@click.option('-i', '--invalidate', is_flag=True, help='Invalidate cache')
@click.option('-r', '--refresh', is_flag=True, help='Refresh cache')
@click.option('--org', help='Organization name for specific operations')
@click.option('--team', help='Team slug for specific operations')
def cache(status, invalidate, refresh, org, team):
    """Manage GitHub team cache."""
    # If no flags are provided, show help
    if not any([status, invalidate, refresh]):
        click.echo(click.get_current_context().get_help())
        return
    
    # Handle org/team format if provided in --team
    if team and '/' in team and not org:
        parts = team.split('/')
        if len(parts) == 2:
            org, team = parts
    
    # Get org/team from GITHUB_TEAM env var if not provided
    if not org:
            org, team_from_env = parse_team_url(os.environ.get('GITHUB_TEAM', ''))
            if not team:  # Only use from env if not explicitly provided
                team = team_from_env
    
    # Show cache status
    if status:
        click.echo("Cache Status:")
        status_info = get_cache_status()
        
        if 'error' in status_info:
            click.echo(f"Error: {status_info['error']}")
            return
        
        total = status_info.get('total_cached_teams', 0)
        click.echo(f"Total cached teams: {total}")
        
        if total > 0:
            click.echo("\nCached Teams:")
            for team_info in status_info.get('teams', []):
                click.echo(f"  - {team_info['org_name']}/{team_info['team_slug']}")
                click.echo(f"    Members: {team_info['member_count']}")
                click.echo(f"    Updated: {team_info['updated_at']}")

                click.echo("")
    
    # Invalidate cache
    if invalidate:
        if org and team:
            click.echo(f"Invalidating cache for team: {org}/{team}")
            count = invalidate_team_cache(org_name=org, team_slug=team)
            click.echo(f"Invalidated {count} cache entries")
        elif org:
            click.echo(f"Invalidating cache for all teams in organization: {org}")
            count = invalidate_team_cache(org_name=org)
            click.echo(f"Invalidated {count} cache entries")
        else:
            click.echo("Invalidating all team caches")
            count = invalidate_team_cache()
            click.echo(f"Invalidated {count} cache entries")
    
    # Refresh cache
    if refresh:
        if not org:
            click.echo("Error: Organization name required for refresh. Use --org option.")
            return
        
        if not team:
            click.echo("Error: Team slug required for refresh. Use --team option.")
            return
        
        click.echo(f"Refreshing cache for team: {org}/{team}")
        members = list_team_members(org, team)
        
        if not members:
            click.echo(f"No members found for team {org}/{team}")
            return
        
        success = cache_team_members(org_name=org, team_slug=team, members=members)
        if success:
            click.echo(f"Successfully cached {len(members)} members for team {org}/{team}")
        else:
            click.echo(f"Failed to cache members for team {org}/{team}")

@cli.command()
@click.argument('team_name')
@click.option('-d', '--delete', is_flag=True, help='Delete all selection records for the team')
@click.option('-u', '--users', is_flag=True, help='List all users who have contributed to the team calendar')
def team(team_name, delete, users):
    """Manage team-related operations for dayhour selection teams.
    
    This command allows you to:
    - Delete all selection records for a team with the -d/--delete flag
    - List all users who have contributed to a team calendar with the -u/--users flag
    """
    # Import here to avoid circular imports
    load_dotenv()
    from pymongo import MongoClient
    from urllib.parse import urlparse
    
    # Connect to MongoDB
    mongo_uri = os.environ.get('MONGO_URI')
    if not mongo_uri:
        click.echo("Error: MONGO_URI environment variable not set")
        sys.exit(1)
    
    try:
        client = MongoClient(mongo_uri)
        db_name = urlparse(mongo_uri).path.strip('/') or 'scheduler'
        db = client[db_name]
    except Exception as e:
        click.echo(f"Error connecting to MongoDB: {e}")
        sys.exit(1)

    # Ensure at least one flag is provided
    if not (delete or users):
        click.echo("Error: Please specify an operation with -d/--delete or -u/--users")
        click.echo(click.get_current_context().get_help())
        sys.exit(1)
        
    # Delete all selection records for the team
    if delete:
        try:
            result = db.userteam.delete_one({"team": team_name})
            click.echo(f"Deleted {1 if result.deleted_count else 0} selection record for team '{team_name}'")
            click.echo(f"Deleted {result.deleted_count} selection records for team '{team_name}'")
        except Exception as e:
            click.echo(f"Error deleting team records: {e}")
            sys.exit(1)
    
    # List all users who have contributed to the team calendar
    if users:
        try:
            users_list = db.userteam.distinct("user_id", {"team": team_name})
            
            if not users_list:
                click.echo(f"No users have contributed to team '{team_name}'")
            else:
                click.echo(f"Users who have contributed to team '{team_name}':")
                for user in sorted(users_list):
                    click.echo(f"  - {user}")
                click.echo(f"Total: {len(users_list)} users")
        except Exception as e:
            click.echo(f"Error listing team users: {e}")
            sys.exit(1)

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Check if GITHUB_TOKEN is set
    if not os.environ.get('GITHUB_TOKEN'):
        click.echo("Warning: GITHUB_TOKEN environment variable not set.")
        click.echo("Set this variable to authenticate with GitHub API.")
    else:
        token = os.environ.get('GITHUB_TOKEN')
        masked_token = token[:4] + '*' * (len(token) - 8) + token[-4:] if len(token) > 8 else '********'
        click.echo(f"Using GitHub token: {masked_token}")
    
    cli()
