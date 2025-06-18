# Simplifying the application

The scheduler application will be simplified by removing authentication.
Security will be handled by making the schedules have codes that are not publish
after creation. 

## Original Description

This web application helps a teacher schedule meetings with students in a class.
The students can log into the application with Github and will see a
representation of a week, with one box per hour, per day, for a single week. The
students will click on all of the boxes for an hour where the students can meet
with the class. The application will store these records in a MongoDB database
and compile all of the records to help the teacher pick a good time for a
meeting. 


## Changes 

First, remove unecessary features: 

* Remove all authentication
* Remove all use of the Github API ( gh_api.py ) 
* Remove the mongo database
* Remove the feature for setting the password from the schedule view. 

The new application flow will be that the main page has a button to create a new
schedule.  Clicking this button will create a new schedule, with a random ID in
the URL. The user will get a session, also with a random ID, and this random ID will go in 
both the session, and the URL for the schedule. 

## Routes

/: show the 'New' button
/new: create a new schedule
/s/<schedule_id>: Schedule Page. Read the session and redirect to the user's schedule page. ( Create a new session if needed )
/u/<schedule_id>/<user_id>: User Page. Display the users view of the schedule. 

## User Interface

The schedule view will have a prominently display URL for the page, so the
user can share the schedule. Display the url to the Schedule page on both the schedule
page and the user page. 

Before the user can submit changes to a schedule, the user's session must have a
name, which can be anything the user want to enter. If there is not a name set
in the user's session, pop a window to require the user to set a name. 

The user page will list the names of all of the users who have responded, with each name as a link to the user's page. If the session ID does not match the user page ID, the user can't
edit the results. 


## Other Details

Change the session storate to client. 

Store the data that user submits in a file in the file system. The root
directory is configurable with an env var but defaults to /data. The path
is the same as the path portion of the URL to the user page, but with a
.json extension. 

# Sprint 1

The files saved in the data directory must have both the schedule id and the user id in the
path. The schedule id is a directory, and the user is a file name, with a .json extension. 

In the schedule page, put the page url and users list below the schedule box

Update: put the page url and users list below the schedule box * on both the schedule page and the user page *


# Sprint 2

When I click on a dayhour, 