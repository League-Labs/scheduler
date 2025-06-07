#!/usr/bin/env python
"""
CLI tool for working with GitHub teams in the scheduler application.

Usage:
    python cli.py teams [org_name]                   List teams in an organization
    python cli.py members [org_name] [team_slug]     List members of a team
    python cli.py cache -s                           Show cache status
    python cli.py cache -i                           Invalidate cache
    python cli.py cache -r                           Refresh cache
"""
import os
import sys
import logging
import click
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
        github_team = os.environ.get('GITHUB_TEAM')
        if github_team:
            org_name, _ = parse_team_url(github_team)
            
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
        github_team = os.environ.get('GITHUB_TEAM')
        if github_team:
            parsed_org, parsed_team = parse_team_url(github_team)
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
        github_team = os.environ.get('GITHUB_TEAM')
        if github_team:
            org, team_from_env = parse_team_url(github_team)
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
                click.echo(f"    Expires in: {team_info['expires_in_seconds']} seconds")
                click.echo(f"    Status: {'Expired' if team_info['is_expired'] else 'Valid'}")
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
