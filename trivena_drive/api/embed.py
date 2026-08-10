from pathlib import Path

import trivena_framework as trivena

from trivena_drive.api.permissions import user_has_permission
from trivena_drive.api.files import get_file_internal
from trivena_drive.utils import WRITER_CONTENT_DOCTYPE, get_home_folder


@trivena.whitelist(allow_guest=True)
def get_file_content(embed_name: str, parent_entity_name: str):
    """
    Give or stream embed content
    """
    parent = trivena.get_value(
        "File",
        parent_entity_name,
        ["content_doctype", "file_name", "mime_type", "file_size", "owner", "file_url", "team"],
        as_dict=1,
    )

    if parent.content_doctype != WRITER_CONTENT_DOCTYPE:
        trivena.throw("This is not an embed.")

    embed = trivena.get_cached_doc("File", embed_name)

    if embed.folder != parent_entity_name or not user_has_permission(embed_name, "read"):
        raise trivena.PermissionError("You do not have permission to view this file")

    if not embed.file_url:
        embed = trivena._dict(
            file_url=str(
                Path(
                    get_home_folder(embed.team)["file_url"],
                    "embeds",
                    embed_name,
                )
            ),
            team=embed.team,
            file_name=embed.file_name,
        )
    return get_file_internal(embed)
