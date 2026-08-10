import trivena_framework as trivena


def execute():
    trivena.reload_doc("Drive", "doctype", "Drive Team Member")
    for id in trivena.get_all("Drive Team Member"):
        member = trivena.get_doc("Drive Team Member", id)
        member.access_level = 2 if member.is_admin else 1
        member.save()
