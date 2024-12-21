# tick 📼

**Tick** is a lightweight, command-line-based task and productivity manager built in Python. It's been developed for my personal use throughout my University courses. 

# Installation (Python 3.7+)

## Mac/Linux
1. Clone the repository
```bash
git clone git@github.com:your-username/tick.git
cd tick
```

2. Install requirements
```bash
pip install -r requirements.txt
```

3. Run the program
```bash
python main.py
```

## Windows
1. Clone the repository
```bash
git clone git@github.com:your-username/tick.git
cd tick
```

2. Install curses for Windows and other requirements
```bash
pip install windows-curses
pip install -r requirements.txt
```

3. Run the program
```bash
python main.py
```

## TODO
- ~~Fix timeout issues when adding assignments/tasks within weeks.~~
- ~~Implement Calendar View as main hub~~
- ~~Allow ability to add "events" or "tasks" to dates and view them persistently~~
- Find cleaner formatting for all text within calendar/day views
- Fix flickering (currently only an issue on macOS)
- (FUTURE) Currently, data is stored in memory and doesn't persist between sessions. This comes after refactoring the code.

## Contributing

Contributions are welcome. Please fork the repository, make your changes, and submit a pull request.
