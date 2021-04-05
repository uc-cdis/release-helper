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

Then you are ready to create auto-annotated tags:

```bash
gen3git tag 2.1.3
```

Or generate release notes into files (this example generates all supported outputs):

```bash
gen3git gen --html --markdown --text
```

It also works as a Travis after-deploy hook to update release notes into the GitHub
release that triggered the deploy:

```yaml
deploy:
  on:
    tags: true
env:
  global:
    secure: encrypted GH_TOKEN=YOUR_PERSONAL_ACCESS_TOKEN here
after_deploy:
- gen3git release
```


## Details

More options are available for the `gen3git` CLI.

```
gen3git --help
```

You only need access token for private repos or workaround GitHub rate limit. The token should be provided by setting `GH_TOKEN` or `GITHUB_TOKEN`. This script should be able to read from public repos without it.
