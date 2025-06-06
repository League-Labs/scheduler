
# League Labs Scheduler

This web application helps a teacher scehdule meeting with students in a class.
The students can log into the application with Github and will see a
representation of a week, with one box per hour, per day, for a single week. The
students will click on all of the boxes for an hour where the students can meet
with the class. The application will store these records in a database and
compile all of the records to help the teacher pick a good time for a meeting. 

## Application Structure

The application is a Python Flask backend with a single page app Javascript
front end. The database is sqlite. The application is deployed with Docker
compose. 

Sessions are stored in the file system not in the Sqlite database

Pages are implemented in Jinja2. The Single Page Application is Javascript that
is stored in its own .js file and is included directly into the SPA page via
Jinja templates

## Login

Users log into the application using Github. If the user loads a page of the
application without being logged in the user is redirected to the login flow,
but the application will save the original URL in the session. After login, the
original URL is restored. 

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

The background color of each dayhour indicates the portion of people who have
selected that dayhour, of all of the github accounts that have a record of any
select for that team.  The colors are: 

- dark green: 100 of users have selected this dayhour
- light green: 100%->90%  of users have selected this dayhour
- yellow: 70%->90% of users have selected this dayhour
- light red < 70% of users have selected this dayhour

## Database & protocol


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

The database has tables for:

* users
* userteam

The userteam table records a user's selections for a team. It has columns for:

* user_id
* team: string name of the team 
* selections: JSON list of all of the dayhours that the user selected. 

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
- Create a section in the README with instructions for me to set up Github Oauth ( like getting tokens from )
- Let me validate that the logins work. 

### Spring4: User Interface

- Full implemementataion of the user interface. 


