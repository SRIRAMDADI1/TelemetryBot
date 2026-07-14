"""Create the Sales IVR agent-building backlog in Azure DevOps.

Creates Epics -> Features -> User Stories -> Tasks with parent-child links,
acceptance criteria, and the `agent-buildable` tag on stories.

Auth and target are read from environment variables:
  AZURE_DEVOPS_ORG_URL   e.g. https://dev.azure.com/YourOrg
  AZURE_DEVOPS_PROJECT   e.g. SalesIVRInsurance
  AZURE_DEVOPS_PAT       Personal Access Token with Work Items (Read & Write)

Usage:
  python create_backlog.py --dry-run     # print what would be created
  python create_backlog.py               # create work items for real

No third-party dependencies (uses urllib from the standard library).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from backlog import BACKLOG, STORY_TAG, Epic, Feature, Story, counts

API_VERSION = "7.1"


class ADOClient:
    def __init__(self, org_url: str, project: str, pat: str) -> None:
        self.org_url = org_url.rstrip("/")
        self.project = project
        token = base64.b64encode(f":{pat}".encode()).decode()
        self.auth_header = f"Basic {token}"

    def create_work_item(
        self,
        work_item_type: str,
        title: str,
        description: str | None = None,
        acceptance_criteria: list[str] | None = None,
        tags: list[str] | None = None,
        parent_url: str | None = None,
    ) -> dict:
        encoded_type = urllib.parse.quote(work_item_type)
        encoded_project = urllib.parse.quote(self.project)
        url = (
            f"{self.org_url}/{encoded_project}/_apis/wit/workitems/"
            f"${encoded_type}?api-version={API_VERSION}"
        )
        patch: list[dict] = [
            {"op": "add", "path": "/fields/System.Title", "value": title}
        ]
        if description:
            patch.append(
                {"op": "add", "path": "/fields/System.Description", "value": _html(description)}
            )
        if acceptance_criteria:
            patch.append(
                {
                    "op": "add",
                    "path": "/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
                    "value": _html_list(acceptance_criteria),
                }
            )
        if tags:
            patch.append(
                {"op": "add", "path": "/fields/System.Tags", "value": "; ".join(tags)}
            )
        if parent_url:
            patch.append(
                {
                    "op": "add",
                    "path": "/relations/-",
                    "value": {
                        "rel": "System.LinkTypes.Hierarchy-Reverse",
                        "url": parent_url,
                    },
                }
            )

        data = json.dumps(patch).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json-patch+json")
        req.add_header("Authorization", self.auth_header)
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            raise RuntimeError(
                f"ADO API error {exc.code} creating {work_item_type} '{title}': {body}"
            ) from exc


def _html(text: str) -> str:
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"<div>{escaped}</div>"


def _html_list(items: list[str]) -> str:
    lis = "".join(
        f"<li>{i.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</li>"
        for i in items
    )
    return f"<ul>{lis}</ul>"


def _titled(ref: str, title: str) -> str:
    return f"[{ref}] {title}"


def create_backlog(client: ADOClient, dry_run: bool) -> None:
    created = {"Epic": 0, "Feature": 0, "User Story": 0, "Task": 0}

    for epic in BACKLOG:
        epic_url = _create(client, "Epic", _titled(epic.ref, epic.title), epic.description, dry_run)
        created["Epic"] += 1

        for feature in epic.features:
            feature_url = _create(
                client,
                "Feature",
                _titled(feature.ref, feature.title),
                feature.description,
                dry_run,
                parent_url=epic_url,
            )
            created["Feature"] += 1

            for story in feature.stories:
                story_url = _create(
                    client,
                    "User Story",
                    _titled(story.ref, story.title),
                    story.description,
                    dry_run,
                    acceptance_criteria=story.acceptance_criteria,
                    tags=[STORY_TAG],
                    parent_url=feature_url,
                )
                created["User Story"] += 1

                for task_title in story.tasks:
                    _create(
                        client,
                        "Task",
                        f"[{story.ref}] {task_title}",
                        None,
                        dry_run,
                        parent_url=story_url,
                    )
                    created["Task"] += 1

    print("\nSummary:")
    for wtype, n in created.items():
        print(f"  {wtype}: {n}")


def _create(
    client: ADOClient,
    work_item_type: str,
    title: str,
    description: str | None,
    dry_run: bool,
    acceptance_criteria: list[str] | None = None,
    tags: list[str] | None = None,
    parent_url: str | None = None,
) -> str | None:
    indent = {"Epic": "", "Feature": "  ", "User Story": "    ", "Task": "      "}[work_item_type]
    if dry_run:
        tag_note = f" [tags: {', '.join(tags)}]" if tags else ""
        print(f"{indent}{work_item_type}: {title}{tag_note}")
        return f"dry-run://{work_item_type}/{title}"

    result = client.create_work_item(
        work_item_type,
        title,
        description=description,
        acceptance_criteria=acceptance_criteria,
        tags=tags,
        parent_url=parent_url,
    )
    wid = result.get("id")
    print(f"{indent}{work_item_type} #{wid}: {title}")
    return result.get("url")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Sales IVR backlog in Azure DevOps")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without calling ADO")
    args = parser.parse_args()

    c = counts()
    print(
        f"Backlog: {c['epics']} epics, {c['features']} features, "
        f"{c['stories']} user stories, {c['tasks']} tasks\n"
    )

    if args.dry_run:
        create_backlog(ADOClient("dry-run", "dry-run", "dry-run"), dry_run=True)
        return 0

    org_url = os.environ.get("AZURE_DEVOPS_ORG_URL")
    project = os.environ.get("AZURE_DEVOPS_PROJECT")
    pat = os.environ.get("AZURE_DEVOPS_PAT")
    missing = [
        name
        for name, val in [
            ("AZURE_DEVOPS_ORG_URL", org_url),
            ("AZURE_DEVOPS_PROJECT", project),
            ("AZURE_DEVOPS_PAT", pat),
        ]
        if not val
    ]
    if missing:
        print(f"ERROR: missing environment variables: {', '.join(missing)}", file=sys.stderr)
        print("Run with --dry-run to preview without credentials.", file=sys.stderr)
        return 1

    client = ADOClient(org_url, project, pat)
    create_backlog(client, dry_run=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
