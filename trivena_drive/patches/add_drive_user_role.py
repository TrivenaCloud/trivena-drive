import trivena_framework as trivena


def execute():
    for user in trivena.get_all("User", fields=["name", "enabled"]):
        if user.enabled:
            user_doc = trivena.get_doc("User", user.name)
            user_doc.add_roles("Drive User")
            user_doc.save()
