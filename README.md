# release-helper

Python CLI to generate release notes by scanning a repo's pull requests descriptions.
Expects PR descriptions to have format specified in the `pull_request_template.md` file
in this repo.

## Quickstart

Must have [Python](https://www.python.org/downloads/) installed.

Install dependencies by running the following in terminal/command prompt:

```
pip install -r requirements.txt
```

Run the script from terminal (this example generates all supported outputs):

```
python release_notes.py fence 0.1.0 --html --markdown --text
```

## Details

More options are available for the `release_notes.py` CLI.

```
python release_notes.py --help
```

You only need access token for private repos. This script should be able to read from
public repos without the need to set the `GITHUB_ACCESS_TOKEN`.