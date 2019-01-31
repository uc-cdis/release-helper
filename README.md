# release-helper

Python CLI to generate release notes by scanning a repo's pull requests descriptions.
Expects PR descriptions to have format specified in the `pull_request_template.md` file
in this repo.


## Quickstart

Must have [Python](https://www.python.org/downloads/) and
[pip](https://pip.pypa.io/en/stable/installing/) installed.

It is recommended to install this tool globally, rather than [in each virtualenv](
https://pipenv.readthedocs.io/en/latest/install/#pragmatic-installation-of-pipenv). So
run this with system-wide pip:

```bash
pip install --user --editable git+https://github.com/uc-cdis/release-helper.git@master#egg=gen3git
```

You may need to add the `bin` directory under "user base" to your `PATH`, for example:

```bash
echo "export PATH=\"`python -m site --user-base`/bin:\$PATH\"" >> ~/.bash_profile
```

(Or alternatively, you may use `sudo pip install` without `--user` and PATH trouble)

Run the script from terminal (this example generates all supported outputs):

```
gen3git fence 0.1.0 --html --markdown --text
```


## Details

More options are available for the `gen3git` CLI.

```
gen3git --help
```

You only need access token for private repos. This script should be able to read from
public repos without the need to set the `GITHUB_ACCESS_TOKEN`.
