![License](https://img.shields.io/badge/license-MIT-blue)
![Unreleased](https://img.shields.io/badge/unreleased-in%20development-orange)


![image](https://github.com/user-attachments/assets/f092a9ba-5b99-4763-8259-6af2b54f3cd4)


**Tick** is a lightweight, TUI-based task and productivity manager built with Python using the Textual library. Intended for University Students, but usable for everyone. 

## Table of Contents

- [Tick 📼](#tick-)
  - [Features](#features)
  - [Installation](#installation)
    - [Mac/Linux](#maclinux)
    - [Windows](#windows)
  - [Contributing](#contributing)
 
    
## Features

- Calendar: [█████████████░░░░░░░] 90%
    - Still a few formatting issues
    - Home view still needs a statistics section showing (and appending to the database) finished, in progress and total tasks for the current year
    - Need to fix/implement keybindngs for navigation
    - Would like to implement a markdown viewer for the notes in the day view. Still trying to figure out the best way to implement this
- Database: [████████████████████] 100%
    - Schema is set and easily scalable
    - Still would be a good idea to implement data imports; allowing the user to move their .db file between devices
- Nest+:    [█████████░░░░░░░░░░] 55%
    - Still a good amount of formatting issues
    - Keybinding/Focus issues. Implemntations for vim motions are setup nicely, but general program navigation and UX needs some work.
    - Need better save, file creation/deletion and navigation for the directory tree
    - Embed a markdown viewer for .md files
    - Need a clean and easy to read, built in guide to help users navigate the code editor and other program keybinds
- Pomodoro: [░░░░░░░░░░░░░░░░░░░] 0%
    - This shouldn't be too hard
- Spotify:  [░░░░░░░░░░░░░░░░░░░] 0%
    - Neither should this, but need to think more about how to implement this exactly...
      - Concurrency in music playing while navigating program
      - Full features or something simpler like playlists only, liked songs, etc.
      - OAUth implementation

## Contributing

New issues and pull requests are welcome! 

If you want to contribute:
1. Fork the repository.
2. Make your changes.
3. Submit a pull request for review.

