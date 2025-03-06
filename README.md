![License](https://img.shields.io/badge/license-MIT-red)
![Unreleased](https://img.shields.io/badge/beta-pre%20release-blue)
<br>
[![Lint](https://github.com/cachebag/Ticked/actions/workflows/lint.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/lint.yml)
<br>
[![Security](https://github.com/cachebag/Ticked/actions/workflows/security.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/security.yml)
<br>
[![Python Tests](https://github.com/cachebag/Ticked/actions/workflows/pytest.yml/badge.svg)](https://github.com/cachebag/Ticked/actions/workflows/pytest.yml/badge.svg)

# 📟 **Ticked** is a Terminal based task and productivity manager built in Python over the Textual framework.

<div align="center">
  <img src="images/ss1.png" alt="Screenshot 1" width="1000">
  <img src="images/ss2.png" alt="Screenshot 2" width="1000">
  <img src="images/ss3.png" alt="Screenshot 3" width="1000">
  <img src="images/ss4.png" alt="Screenshot 3" width="1000">
</div>



--- 

### To update if you already have an older version installed:
  - For Homebrew:
```bash
brew upgrade ticked
```
  - For pip:
```bash
pip install --upgrade ticked
```

## [Read the docs to quickly get set up](https://cachebag.github.io/Ticked/#introduction)
#  **Features**

### 📝 **Task and Schedule Management** - TODO's, Task Metrics, iOS, Google and Outlook Calendar Syncing
###  <img src="https://github.com/user-attachments/assets/51f56067-9cb8-4c70-bae9-031373661774" alt="Canvas Bug Icon" width="24" /> **NEST+** - Vim Motions/Commands, Syntax Highlighting, Autopairs/complete/indent, etc.
### <img src="https://github.com/user-attachments/assets/b82fa581-1b89-442f-8090-94390c388030" alt="Canvas Bug Icon" width="24" /> **CANVAS LMS** - Course List Details, Assignments, Announcements and Grade Statistics
### <img src="https://upload.wikimedia.org/wikipedia/commons/1/19/Spotify_logo_without_text.svg" alt="Spotify Logo" width="24" /> **Spotify Integration** - Playlists, Search Functionality and Playback control
---

## Want to jump in?
You can either read the [docs](https://cachebag.github.io/Ticked/), and get quickly setup to begin working or you can go straight into it by doing:
```bash
pip install ticked
ticked
```
for Homebrew
```bash
brew tap cachebag/ticked
brew install ticked
```


## Contributing

New issues and pull requests are welcome. [Read the Development guide for details.](https://cachebag.github.io/Ticked/#dev)

If you want to contribute:
1. Fork the repository.
2. Make your changes.
3. Submit a pull request for review.

## Testing

```bash
pytest
```

## Development

### Running CI Checks Locally

You can run the same checks that run in GitHub Actions locally using the provided script:

1. First, make the script executable:
   ```bash
   chmod +x check.sh
   ```

2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

3. Run specific checks:
   - For security checks: `./check.sh security`
   - For linting: `./check.sh lint`
   - For tests: `./check.sh pytest`
   - For all checks: `./check.sh all`

## License

[MIT](LICENSE)

