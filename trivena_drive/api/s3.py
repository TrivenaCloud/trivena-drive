import trivena_framework as trivena
from trivena_framework import _
from trivena_drive.api.files import get_file_content, get_s3_url


@trivena.whitelist(allow_guest=True)
def fetch(path: str):
    name = trivena.db.get_value("File", {"file_url": get_s3_url(path)})
    if not name:
        trivena.throw(_("Not found"), trivena.DoesNotExistError)
    try:
        return get_file_content(name)
    except (trivena.PermissionError, trivena.DoesNotExistError):
        trivena.throw(_("Not found"), trivena.DoesNotExistError)
