import trivena_framework as trivena


def execute():
    for user in trivena.db.get_list("User", pluck="name"):
        teams = trivena.get_all(
            "Drive Team Member",
            pluck="parent",
            filters=[
                ["parenttype", "=", "Drive Team"],
                ["user", "=", user],
            ],
        )
        if teams:
            if not trivena.db.exists("Drive Settings", {"user": user}):
                trivena.get_doc(
                    {
                        "doctype": "Drive Settings",
                        "user": user,
                        "single_click": 1,
                        "default_team": teams[0],
                    }
                ).insert()
