import trivena_framework as trivena


def scan(folder):
    folder = trivena.get_doc("Drive File", folder)
    child_folders = trivena.get_list("Drive File", {"folder": folder.name, "is_group": 1}, pluck="name")
    for child in child_folders:
        scan(child)
    sizes = trivena.get_list("Drive File", {"folder": folder.name, "is_active": 1}, pluck="file_size")
    trivena.db.set_value("Drive File", folder.name, "file_size", sum(sizes), update_modified=False)


def execute():
    roots = trivena.get_list("Drive File", {"folder": ""}, pluck="name")
    for root in roots:
        scan(root)
