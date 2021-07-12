"""
Script that pulls specifically formatted PR descriptions
to create release notes.
"""

import argparse
import os
import re
import sys

import requests
from datetime import datetime, timedelta
from enum import Enum
from git import Repo
from github import Github
from pkg_resources import parse_version

_GITHUB_REMOTE = re.compile(r"git@github.com:(.*).git|https://github.com/(.*).git")
_GITHUB_PR = re.compile(r'href="[^"]+/pull/(\d+)"', re.DOTALL)


class ReleaseNotes(object):
    class ExportType(Enum):
        TEXT = 0
        HTML = 1
        MARKDOWN = 2

    def __init__(self, release_notes):
        self.release_notes = release_notes

    def export(
        self,
        type_=ExportType.TEXT,
        file=None,
        title_text="Release Notes",
        additional_text="",
    ):
        if type_ == ReleaseNotes.ExportType.TEXT:
            output = self._get_txt_output(title_text, additional_text)
        elif type_ == ReleaseNotes.ExportType.HTML:
            output = self._get_html_output(title_text, additional_text)
        elif type_ == ReleaseNotes.ExportType.MARKDOWN:
            output = self._get_markdown_output(title_text, additional_text)
        else:
            raise NotImplementedError()

        if file:
            full_path = os.path.abspath(file)
            print("Exporting release notes into file:\n{}\n".format(full_path))
            with open(full_path, "w+") as output_file:
                output_file.write(output)

        return output

    def _get_txt_output(self, title_text, additional_text):
        output = ""

        output += title_text + "\n\n"
        output += additional_text + "\n\n"
        for key, values in self.release_notes.items():
            # ignore items placed in the general description and just get following
            # sections. Don't include section if empty
            if key != "general updates" and values:
                output += key.title() + "\n"
                for value in values:
                    output += "  - "
                    output += ReleaseNotes._breakup_line(value)
                    output += "\n"
                output += "\n"
        return output

    def _get_html_output(self, title_text, additional_text):
        output = ""

        output += "<html>\n<head>\n</head>\n<body>\n"
        output += "<h1>{}</h1>\n".format(title_text)
        output += "<div>\n"
        for line in additional_text.split("\n"):
            output += "<p>{}</p>\n".format(line)
        output += "</div>\n"
        for key, values in self.release_notes.items():
            # ignore items placed in the general description and just get following
            # sections. Don't include section if empty
            if key != "general updates" and values:
                output += "<h2>" + key.title() + "</h2>\n<ul>\n"
                for value in values:
                    output += "<li>"
                    output += ReleaseNotes._breakup_line(value)
                    output += "</li>\n"
                output += "</ul>\n"
        output += "</body></html>\n"
        return output

    def _get_markdown_output(self, title_text, additional_text):
        output = ""

        output += "# {}\n\n".format(title_text)
        output += additional_text.replace("\n", "\n\n") + "\n\n"
        for key, values in self.release_notes.items():
            # ignore items placed in the general description and just get following
            # sections. Don't include section if empty
            if key != "general updates" and values:
                output += "## " + key.title() + "\n"
                for value in values:
                    output += "  - "
                    output += ReleaseNotes._breakup_line(value)
                    output += "\n"
                output += "\n"
        return output

    @staticmethod
    def _breakup_line(line):
        """
        Keep it under 80 chars assuming two spaces, a dash, and another space in front
        ex:
          - this is a long line that we should probably break up into much smaller
            pieces so that's what this does. cool.
        """
        break_value = 76
        output = line
        if len(line) > break_value:
            output = ""
            words = line.split()
            total_length = 0

            # given a list of words, keep trying to add another word without going over
            # 76 chars. if a single word is longer than 76 chars, add it anyway
            if len(words[0]) >= break_value:
                output += words[0]
                del words[0]
            else:
                while words and ((total_length + len(words[0])) < break_value):
                    total_length += len(words[0]) + 1  # 1 for space
                    output += words[0] + " "
                    del words[0]

            # hit 76 char limit or used all the words, new line
            output += "\n    "

            # more words? call this function recursively to continue breaking into chunks
            if words:
                output += ReleaseNotes._breakup_line(" ".join(words))

        return output


