# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import trivena_framework as trivena


def whitelist(fn):
    if not trivena.conf.enable_ui_tests:
        trivena.throw("Cannot run UI tests. Set 'enable_ui_tests' in site_config.json to continue.")

    whitelisted = trivena.whitelist(allow_guest=True)(fn)
    return whitelisted


@whitelist
def clear_data():
    doctypes = trivena.get_all("DocType", filters={"module": "Drive", "issingle": 0}, pluck="name")
    for doctype in doctypes:
        trivena.db.delete(doctype)

    trivena.set_user("Administrator")
    admin = trivena.get_doc("User", "Administrator")
    admin.add_roles("Drive Admin")

    if not trivena.db.exists("User", "four@test.io"):
        user = trivena.get_doc(
            doctype="User",
            email="four@test.io",
            first_name="Four",
            last_name="McTest",
            send_welcome_email=0,
        )
        user.insert()

    keep_users = ["Administrator", "Guest", "four@test.io"]
    for user in trivena.get_all("User", filters={"name": ["not in", keep_users]}):
        trivena.delete_doc("User", user.name)
