import trivena_framework as trivena

from trivena_drive.utils import PRESENTATION_CONTENT_DOCTYPE


def presentation(doc, event):
    file = trivena.db.get_value(
        "File",
        {"content_docname": doc.name, "content_doctype": PRESENTATION_CONTENT_DOCTYPE},
        "name",
    )
    print('renaming', doc)
    if file:
        drive_file = trivena.get_doc("File", file)
        if event == "on_update":
            drive_file.rename(doc.title)
        if event == "on_trash":
            drive_file.permanent_delete()
