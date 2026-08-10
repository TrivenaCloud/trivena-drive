import trivena_framework as trivena
from trivena_framework import _
from trivena_framework.rate_limiter import rate_limit
from trivena_framework.translate import get_all_translations
from trivena_framework.utils import escape_html, split_emails, validate_email_address

from trivena_drive.api.permissions import get_teams, is_admin
from trivena_drive.utils import default_team


def access_app():
    return True


@trivena.whitelist()
def create_team(
    user: str, team_name: str = None, icon: str = None, s3_bucket: str = None, prefix: str = None, personal: int = 0
):
    """
    Used for creating teams (including the personal "team")
    """
    team_name = team_name if team_name else trivena.session.user
    exists = trivena.db.exists("Drive Team", {"title": team_name, "owner": user})
    if exists:
        return exists

    team = trivena.get_doc(
        {
            "doctype": "Drive Team",
            "title": team_name,
            "icon": icon,
            "s3_bucket": s3_bucket,
            "prefix": prefix,
            "personal": personal,
        }
    ).insert()

    # Insert Drive settings if not already there
    if not trivena.db.exists("Drive Settings", {"user": trivena.session.user}):
        trivena.get_doc({"doctype": "Drive Settings", "user": trivena.session.user}).insert()

    team.save()
    return team.name


@trivena.whitelist()
def edit_team(team: str, icon: str = None, team_name: str = None):
    team = trivena.get_doc("Drive Team", team)
    if not is_admin(team.name):
        trivena.throw("You are not an admin of this team")
    if team_name:
        team.title = team_name
    if icon is not None:
        team.icon = icon
    team.save()
    return team.name


@trivena.whitelist()
def leave_team(team: str):
    user = trivena.session.user
    drive_team = {k.user: k for k in trivena.get_doc("Drive Team", team).users}
    if user not in drive_team:
        trivena.throw("User doesn't belong to team")

    trivena.delete_doc("Drive Team Member", drive_team[user].name)


@trivena.whitelist()
def get_my_invites():
    invites = trivena.db.get_list(
        "Drive User Invitation",
        fields=["creation", "status", "team", "name"],
        filters={"email": trivena.session.user, "status": ("in", ("Proposed", "Pending"))},
    )
    for i in invites:
        i["team_name"] = trivena.db.get_value("Drive Team", i["team"], "title")
    return invites


@trivena.whitelist()
def get_team_invites(team: str):
    if not is_admin(team):
        trivena.throw(_("You don't have the permissions for this action."), trivena.PermissionError)

    invites = trivena.db.get_list(
        "Drive User Invitation",
        fields=["creation", "status", "email", "name", "owner"],
        filters={"team": team, "status": ("in", ("Proposed", "Pending"))},
    )
    for i in invites:
        i["user_name"] = trivena.db.get_value("User", i["email"], "full_name")
    return invites


@trivena.whitelist(allow_guest=True)
def signup(
    account_request: str,
    first_name: str,
    password: str,
    last_name: str | None = None,
    team: str | None = None,
):
    if not password:
        trivena.throw("Password is required.")

    account_request = trivena.get_doc("Account Request", account_request)
    if not account_request.invite:
        if trivena.get_website_settings("disable_signup"):
            trivena.throw("Signing up is disabled on this site.", trivena.PermissionError)

        if not account_request.login_count:
            trivena.throw("Please verify the email first.")

    user = create_user(account_request.email, first_name, password, last_name, True)
    account_request.signed_up = 1
    account_request.save(ignore_permissions=True)
    team = None
    if account_request.invite:
        invite = trivena.get_doc("Drive User Invitation", account_request.invite)
        invite.status = "Accepted"
        invite.save(ignore_permissions=True)
        if invite.team:
            # Add to that team
            team = trivena.get_doc("Drive Team", invite.team)
            team.append("users", {"user": user.email, "access_level": 0 if invite.as_guest else 1})
            team.save(ignore_permissions=True)
            team = invite.team
    return {"location": f"/drive/t/{team}" if team else "/drive/"}


