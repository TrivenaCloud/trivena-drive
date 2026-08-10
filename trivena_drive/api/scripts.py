import trivena_framework as trivena

from trivena_drive.api.product import is_admin
from trivena_drive.utils import (
    create_drive_file,
    default_team,
    get_file_type,
    get_home_folder,
    update_file_size,
    STATUS_TRASHED,
    STATUS_REMOVED,
)
from trivena_drive.utils.files import FileManager
from trivena_drive.api.files import delete_entities
from datetime import date, timedelta


@trivena.whitelist()
@default_team
def sync_preview(team: str, json: bool = True):
    manager = FileManager()
    files = manager.fetch_new_files(team)
    sorted_files = sorted(files.items(), key=lambda p: len(p[0].parts))
    # For just checking, strip the root folder
    if json:
        return map(lambda x: (str(x[0]), x[1]), sorted_files)
    return sorted_files


@trivena.whitelist()
@default_team
def sync_from_disk(team: str):
    """
    One-way sync from disk to Drive. Ignores hidden files.
    """
    if not is_admin(team):
        trivena.throw(
            "You do not have permission to sync files from disk.",
            trivena.PermissionError,
        )

    sorted_files = sync_preview(team, json=False)
    files_added = []
    home_folder = get_home_folder(team)["name"]

    def get_or_create_parent(parent_path, owner):
        if not parent_path:
            return home_folder
        # Check if the parent folder exists
        parent = trivena.get_value(
            "File",
            {"file_url": (parent_path + "/") if parent_path else "", "team": team},
            "name",
        )
        if parent:
            return parent

        # If not, recursively create its own parent first
        grandparent_path = "/".join(parent_path.strip("/").split("/")[:-1])
        grandparent = get_or_create_parent(grandparent_path, owner)

        # Now create this parent folder
        new_parent = create_drive_file(
            team,
            file_name=parent_path.strip("/").split("/")[-1],
            parent=grandparent,
            file_type="Folder",
            entity_path=lambda _: str(parent_path) + "/",
            mime_type="folder",
            file_size=0,
            owner=owner,
        )
        return new_parent.name

    for file, (file_size, file_modified, mime_type, actual_path) in sorted_files:
        parent_path = str(file.parent).strip("./")
        parent = trivena.get_value(
            "File",
            {"file_url": parent_path + "/" if parent_path else "", "team": team},
            "name",
        )
        parent = get_or_create_parent(parent_path, trivena.session.user)

        files_added.append(
            create_drive_file(
                team,
                file.name,
                parent,
                "Folder" if mime_type == "folder" else get_file_type(mime_type),
                lambda _: actual_path if mime_type != "folder" else actual_path.strip("/") + "/",
                mime_type=mime_type,
                file_modified=file_modified,
                file_size=file_size,
                owner=trivena.session.user,
            )
        )
        update_file_size(parent, file_size)

    return files_added


def auto_delete_from_trash():
    days_before = (date.today() - timedelta(days=30)).isoformat()
    result = trivena.db.get_all(
        "File",
        filters={"status": STATUS_TRASHED, "file_modified": ["<", days_before]},
        fields=["name"],
    )
    delete_entities(result)


def clear_deleted_files():
    days_before = (date.today() - timedelta(days=30)).isoformat()
    result = trivena.db.get_all(
        "File",
        filters={"status": STATUS_REMOVED, "modified": ["<", days_before]},
        fields=["name"],
    )
    for entity in result:
        doc = trivena.get_doc("File", entity, ignore_permissions=True)
        doc.delete()
