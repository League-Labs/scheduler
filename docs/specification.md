# League Labs Scheduler

This web application helps a teacher schedule meetings with students in a class.
The students can log into the application with Github and will see a
representation of a week, with one box per hour, per day, for a single week. The
students will click on all of the boxes for an hour where the students can meet
with the class. The application will store these records in a MongoDB database
and compile all of the records to help the teacher pick a good time for a meeting. 

## Application Structure

The application is a Python Flask backend with a single page app Javascript
front end. The database is MongoDB (connection string in the MONGO_URI env var).
The application is deployed with Docker compose. 

Sessions are stored in the file system, not in MongoDB.

Pages are implemented in Jinja2. The Single Page Application is Javascript that
is stored in its own .js file and is included directly into the SPA page via
Jinja templates

## Login

Users log into the application using Github. If the user loads a page of the
application without being logged in the user is redirected to the login flow,
but the application will save the original URL in the session. After login, the
original URL is restored. 

For deployment, the configuration can specify a team ( secified by the full team
URL ) in the env var GITHUB_TEAM. If specified, only members of that team will
be allowed to log in


## User Interface

There is only one page to the application: a view of a schedule for a week, with
hours in a grid,  with a column for each day of the week, starting with Monday,
and a row for each hour of the day, from 8AM to 9PM. We will case the
intersection of the hour row and the day column a 'dayhour' where each day hour
in the grid represents one hour of a day in a week. 

The user interface functionality on the page is implemented in Javascript.

The URL path may have a <team> part, which  determines the 'team' for the page.
An individual schedule is determiend by the combination of the user and the
team, so a single user can have scheduled on multiple teams. 

- If the user clicks on a dayhour, the dayhour is selected, with a black dot
placed in the middle of the dayhour box.

- if the user clicks on an hour ( the row header ) all of the dayhours in that
row are toggled on or off. If there are no dayhours in the row selected, they
are all turned on. If there is one or more selected, all of the dayhours that
are on are turned off. 

- If the user clicks on a day ( the column header ) all of the dayhours in that
column are toggled on or off. If there are no dayhours in the column selected, they
are all turned on. If there is one or more selected, all of the dayhours that
are on are turned off. 

- Below each column title (day names) is a button with "copy ->". Clicking this
button will copy the contents of the column below the button to the column to
the right. 

There are instructions at the bottom of the app page, telling the user about the
effect of clicking on the row and column headings, and what the copy button does. 

### Dayhour Colors

The background color of each dayhour indicates the portion of people who have
selected that dayhour, of all of the github accounts that have a record of any
select for that team.  The colors are: 

- dark green and star icon on the left of the cell: 100 of users have selected this dayhour
- light green: second most common number of choices
- yellow: third most common number of choices
- light red < 70% of users have selected this dayhour
- white: there are zero selections for this day hour. 

To find the color for the dayhour cells:

- sum the number of selections per day hour cell for all dayhours
- put all of the sums into a list
- remove duplicated from the list
- sort the list from greatest to least

Then for the first three numbers in the list, color all cells with that
number of selections with the corresponding colors in the color list, 
(dark green, light green, yellow). All other cells with a non-zero value are red, 
and the cells with a zero value are white. 

### Dayhour counts

The dayhour cell with also display a small number in the lower-right, with a
size that is 1/2 of the dayhour cell, with displays the count of votes for that
cell, if there are more than 0 selections for the cell. 

## Database & protocol

The application uses MongoDB for data storage. The connection string is provided
in the environment variable MONGO_URI.

In the database, days are recorded in common 1 letter abbreviations: 

* M: Monday
* T: Tuesday
* W: Wednesday
* R: Thursday
* F: Friday
* S: Saturday
* U: Sunday

Hours are recorded in 24H format: 08,09,10,11,12,13,14,15,16,17,18,19

A Dayhour is recorded by concatenating the two, so:

W08: Wednesday at 8AM
U14: Sunday at 2PM. 

The MongoDB database has collections for:

* users
* userteam

The userteam collection records a user's selections for a team. Each document has fields for:

* user_id (name of the user, as it appears in  session['user'])
* team: string name of the team 
* selections: List of all of the dayhours that the user selected. 

