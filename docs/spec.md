# League Labs Scheduler

This web application helps a people schedule meetings with others. The users
will see a representation of a week, with one box per hour, per day, for a
single week. The students will click on all of the boxes for an hour where the
students can meet with the class. The application will store these records  and
compile all of the records to help the user pick a good time for a meeting. 

## Pages

Sessions are stored in Cookies, and users will get a session from any page. The
session primarily holds the 6 digit base-62 user id and the user's full name. 

### The Index page

The Index page shows a "new"  button to create a new schedule. When user clicks
on the "new" button, it wil redirect to the `/new` new schedule page. That page
will create a database ( filesystem ) entry for the new schedule ( including
creating the password ), then it will redirect to the schedule page.  The
redirection will include the query arg `?pw=<passwword>` where `password` is a 6
digit base-62 random string. 

### Schedule page

When the schedule page loads, it looks for the `?pw=<password>` argument.
Different things can heppend depending on the combinations of the `?pw` arg
being set and the password being set in the `meta.json` file exising:

* `?pw` exists, `meta.json` password exists: Check the password, redirect to
  index with flash error if the passwords to not match
* `?pw` does not exist: redirect to the user's schedule page, based on the user
  id in the session 
* `?pw` exists, `meta.json` password does not: Redirect to index with a flash
  error message. 

The schedule page shows:

* A non-editable schedule
* The URL for the page schedule page without the password ( To give to other
  users ) 
* The URL for the page schedule page with the password ( For the user to manage
  the page ) 
* A button to take the current user to the user's scheduling page. 
* A list of the names of the users who have submitted responses. 
* An editable string for the name of the schedule
* an editable text box for the description of the schedule

### User Schedule

This page has a view of a schedule for a week, with hours in a grid,  with a
column for each day of the week, starting with Monday, and a row for each hour
of the day, from 8AM to 9PM. We will call the intersection of the hour row and
the day column a 'dayhour' where each day hour in the grid represents one hour
of a day in a week. 

At the top of the screen is the name of the schedule, and below that is the
description, both taken from the `meta.json` file. Below the description is the
schedule. 

The user interface functionality on the page is implemented in Javascript.

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

The application uses the file system for data storage. The files saved in the
data directory must have both the schedule id and the user id in the path. The
schedule id is a directory, and the user is a file name, with a .json extension.

For instance, the data directory might look like:

```
$ tree data 
data
├── FK4ZLCeq8LXv
│   ├── kjhgsdfu.json
│   └── meta.json
├── u5G5AjLR6nie
│   ├── kjhhg6G4R.json
│   └── meta.json
└── zEnSAbJgxQWM
    └── d2E2Tq7.json
```

Each `.json` file with the random number is the selections for one user. Both
the schedule id and the user id are 6 digit base-62 random numbers. The
`meta.json` files hold the metadata, including the password and other text about
the schedule.

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

## Routes

/: show the 'New' button
/new: create a new schedule then redirect to schedule page. 
/s/<schedule_id>: Schedule Page. Read the session and redirect to the user's schedule page. ( Create a new session if needed )
/u/<schedule_id>/<user_id>: User Page. Display the users view of the schedule. 

The `/new` route should not create a new schedule if the user does not have a
session with a user id 
