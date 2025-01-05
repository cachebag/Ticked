# NEST+ 
<br>

NEST+ is the bread and butter of Ticked. My goal with it is to create a central environment for STEM students in particular to handle all of the things they typically do in 3 different platforms and place them into one place.

<br>

Most aren't familiar with code editors like Vim, which is okay. The idea is that for those who are especially interested in communicating with their terminal and learning skills, such as vim, this will be a place to do that in a bit more of a friendly fashion.

##  Navigating NEST+

Since there's a few moving pieces in NEST+, knowing how to make your way around will be a good way to not lose time figuring out how to make it work.

<br>
In general, you will navigate between your file navigator and code editor using your arrow keys. Upon opening the page, your default focus will be on the file navigator.

- Right arrow key will take you to the Code Editor

<br>

<img src="./images/ss20.png" alt="Screenshot of Tick interface" width="800">

- The border color of the respective window will indicate what you are "focused" on
- When in the Code Editor, you can press `Shift+left-arrow-key` to focus back on the file navigator.

<br>

<img src="./images/ss19.png" alt="Screenshot of Tick interface" width="800">

<br> 

- When inside the file navigator, you can use the left, right, up and down arrow keys to navigate your directories and `Enter` to go into them.
- `Ctrl+H` will toggle your hidden files and folder within any given directory
- `Ctrl+N` will create a new file (Currently does not work when focused on the file navigator)

<img src="./images/ss21.png" alt="Screenshot of Tick interface" width="800">

- You can select where to save your newly created file.

<br>

There will be future support for deleting files, in addition to creating/deleting folders as well. 


# Using the code editor

## Code Editor Features

When inside the code editor, the following features are currently supported, though limited in their customization:

- Syntax highlighting for most popular programming languages and markup formats:
    - Python
    - JavaScript
    - HTML
    - CSS
    - YAML
    - JSON
    - SQL
    - XML
- The editor also supports vim motions and commands. Only the following are currently implemented:
    - Motions
        - `dd`: Delete entire line
        - `de`: delete from here, to the end of a line
        - `x`: delete character
        - `w`: go forward to the next word
        - `b`: go back to the previous word
        - `u`: undo
        - `ctrl+r`
    - Commands | To begin using a command, press `Esc` to enter `NORMAL` mode. `:` is the prefix for commands
        - `%d`: Delete everything in current file
        - `w`: Save file
- To use either the commands or the motions, you must be in `NORMAL` mode, triggered by pressing `Esc` when in the code editor. Pressing `i` will take you into `INSERT` mode where you can type like normal. 

- There is a vim-like status bar at the bottom of the editor to indicate file write info, command snippets as well as the current mode you are in.

<br>

<img src="./images/ss22.png" alt="Screenshot of Tick interface" width="800">

<br>

Future support will include a breadth of vim-esque features and hopefully plugins as well to allow for things that make our lives easier such as auto-indentation/folding, auto-pairs(for bracks, parentheses, etc.) and auto-completion

<br>

Keep an eye on the [GitHub releases](https://github.com/cachebag/Ticked/releases) and my [Reddit account](https://www.reddit.com/user/cachebags/submitted/) to find out when NEST+ is udpated.

<div align="right">
<a href="#dev" onclick="event.preventDefault(); loadPage('dev');">
    <kbd>Next: Development Guide →</kbd>
</a>
</div>