## Server

The backend server is implemented in Flask. It has these routes: 

GET / ( root ): Lists all of the teams, with URLs to each team
GET /<team>: Return the page + javascript  for the team view for this user. 
GET /<team>/selections: Return Javascript of all of the dayhours that are selected for the current user + team ( return a javascript list of selected dayhours)
POST /<team>/selections: Save the dayhours that the user has selected. ( POST a list of selected dayhours )
GET /<team>/info: Return a TeamInfo structure that has info about the team. 
GET /hello: a test route that returns 'hello' and the name of the current user. 

The TeamInfo structure has:
* name: team name ( the fragment)
* count: total number of user accounts that have made selections
* users: list of github usernames that have made selections on the team
* dayhours: a map, where keys are dayhours, and the values are the number of selections for that dayhour. 

## Testing

When the database is created, it will create three test users: test1, test1, test3. These users can be specified
in a query parameter to the url, '?user=test1': For instance: 

http://host/footeam/?user=test1

If the server gets a user with a user=test? query argument it will:

1) Log out any logged in user
2) Clear the session and create a new one
3) Log in that test user
4) Redirect to the URL without the query parameter. 


## Development Sprints

We will implement this application in several steps. You will complete each step 
and test it before going on to the next step. 

### Sprint 1: Hello World Server

- Setup the Flask application. 
- Create a stub /login route for logins. 
- Test starting the server
- Test the /hello target and that it redirects to the login stub 
- Test the test user login with /hello?user=test1 ( which does not redirect to login )
- Test logging in another test user and show that the sessions are cleared. 

### Sprint2: Backend server

- Create the GET and POST  routes for `/<team>/selections`
- Test loging in as test1, then POST selections and GET them again. 
- Create the routes for /<team>/info to get info about the team
- Test POSTing selections for the test1, test2 and test3 users and verify that /<team>/info works

### Sprint3: Github Login

- Implement Github login
- Create a section in the README with instructions for me to set up Github Oauth
  ( like getting tokens from )
- Let me validate that the logins work. 

### Sprint4: Add Jinja2 Templates

Setup Jinja templates. Create a page 'base.html' for the basic structure of the
application ( head, title, body, etc ). From base.html, derive a `page.html`
that is tailored with the style for the pages in this application. THen create
pages for: 

* index
* team ( which will hold the SPA )
* hello

Setup static files for style.css, the application .js file, and images. 

### Sprint5: User Interface

- Full implemementataion of the user interface. 

### Sprint6: Database 

- Implement MongoDB for data storage. 
- Auto create collections and indexes if they do not exist. 
- create a justfile to run management commands: run the development server and
  recreate the database. 

### Sprint7: Dockerize

Setup a docker deployment. 

- run the production server using gunicorn to run the Flask app
- copy the whole repo into the /app directory in the Dockerfile
- create a Justfile entry to build the docker container
- Create a Justfile entry to run the docker composition. 

For the docker composed configuration, the MongoDB connection string is provided
via the MONGO_URI environment variable, in the .env file. This file and
variablel should be referenced in the Docker configuration

### Sprint8: Github Team

See the section "## Login" for a description of the used of teams in the login
process. 

- Create a github.py file that has functions for using the Github API to get a
list of Github accounts that are members of the team specified in GITHUB_TEAM
- Create a click CLI program, in file cli.py, that has commands that can (1)
list the teams that the GITHUB_TOKEN has access to and (2) list the members of a
given team
- Update the app so that if GITHUB_TEAM is specified, only users that are a
member of the team can login. 

Getting the list of teams and team members from Github is slow so the app should
cache the member list in Mongo. Start a single thread that will re-cache the data 
occasionally. The re-caching process will be implemented in a persistent thread that will: 

- recache the data
- waits for a GITHUB_TEAM_TTL seconds
- waits for a threading.Event
- Clears the event

Besure to acess the Mongo database in a thread-safe way. 

Also add a command to the cli, 'cache' which has options to: print the cache
status ( '-s/--status' ), invalidate the cache (-i/--invalidate) and  refresh (
-r/--refresh)