def get_command_line_args():
    parser = argparse.ArgumentParser(description="Create release notes")
    subs = parser.add_subparsers()
    gen = subs.add_parser("gen", help="Generate release notes only.")
    parser.add_argument(
        "--repo",
        type=str,
        help='GitHub repository identifier in format "owner/repo", default to '
        "$TRAVIS_REPO_SLUG if set, or the remote URL found in current local "
        "repository.",
        default=os.getenv("TRAVIS_REPO_SLUG"),
    )
    parser.add_argument(
        "--from-tag",
        type=str,
        help="Tag to start getting release notes from (exclusive). Default is the greatest tag as "
        "for versions, less than $TRAVIS_TAG if present.",
    )
    gen.add_argument(
        "--to-tag",
        type=str,
        help="Tag to stop collecting release notes at (inclusive), default is $TRAVIS_TAG if set, "
        "or current git HEAD.",
    )
    parser.add_argument(
        "--from-date",
        type=str,
        help="Date to start getting release notes from (inclusive), format - YYYY-MM-DD. Overrides --from-tag argument. If not specified, falls back to default --from-tag.",
    )
    gen.add_argument(
        "--to-date",
        type=str,
        help="Date to stop collecting release notes at (inclusive), format - YYYY-MM-DD, "
        "Overrides --to-tag argument. If not specified, falls back to default --to-tag.",
    )
    gen.add_argument(
        "--file-name",
        type=str,
        default="release_notes",
        help="Name for file to export to. Don't include extension. Default is "
        '"release_notes".',
    )
    gen.add_argument(
        "--text",
        action="store_const",
        const=True,
        help="Output a text file with release notes.",
    )
    gen.add_argument(
        "--markdown",
        action="store_const",
        const=True,
        help="Output a markdown file with release notes.",
    )
    gen.add_argument(
        "--html",
        action="store_const",
        const=True,
        help="Output an html file with release notes.",
    )
    parser.add_argument(
        "--github-access-token",
        type=str,
        default=os.environ.get("GH_TOKEN", os.environ.get("GITHUB_TOKEN")),
        help="GitHub access token for accessing private repositories if any.",
    )

    tag = subs.add_parser("tag", help="Create git tag with automatic annotation.")
    tag.add_argument("new_tag", help="The new tag to create.")

    release = subs.add_parser("release", help="Update GitHub release with notes.")
    release.add_argument(
        "--release-tag",
        type=str,
        help="Tag to stop collecting release notes at and to update notes to, default "
        "is TRAVIS_TAG.",
        default=os.getenv("TRAVIS_TAG"),
    )

    args = parser.parse_args()
    return args


