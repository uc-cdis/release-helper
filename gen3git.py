"""
Script that pulls specifically formatted PR descriptions
to create release notes.
"""

import os
from enum import Enum
import requests
import json
from github import Github
import argparse
from datetime import datetime


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
            dir_path = os.path.dirname(os.path.realpath(__file__))
            print(
                "Exporting release notes into file:\n{}\n".format(dir_path + "/" + file)
            )
            with open(file, "w+") as output_file:
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
        output = line
        if len(line) > 76:
            output = ""
            words = line.split()
            total_length = 0

            # given a list of words, keep trying to add another word without going over
            # 76 chars
            while words and ((total_length + len(words[0])) < 76):
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
    parser.add_argument(
        "repo", type=str, help="Tag to start getting release notes from."
    )
    parser.add_argument(
        "from_tag", type=str, help="Tag to start getting release notes from."
    )
    parser.add_argument(
        "--to_tag",
        type=str,
        default="latest",
        help="Tag to stop collecting release notes at.",
    )
    parser.add_argument(
        "--file_name",
        type=str,
        default="release_notes",
        help="Name for file to export to. Don't include extention",
    )
    parser.add_argument(
        "--text",
        action="store_const",
        const=True,
        help="output a text file with release notes",
    )
    parser.add_argument(
        "--markdown",
        action="store_const",
        const=True,
        help="output a markdown file with release notes",
    )
    parser.add_argument(
        "--html",
        action="store_const",
        const=True,
        help="output an html file with release notes",
    )
    parser.add_argument(
        "--org",
        type=str,
        default="uc-cdis",
        help="Organization or person owning the specified repo",
    )

    parser.add_argument(
        "--github_access_token",
        type=str,
        default=os.environ.get("ACCESS_TOKEN"),
        help="",
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

    repo_path = args.org + "/" + args.repo
    repo = g.get_repo(repo_path)

    input_tag = args.from_tag

    if not input_tag:
        print("You didn't enter a git tag, can't get release notes.")
        exit()

    tagged_commit_sha = get_commit_sha_from_tag(repo, input_tag)
    if not tagged_commit_sha:
        print(
            "Tag {} doesn't exist in GitHub for repo: {}.".format(
                input_tag, repo.full_name
            )
        )
        exit()

    tagged_commit = repo.get_commit(sha=tagged_commit_sha)
    tagged_commit_date = tagged_commit.commit.committer.date.isoformat()

    prs = get_pr_descriptions_since_date(
        tagged_commit_date, repo_path, github_access_token=args.github_access_token
    )

    release_notes_raw = {"general updates": []}
    for pr in prs:
        release_notes_raw = parse_pr_body(pr, release_notes_raw)

    release_notes = ReleaseNotes(release_notes_raw)
    additional_text = "For: {}\nNotes since tag: {}\nGenerated: {}\n".format(
        repo.full_name, input_tag, datetime.now().date()
    )

    if args.markdown:
        release_notes.export(
            type_=ReleaseNotes.ExportType.MARKDOWN,
            file=args.file_name + ".md",
            additional_text=additional_text,
        )

    if args.html:
        release_notes.export(
            type_=ReleaseNotes.ExportType.HTML,
            file=args.file_name + ".html",
            additional_text=additional_text,
        )

    if args.text or not any([args.text, args.markdown, args.html]):
        release_notes.export(
            type_=ReleaseNotes.ExportType.TEXT,
            file=args.file_name + ".txt",
            additional_text=additional_text,
        )


def get_pr_descriptions_since_date(
    tagged_commit_date, repo_path, github_access_token=None
):
    get_pr_comments_query = """query {
          search(first: 100, type: ISSUE, query: $QUERY) {
            edges {
              node {
                ... on PullRequest {
                  title
                  body
                }
              }
            }
            pageInfo {
              endCursor
              hasNextPage
            }
          }
        }"""
    get_pr_comments_query = get_pr_comments_query.replace(
        "$QUERY",
        '"repo:{} state:closed type:pr created:>{}"'.format(
            repo_path, tagged_commit_date
        ),
    )

    if github_access_token:
        headers = {"Authorization": "Bearer {}".format(github_access_token)}
    else:
        headers = {}

    data = json.dumps({"query": str(get_pr_comments_query)})
    response = requests.post(
        "https://api.github.com/graphql", headers=headers, data=data
    )
    prs = response.json().get("data", {}).get("search", {}).get("edges", [])
    prs = [pr.get("node", {}).get("body") for pr in prs]
    return prs


def get_commit_sha_from_tag(repo, input_tag):
    tags = repo.get_tags()
    tagged_commit_sha = None
    for tag in tags:
        if tag.name == input_tag:
            tagged_commit_sha = tag.commit.sha

    return tagged_commit_sha


def parse_pr_body(body, release_notes):
    category = "general updates"
    for line in body.replace("\r", "").split("\n"):
        if line.startswith("###"):
            category = line.replace("###", "").strip().lower()
            if category not in release_notes:
                release_notes[category] = []
        elif line:
            line = parse_line(line)
            if line:
                release_notes[category].append(line)
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
    ):
        return None

    return line


if __name__ == "__main__":
    main()
