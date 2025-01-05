# Development Guide for Ticked

Welcome to the development documentation for **Ticked**. This guide provides everything you need to contribute effectively to the project, including setup instructions, best practices, issue tracking, and useful resources.

---

## Introduction to Contribution

Here's how you can contribute.

### Forking and Cloning the Repository
- Fork the repository on GitHub.
- Clone the forked repository to your local machine:
   ```powershell
   git clone https://github.com/cachebag/Ticked.git
   ```
- Navigate to the project directory:
   ```powershell
   cd Ticked
   ```

### Submitting Pull Requests
- Create a new branch for your changes:
   ```powershell
   git checkout -b feature/your-feature-name
   ```
- Make your changes and commit them:
   ```powershell
   git add .
   git commit -m "Add description of your changes"
   ```
- Push the branch to your fork:
   ```powershell
   git push origin feature/your-feature-name
   ```
- Open a pull request on the original repository.

---

## Best Practices

To maintain code quality and consistency, please follow these best practices:

### Code Quality
- [Textual's documentation](https://textual.textualize.io/) is extensive and should always be open if you plan to help implemented new feature or fix existing ones.
- Make graceful use of `async` functions, the `@work` decorator (along with all methods and practices of workers and Textual widgets) and mount_all/remove_children functions to prioritize the performance of Ticked.

I am open to all suggestions for improvement on the codebase, its structure or practices used within the code itself. I want to make this project perfect for its users so I welcome any and all criticism/feedback.

<br>

## Some more general ideas for those that are helping that are also more novice:
### Git Workflow
- Keep your main branch updated with the upstream repository.
- Use meaningful commit messages.
- Squash minor commits before submitting a pull request.

---

## Setup and Pull Requests

### Environment Setup
1. Install the required dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
2. Make and activate a virtual environment:
   ```powershell
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Run the application:
   ```powershell
   textual run ticked.app:Ticked --dev
   ```

### Testing Changes
Ensure that the application runs without errors after your changes:
```powershell
python -m ticked.app
```

---

## Features and Bugs

### Existing Issues
#### Nest+ (File Management)
- **Ctrl+N** does not work when creating a new file in the file directory view. (Specifically when focused on the directory tree, it works when in the code editor)
- Missing ability to create or delete folders/files.
- Newly created files do not automatically open in the editor.

#### Main Menu
- Clicking on multiple menu options during loading causes a blank screen.
- Navigation is not implemented for Pomodoro Timer, Spotify, and Settings views.

#### Calendar View
- Day buttons should expand dynamically to show more tasks.
- Improve styling of "Previous" and "Next Month" buttons.
- Day view lacks a feature. Possible ideas include:
  - AI chatbot.
  - Time-blocking schedule.
  - Important links list.

### Suggested Enhancements
- Investigate using **pynvim** for custom command support. I don't think this will work well but if it can and does, it might save us some headaches when implementing vim-esque features in NEST+.

---

## Useful Resources

### Textual Documentation
- [Textual Official Documentation](https://textual.textualize.io/)
- [Getting Started with Textual](https://textual.textualize.io/getting_started/)

### Other References
- [GitHub Docs - Pull Requests](https://docs.github.com/en/pull-requests)

---

I appreciate your contributions and effort in improving Ticked. If you have any questions or need assistance, feel free to reach out via GitHub discussions or on Discord @cachebag.

