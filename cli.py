#!/usr/bin/env python
"""
CLI tool for working with GitHub teams in the scheduler application.

Usage:
    python cli.py list-teams [org_name]
    python cli.py list-members [org_name] [team_slug]
"""
import os
import sys
import logging
import click
from dotenv import load_dotenv
from gh import list_teams, list_team_members, parse_team_url

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
