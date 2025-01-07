# Overview of Task Manager
<br>

##  Creating a task and the "Day View"

The Calendar treats each individual day as a place for tasks to be stored and managed, notes and a future feature not currently implemented

<br>

<img src="./images/ss9.png" alt="Screenshot of Tick interface" width="800">

<br> 

- Create a task, set a time and a short (or long) description about what needs to be done or some quick reminders.

<img src="./images/ss10.png" alt="Screenshot of Tick interface" width="800">

<br>

<img src="./images/ss11.png" alt="Screenshot of Tick interface" width="800">

<br>

The notes section will support Markdown formatting in the future. For now, you can feel free to journal your thoughts or any important notes, and press `Ctrl+S` to save them.

<br>

- You can navigate the day view with your up, down, left and right arrow keys and use `Enter` to select something. Tab is used to exit a element's focus. If you "focus" in on the notes section for example, you can press `Tab` to exit focus and move over to the next element again.

<br>

<img src="./images/ss12.png" alt="Screenshot of Tick interface" width="800">

<br>

- You can hover over a task to view it's full content.

<br>

<img src="./images/ss13.png" alt="Screenshot of Tick interface" width="600">




# Task indictators and insights 

## Task status tracking

 A task can be marked as "done" or "in-progress", and that will persist throughout other views of the app, of course. Once a task is marked, it is then stored and used to calculate:
    - Total number of tasks finished in a month
    - Total number of completed tasks
    - Total number of incomplete tasks
And then, a calculation is made based off of the completion % of all tasks within a month, and you are given a "grade" to help give you an idea of what you've comitted to and what you didn't. 

<br>

This feature will be fleshed out some more, as I've got a lot of ideas to gameify this.

<img src="./images/ss14.png" alt="Screenshot of Tick interface" width="900" style="transform: translateX(-10%)">




## Day view in Home section
All tasks are stored in the home section as well, in the "Today" tab. Here, you will get a view of the current day's tasks, quote of the day, Spotify playback widget, and a view of your "Upcoming" tasks that can be filtered between the next 7 days, and the next 30 days.

<br>

<img src="./images/ss15.png" alt="Screenshot of Tick interface" width="800">

<br>

<img src="./images/ss16.png" alt="Screenshot of Tick interface" width="800">

<br>

<img src="./images/ss17.png" alt="Screenshot of Tick interface" width="800">

## Navigation

<br>

This page can also be controlled with your up, down, left and right arrow keys. Up and down typically to cycle between tasks, and then left and right to switch between tabs. More tab features will be coming in the future. 

<br>

Pressing `Tab` however, will toggle the 7 day and 30 day views in your upcoming tasks.

<div align="right">
<a href="#nest" onclick="event.preventDefault(); loadPage('advanced');">
    <kbd>Next: NEST+ →</kbd>
</a>
</div>

# CALDAV Calendar Syncing

<br>

CalDAV (Calendar Distributed Authoring and Versioning) is an internet standard that allows users to access, manage, and share calendar data across multiple devices. Ticked now supports this- allowing you to sync Apple, Outlook(Windows only), Google, Thunderbird, Gmail, and many more Calendars to Ticked.

<br>

To get this setup, I'll quickly go over an example using iCloud syncing. 

<br>

1. First, you will want to go ahead and paste the corresponding CalDav link to your email system. Every site has one and in this case, we will be using apple's which is`https://caldav.icloud.com`

2. You will then want to head over to the Calendar on Ticked, and press `Ctrl+Y` to open the dialog to begin logging in to your Calendar.

<br>

<img src="./images/ss23.png" alt="Screenshot of Tick interface" width="800">

<br>

3. Next, head over to your calendar's account management page. For Apple, we will head over to `https://account.apple.com/account/manage`

4. Click on Sign-In and Security (or most similar for your calendar)

<br>

<img src="./images/ss24.png" alt="Screenshot of Tick interface" width="400">

<br>

5. Click "App-Specific Passwords"

<br>

<img src="./images/ss25.png" alt="Screenshot of Tick interface" width="800">

<br>

6. Go ahead and create one, name it something like "CalDav - Ticked" and copy/paste it somewhere safe.

7. Head over back to Ticked and paste the password into the Password input and enter your username (which will just be your email to whatever Calendar you are syncing)

<br>

<img src="./images/ss27.png" alt="Screenshot of Tick interface" width="800">

<br>

8. Click "Test" and you should receive a notification that it was succesful 
    - If you are failing to connect, make sure the password is correct, and that you placed your email into the username input

<br>

<img src="./images/ss28.png" alt="Screenshot of Tick interface" width="800">

<br>
<br>

<img src="./images/ss29.png" alt="Screenshot of Tick interface" width="800">

<br>

9. You are now able to select the Calendar you'd like to use, and press `Ctrl+Y` whenever you've adding events to your phone, computers or other devices in order to sync them up with Ticked.

10. If you'd like to switch Calendars or link a new one, press `Ctrl+S` in the Calendar view to repeat the process for your other calendars.

<br>

-----

<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>