def create_user(email, first_name, password, last_name=None, login=False):
    user = trivena.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": escape_html(first_name),
            "last_name": escape_html(last_name),
            "enabled": 1,
            "user_type": "Website User",
            "new_password": password,
        }
    )

    user.flags.no_welcome_mail = True
    try:
        user.insert(ignore_permissions=True)
    except trivena.DuplicateEntryError:
        trivena.throw("User already exists")

    if login:
        trivena.local.login_manager.login_as(user.email)
    return user


@trivena.whitelist(allow_guest=True)
def oauth_providers():
    from trivena_framework.utils.html_utils import get_icon_html
    from trivena_framework.utils.oauth import get_oauth2_authorize_url, get_oauth_keys
    from trivena_framework.utils.password import get_decrypted_password

    out = []
    providers = trivena.get_all(
        "Social Login Key",
        filters={"enable_social_login": 1},
        fields=["name", "client_id", "base_url", "provider_name", "icon"],
        order_by="name",
    )

    for provider in providers:
        client_secret = get_decrypted_password("Social Login Key", provider.name, "client_secret")
        if not client_secret:
            continue

        icon = None
        if provider.icon:
            if provider.provider_name == "Custom":
                icon = get_icon_html(provider.icon, small=True)
            else:
                icon = f"<img src='{provider.icon}' alt={provider.provider_name}>"

        if provider.client_id and provider.base_url and get_oauth_keys(provider.name):
            out.append(
                {
                    "name": provider.name,
                    "provider_name": provider.provider_name,
                    "auth_url": get_oauth2_authorize_url(provider.name, "/drive"),
                    "icon": icon,
                }
            )
    return out


@trivena.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60)
def send_otp(email: str, login: bool = False):
    if signup_disabled():
        trivena.throw("Signing up is disabled on this site.", trivena.PermissionError)

    account_request = trivena.get_doc(
        {
            "doctype": "Account Request",
            "email": email,
            "signed_up": 0,
        }
    ).insert(ignore_permissions=True)
    account_request.set_otp()
    try:
        account_request.send_otp()
    except:
        trivena.throw("Please setup an email account in Desk.")
    return account_request.name


@trivena.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60)
def verify_otp(account_request: str, otp: str):
    req = trivena.get_doc("Account Request", account_request)
    if req.otp != otp:
        trivena.throw("Invalid OTP")
    req.login_count += 1
    req.save(ignore_permissions=True)


@trivena.whitelist(allow_guest=True)
def get_settings():
    if trivena.session.user == "Guest":
        return {}
    try:
        return trivena.get_cached_doc("Drive Settings", trivena.session.user)
    except:
        return {}


@trivena.whitelist()
def set_settings(updates: dict[str, int | str]):
    try:
        settings = trivena.get_doc("Drive Settings", trivena.session.user)
    except:
        settings = trivena.get_doc({"doctype": "Drive Settings", "user": trivena.session.user})
        settings.insert()

    if "single_click" in updates:
        settings.single_click = int(updates["single_click"])
    if "auto_detect_links" in updates:
        settings.auto_detect_links = int(updates["auto_detect_links"])
    if "default_team" in updates:
        settings.default_team = updates["default_team"]
    settings.save()


@trivena.whitelist()
def invite_users(emails: str, team: str = None, as_guest: bool = False, auto: bool = False):
    if not emails:
        return

    # team-less call (share with new user) is gated at its call site
    if team and not is_admin(team):
        trivena.throw(_("You don't have the permissions for this action."), trivena.PermissionError)

    email_string = validate_email_address(emails, throw=False)
    email_list = split_emails(email_string)
    if not email_list:
        return

    existing_invites = trivena.db.get_list(
        "Drive User Invitation",
        filters={"email": ["in", email_list], "team": team, "status": "Pending"},
        pluck="email",
    )

    new_invites = list(set(email_list) - set(existing_invites))
    for email in new_invites:
        invite = trivena.new_doc("Drive User Invitation")
        invite.email = email
        invite.team = team
        invite.status = "Automatic" if auto else "Pending"
        invite.as_guest = as_guest
        invite.insert()


