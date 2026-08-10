from __future__ import unicode_literals

import trivena_framework as trivena

no_cache = 1

TITLES = {"signup": "Create an Account"}


def get_desk_theme():
    if trivena.session.user == "Guest":
        return "Light"
    return trivena.get_cached_value("User", trivena.session.user, "desk_theme") or "Light"


def get_context():
    csrf_token = trivena.sessions.get_csrf_token()
    trivena.db.commit()
    context = trivena._dict()
    context.boot = get_boot()
    context.boot.csrf_token = csrf_token
    context.desk_theme = context.boot.desk_theme
    context.csrf_token = csrf_token
    context.site_name = trivena.local.site

    context.title = "Frappe Drive"
    context.description = "Visit Drive online."

    if not trivena.form_dict.app_path:
        return context

    # Parsing
    parts = trivena.form_dict.app_path.split("/")
    if len(parts) >= 3:
        context.description = "Open this online."
        # Ideally add thumbnail, but that might break if there's no thumbnail
        try:
            [file_name, owner, is_folder] = trivena.get_cached_value(
                "File", parts[1], ["file_name", "owner", "is_folder"]
            )
            context.title = "Folder - " + file_name if is_folder else file_name
            context.description = "Owned by " + trivena.get_cached_value("User", owner, "full_name")
        except:
            pass

    elif parts[0] in TITLES:
        context.title = TITLES[parts[0]]
        context.description = ""
    return context


@trivena.whitelist(methods=["POST"])
def get_context_for_dev():
    if not trivena.conf.developer_mode:
        trivena.throw("This method is only meant for developer mode")
    return get_boot()


def get_boot():
    return trivena._dict(
        {
            "frappe_version": trivena.__version__,
            "default_route": get_default_route(),
            "site_name": trivena.local.site,
            "read_only_mode": trivena.flags.read_only,
            "desk_theme": get_desk_theme(),
        }
    )


def get_default_route():
    return "/drive"
