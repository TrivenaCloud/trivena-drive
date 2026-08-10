import os

import trivena_framework as trivena
import requests
from trivena_framework.rate_limiter import rate_limit
from trivena_framework.utils import now


def mark_as_viewed(entity):
    return
    if (
        trivena.session.user == "Guest"
        or not trivena.has_permission(doctype="Drive Entity Log", ptype="create", user=trivena.session.user)
        or entity.is_folder
    ):
        return

    entity_log = trivena.db.get_value("Drive Entity Log", {"entity_name": entity.name, "user": trivena.session.user})
    if entity_log:
        trivena.db.set_value("Drive Entity Log", entity_log, "last_interaction", now(), update_modified=False)
        return
    doc = trivena.new_doc("Drive Entity Log")
    doc.entity_name = entity.name
    doc.user = trivena.session.user
    doc.last_interaction = now()
    doc.insert()
    return doc


def generate_otp():
    """Generates a cryptographically secure random OTP"""

    return int.from_bytes(os.urandom(5), byteorder="big") % 900000 + 100000


def get_country_info():
    ip = trivena.local.request_ip

    def _get_country_info():
        fields = [
            "status",
            "message",
            "continent",
            "continentCode",
            "country",
            "countryCode",
            "region",
            "regionName",
            "city",
            "district",
            "zip",
            "lat",
            "lon",
            "timezone",
            "offset",
            "currency",
            "isp",
            "org",
            "as",
            "asname",
            "reverse",
            "mobile",
            "proxy",
            "hosting",
            "query",
        ]

        try:
            res = requests.get(f"https://pro.ip-api.com/json/{ip}?fields={','.join(fields)}")
            data = res.json()
            if data.get("status") != "fail":
                return data
        except Exception:
            pass

        return {}

    return trivena.cache().hget("ip_country_map", ip, generator=_get_country_info)



def assign_drive_role_and_create_settings(user, method: str) -> None:
    """Assign the "Drive User" role, settings and a personal team to a new User."""
    from trivena_drive.api.product import create_team

    role_name = "Drive User"
    user_name = user.name

    if not user_name or user_name in ("Guest", "Administrator"):
        return

    if not trivena.db.exists("Role", role_name):
        trivena.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)

    user_doc = trivena.get_doc("User", user_name)
    user_doc.append("roles", {"role": role_name})
    user_doc.save(ignore_permissions=True)

    trivena.get_doc({"doctype": "Drive Settings", "user": user.email}).insert(ignore_permissions=True)

    # Created as the new user so the team is owned by and shared with them.
    original_user = trivena.session.user
    try:
        trivena.set_user(user_name)
        create_team(user=user_name, team_name=user_name, personal=1)
    finally:
        trivena.set_user(original_user)