@trivena.whitelist()
def set_user_access(team: str, user: str, access_level: int):
    if not is_admin(team):
        trivena.throw("You don't have the permissions for this action.")
    drive_team = {k.user: k for k in trivena.get_doc("Drive Team", team).users}
    drive_team[user].access_level = access_level
    drive_team[user].save()


@trivena.whitelist()
def remove_user(team: str, user_id: str):
    if not is_admin(team) or user_id == trivena.session.user:
        trivena.throw("You don't have the permissions for this action.")
    drive_team = {k.user: k for k in trivena.get_doc("Drive Team", team).users}
    if trivena.session.user not in drive_team:
        trivena.throw("User doesn't belong to team")
    trivena.delete_doc("Drive Team Member", drive_team[user_id].name)


@trivena.whitelist()
@default_team
def get_team_users(team: str):
    user_teams = get_teams()
    if team == "all":
        teams = user_teams
    elif team in user_teams:
        teams = [team]
    else:
        trivena.throw(_("You don't have access to this team."), trivena.PermissionError)

    team_users = {}
    for team in teams:
        team_users |= {k.user: k.access_level for k in trivena.get_doc("Drive Team", team).users}
    users = trivena.get_all(
        doctype="User",
        filters=[
            ["name", "in", list(team_users.keys())],
        ],
        fields=[
            "name",
            "email",
            "full_name",
            "user_image",
        ],
    )
    for u in users:
        u["access_level"] = team_users[u["name"]]
    return users



@trivena.whitelist(allow_guest=True)
def accept_invite(key: str, redirect: bool | str = True):
    try:
        invitation = trivena.get_doc("Drive User Invitation", key)
    except:
        trivena.throw("Could not find invitation.")

    return invitation.accept(redirect)


@trivena.whitelist()
def reject_invite(key: str):
    try:
        invitation = trivena.get_doc("Drive User Invitation", key)
    except:
        trivena.throw("Could not find invitation.")

    invitation.status = "Expired"
    invitation.save(ignore_permissions=True)


@trivena.whitelist(allow_guest=True)
def get_translations():
    if trivena.session.user != "Guest":
        language = trivena.db.get_value("User", trivena.session.user, "language")
        if not language:
            language = trivena.db.get_single_value("System Settings", "language")
    else:
        language = trivena.db.get_single_value("System Settings", "language")

    return get_all_translations(language)


def is_drive_site_admin():
    return trivena.has_permission("Drive Disk Settings", "write")


@trivena.whitelist()
def is_site_admin():
    return {"is_admin": is_drive_site_admin()}


@trivena.whitelist(allow_guest=True)
def disk_settings(**kwargs):
    settings = trivena.get_single("Drive Disk Settings")
    if not is_drive_site_admin():
        # Return only safe values
        return {"preview_size": settings.preview_size, "enabled": settings.enabled}

    if trivena.request.method == "GET":
        return settings

    field_map = {
        "team_prefix": "team_id",
        "root_folder": None,
        "aws_key": None,
        "aws_secret": None,
        "bucket": None,
        "endpoint_url": None,
        "signature_version": "s3v4",
    }
    settings.enabled = 1
    for field, value in kwargs.items():
        if field in field_map and value:
            setattr(settings, field, value)
        elif field == "backend_type":
            # If backend is s3, enable it. Otherwise, disable.
            settings.enabled = 1 if value == "s3" else 0
    settings.save()


WHITELISTED_DOMAINS = [
    "https://gameplan.frappe.cloud",
    "https://frappecloud.com",
    "https://trivena.io",
    "https://cloud.trivena.io",
]


def after_request(request):
    try:
        if request.path.startswith("/drive/") or request.path.startswith("/api/method/"):
            trivena.local.response_headers["Content-Security-Policy"] = (
                f"frame-ancestors {' '.join(WHITELISTED_DOMAINS)} 'self'"
            )
            if "X-Frame-Options" in trivena.local.response_headers:
                del trivena.local.response_headers["X-Frame-Options"]
    except:
        pass


@trivena.whitelist(allow_guest=True)
def signup_disabled():
    return trivena.get_website_settings("disable_signup")
