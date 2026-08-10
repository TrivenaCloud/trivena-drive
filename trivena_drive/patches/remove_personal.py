import time
from pathlib import Path

import trivena_framework as trivena


def execute():
    print(
        "This migration to a beta release might CORRUPT your data. Do NOT run this before taking a complete backup. You have two minutes left to cancel this deployment. "
    )
    time.sleep(120)

    trivena.reload_doc("Drive", "doctype", "Drive Disk Settings")
    doc = trivena.get_single("Drive Disk Settings")
    doc.team_prefix = "team_name"
    doc.preview_size = 100
    doc.save()

    trivena.reload_doc("Drive", "doctype", "Drive Permission")

    # Change team shares
    for share in trivena.get_list("Drive Permission", filters={"user": "$TEAM"}, fields=["name", "entity"]):
        team = trivena.db.get_value("Drive File", share["entity"], "team")
        trivena.db.set_value("Drive Permission", share["name"], "user", team)
        trivena.db.set_value("Drive Permission", share["name"], "team", 1)

    if trivena.get_value("Drive Permission", {"user": "$TEAM"}, "name"):
        raise ValueError("Not all perms migrated!")

    # Insert personal team for every user if not exists
    trivena.reload_doc("Drive", "doctype", "Drive Team")
    MAP = {}
    for user in trivena.get_all("User", pluck="name"):
        if user == "Guest":
            continue
        trivena.session.user = user
        team = trivena.db.exists({"doctype": "Drive Team", "personal": 1, "owner": user})
        if not team:
            team = trivena.get_doc({"doctype": "Drive Team", "title": user, "personal": 1})
            team.insert()
            print(f"Created personal team {team.name} for user {user}")
            trivena.db.set_value("Drive Team", team.name, "owner", user)
            MAP[user] = team.name
        else:
            print(f"Using pre-existing team {team} for {user}")
            MAP[user] = team

    trivena.session.user = "Administrator"

    trivena.reload_doc("Drive", "doctype", "Drive File")
    # Move all is_private files to personal team
    for f in trivena.get_all(
        "Drive File",
        filters={"is_private": 1},
        fields=["name", "is_private", "owner", "folder"],
    ):
        try:
            trivena.db.set_value("Drive File", f.name, "team", MAP[f.owner], update_modified=False)
            # For root elements, change parent folder
            if not trivena.db.get_value("Drive File", f.folder, "folder"):
                new_parent = trivena.db.get_value("Drive File", {"team": MAP[f.owner], "folder": None}, "name")
                trivena.db.set_value("Drive File", f.name, "folder", new_parent)
        except KeyError:
            print(f"There was an issue with the file {f} owned by {f.owner}")

    trivena.db.commit()
