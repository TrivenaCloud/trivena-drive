import trivena_framework as trivena


def execute():
    for k in trivena.get_all("Drive File", fields=["name", "modified"]):
        trivena.db.set_value(
            "Drive File",
            k.name,
            "_modified",
            k.modified.strftime("%Y-%m-%d %H:%M:%S.%f"),
            update_modified=False,
        )
