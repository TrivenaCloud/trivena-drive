import trivena_framework as trivena
from trivena_framework import _
from pypika import functions as fn

from trivena_drive.api.permissions import get_teams
from trivena_drive.utils import default_team, STATUS_ACTIVE

MEGA_BYTE = 1024**2
DriveFile = trivena.qb.DocType("File")


@trivena.whitelist()
def storage_breakdown(team: str, owned_only: bool):
    if team not in get_teams():
        trivena.throw(_("You don't have access to this team."), trivena.PermissionError)

    limit = trivena.get_value("Drive Team", team, "quota" if owned_only else "storage") * MEGA_BYTE
    filters = {
        "team": team,
        "is_folder": False,
        "status": STATUS_ACTIVE,
        "file_size": [">=", limit / 200],
    }
    if owned_only:
        filters["owner"] = trivena.session.user

    entities = trivena.db.get_list(
        "File",
        filters=filters,
        order_by="file_size desc",
        fields=["name", "file_name", "owner", "file_size", "file_type"],
    )

    query = (
        trivena.qb.from_(DriveFile)
        .select(DriveFile.file_type, fn.Sum(DriveFile.file_size).as_("file_size"))
        .where((DriveFile.is_folder == 0) & (DriveFile.status == STATUS_ACTIVE) & (DriveFile.team == team))
    )
    if owned_only:
        query = query.where(DriveFile.owner == trivena.session.user)

    return {
        "limit": limit,
        "total": query.groupby(DriveFile.file_type).run(as_dict=True),
        "entities": entities,
    }


@trivena.whitelist()
@default_team
def storage_bar_data(team: str | None = None, entity_name: str | None = None):
    if not team:
        team = trivena.get_value("File", entity_name, "team")
        if not team:
            trivena.throw("Could not find team.", ValueError)

    if team not in get_teams():
        trivena.throw(_("You don't have access to this team."), trivena.PermissionError)

    query = (
        trivena.qb.from_(DriveFile)
        .where(
            (DriveFile.team == team)
            & (DriveFile.is_folder == 0)
            & (DriveFile.owner == trivena.session.user)
            & (DriveFile.status == STATUS_ACTIVE)
        )
        .select(fn.Coalesce(fn.Sum(DriveFile.file_size), 0).as_("total_size"))
    )
    result = query.run(as_dict=True)[0]
    result["limit"] = trivena.get_value("Drive Team", team, "quota") * MEGA_BYTE
    return result