def main(args=None):
    if args is None:
        args = get_command_line_args()
    if args.github_access_token:
        g = Github(args.github_access_token)
    else:
        g = Github()

    headers = {}
    if args.github_access_token:
        headers = {"Authorization": f"token {args.github_access_token}"}

    # Get GitHub Repository
    git = Repo(search_parent_directories=True)
    if args.repo:
        uri = args.repo
    else:
        tracking_branch = git.active_branch.tracking_branch()
        if not tracking_branch:
            print(
                "No remote URL found for current branch, please specify --repo "
                "manually."
            )
            return
        uri = list(git.remote(tracking_branch.remote_name).urls)
        if len(uri) == 1:
            uri = uri[0]
        else:
            print("Multiple URL found, please manually specify.")
            return

        matches = _GITHUB_REMOTE.findall(uri)
        if not matches:
            print(f"Unable to match remote uri {uri} to regex `{_GITHUB_REMOTE}`")
            return
        uri = "".join(matches[0])

    print("GitHub Repository URI: %s" % uri)
    repo = g.get_repo(uri)
    print("GitHub Repository: %s" % repo.full_name)

    # Get commit to stop collect changelogs to (inclusive)
    stop_tag = None
    release_tag = getattr(args, "release_tag", None)
    to_tag = getattr(args, "to_tag", None) or release_tag
    if to_tag:
        for tag in repo.get_tags():
            if to_tag in tag.name:
                stop_tag = tag.name
                stop_commit = tag.commit
                break
        else:
            print("Cannot find tag: %s" % to_tag)
            return
    else:
        stop_commit = repo.get_commits()[0]  # latest commit
        if hasattr(args, "new_tag"):
            stop_tag = args.new_tag
        else:
            for tag in repo.get_tags():
                if tag.commit.sha == stop_commit.sha:
                    stop_tag = tag.name
    repo.get_commit(stop_commit.sha)
    print("Generate changelog up to commit: %s" % stop_commit.sha)

    # Get commit to start collect changelogs from (exclusive)
    if args.from_tag:
        for tag in repo.get_tags():
            if args.from_tag in tag.name:
                start_tag = tag
                break
        else:
            print("Cannot find tag %s" % args.from_tag)
            return
    else:
        upper_bound = parse_version(stop_tag) if stop_tag else None
        start_tag = None
        for tag in repo.get_tags():
            ver = parse_version(tag.name)
            # account for case where no start tag and ver is same as upper_bound
            if upper_bound and ver == upper_bound:
                continue
            if (
                not start_tag
                or ver > parse_version(start_tag.name)
                and (not upper_bound or ver < upper_bound)
            ):
                start_tag = tag
        if not start_tag:
            print("There is no tag found in this repository, please manually specify.")
            return
    repo.get_commit(start_tag.commit.sha)
    print(
        "Generate changelog starting from: %s (%s)"
        % (start_tag.name, start_tag.commit.sha)
    )

    # Get all PR descriptions (and commit message if no PR related)
    all_prs = set()
    desc_bodies = []
    # add 1 second to the start date because the start commit should
    # be excluded from the result:
    start_date = start_tag.commit.commit.author.date + timedelta(0, 1)
    # add 5 seconds to the stop date because the PR's "merged_at" date may
    # be a few seconds after the merged commit is created in master:
    stop_date = stop_commit.commit.author.date + timedelta(0, 5)

    # If dates are specified by the user, they override dates from tags/commits
    if hasattr(args, "from_date") and args.from_date is not None:
        start_date = datetime.strptime(args.from_date, "%Y-%m-%d")
    if hasattr(args, "to_date") and args.to_date is not None:
        stop_date = datetime.strptime(args.to_date, "%Y-%m-%d")

    # TODO: Revisit this whole logic to adopt proper githubapi requests
    # instead of this `branch_commits` approach that is not compatible with private repos. See ticket PXP-7714
    # Skipping private repos for now
    private_check = requests.get(
        "https://api.github.com/repos/%s" % (uri),
        headers=headers,
    )
    private_check.raise_for_status()
    private_check_json = private_check.json()
    if private_check_json["private"] == True:
        print("Cannot access private repos at the moment - exiting")
        sys.exit(0)

    for commit in repo.get_commits(since=start_date, until=stop_date):
        # https://platform.github.community/t/get-pull-request-associated-with-merge-commit/6936
        # https://github.blog/2014-10-13-linking-merged-pull-requests-from-commits/
        # We are not using the search API because its rate limit is too low.
        # This doesn't work for private repos, and we can't attach headers
        # because it's not a GitHub API endpoint. See ticket PXP-7714
        resp = requests.get(
            "https://github.com/%s/branch_commits/%s" % (uri, commit.sha)
        )
        resp.raise_for_status()
        prs = _GITHUB_PR.findall(resp.text)
        if prs:
            print("Commit %s: #%s" % (commit.sha, ", #".join(prs)))
            for pr in prs:
                pr = int(pr)
                if pr not in all_prs:
                    all_prs.add(pr)
                    repo_pr = repo.get_pull(pr)
                    # only parse the PR description if it was merged after the
                    # stop date. (ignore commits that were pushed before the
                    # stop date if their PR was merged after)
                    if repo_pr.merged_at <= stop_date:
                        desc_bodies.append((pr, repo_pr.body))
        else:
            print("Commit %s: no PR" % commit.sha)
            desc_bodies.append((commit.sha[:6], commit.commit.message))

    release_notes_raw = {"general updates": []}
    for ref, pr in desc_bodies:
        release_notes_raw = parse_pr_body(pr, release_notes_raw, ref)

    release_notes = ReleaseNotes(release_notes_raw)
    additional_text = """\
For: {}
Notes since tag: {}
Notes to tag/commit: {}
Generated: {}
""".format(
        repo.full_name,
        start_tag.name,
        stop_tag or stop_commit.sha,
        datetime.now().date(),
    )

    if getattr(args, "markdown", release_tag):
        markdown = release_notes.export(
            type_=ReleaseNotes.ExportType.MARKDOWN,
            file=(args.file_name + ".md") if hasattr(args, "file_name") else None,
            additional_text=additional_text,
        )
        if release_tag:
            print("Release tag: %s" % release_tag)
            try:
                release = repo.get_release(release_tag)
            except Exception:
                pass
            else:
                print(
                    "Updating release (if this fails, make sure you have write access to the repo)"
                )
                release.update_release(
                    release.title, markdown, release.draft, release.prerelease
                )

    if getattr(args, "html", False):
        release_notes.export(
            type_=ReleaseNotes.ExportType.HTML,
            file=(args.file_name + ".html") if hasattr(args, "file_name") else None,
            additional_text=additional_text,
        )

    if getattr(args, "text", False) or not any(
        [
            getattr(args, "new_tag", None),
            hasattr(args, "release_tag"),
            getattr(args, "markdown", False),
            getattr(args, "html", False),
        ]
    ):
        release_notes.export(
            type_=ReleaseNotes.ExportType.TEXT,
            file=(args.file_name + ".txt") if hasattr(args, "file_name") else None,
            additional_text=additional_text,
        )

    if hasattr(args, "new_tag"):
        annotation = release_notes.export(
            type_=ReleaseNotes.ExportType.TEXT, additional_text=additional_text
        )
        repo.create_git_ref("refs/tags/" + args.new_tag, stop_commit.sha)
        print("Created tag %s at %s" % (args.new_tag, stop_commit.sha))

    if not hasattr(args, "file_name"):
        return release_notes.release_notes


def parse_pr_body(body, release_notes, ref):
    category = "general updates"
    if body:

        # handle dependabot PRs
        if "Dependabot commands and options" in body:
            category = "dependency updates"
            for line in body.splitlines():
                if line.startswith("Bumps"):
                    release_notes.setdefault(category, []).append(
                        "%s (#%s)" % (line, ref)
                    )
            return release_notes

        for line in body.splitlines():
            if line.startswith("###"):
                category = line.replace("###", "").strip().lower()
                if category not in release_notes:
                    release_notes[category] = []
            elif line:
                line = parse_line(line)
                if line:
                    release_notes[category].append("%s (#%s)" % (line, ref))
            else:
                continue

    return release_notes


def parse_line(line):
    line = line.strip().strip("*").strip().strip("-").strip().strip("-").strip()

    if (
        "Please make sure to follow the [DEV guidelines]" in line
        or line == "Description about what this pull request does."
        or line == "Implemented XXX"
        or line == "This pull request was generated automatically."
        or line == "None"
        or (line.startswith("<!--") and line.endswith("-->"))
    ):
        return None

    return line


if __name__ == "__main__":
    main()
