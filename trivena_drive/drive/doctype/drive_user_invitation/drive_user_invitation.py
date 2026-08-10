# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import trivena_framework as trivena
from trivena_framework.model.document import Document
from trivena_framework.utils import add_days, get_datetime, now, validate_email_address

EXPIRY_DAYS = 1


class DriveUserInvitation(Document):
    def has_expired(self):
        return get_datetime(self.creation) < get_datetime(add_days(now(), -EXPIRY_DAYS))

    def before_insert(self):
        validate_email_address(self.email, True)

    def after_insert(self):
        if self.status == "Pending":
            try:
                self.invite_via_email()
            except BaseException as e:
                trivena.log_error(f"Failed to send invite email: {e}")
                pass
        elif self.status == "Proposed":
            admins = trivena.get_all("Drive Team Member", filters={"parent": self.team, "access_level": 2}, pluck="user")
            for admin in admins:
                trivena.get_doc(
                    {
                        "doctype": "Drive Notification",
                        "to_user": admin,
                        "type": "Team",
                        "message": f"A person ({self.email}) from your domain has joined Frappe Drive",
                    }
                ).insert(ignore_permissions=True)
            trivena.db.commit()

    def invite_via_email(self):
        trivena.sendmail(
            recipients=self.email,
            subject=f"Frappe Drive - Invitation",
            template="drive_invitation",
            args={
                "invite_link": trivena.utils.get_url(f"/api/method/drive.api.product.accept_invite?key={self.name}"),
                "user": trivena.session.user,
                "team_name": trivena.db.get_value("Drive Team", self.team, "title"),
            },
            now=True,
        )

    def accept(self, redirect=True):
        if self.status not in ["Pending", "Automatic"]:
            trivena.throw("This key has already been used")
        if self.status == "Expired" or self.has_expired():
            self.status = "Expired"
            self.save(ignore_permissions=True)
            trivena.db.commit()
            trivena.throw("Invalid or expired key")

        exists = trivena.db.exists(
            "Account Request",
            {
                "email": self.email,
                "signed_up": 1,
            },
        )

        if redirect:
            trivena.local.response["type"] = "redirect"

        if not exists:
            # If the user does not have an account, redirect to sign up
            req = trivena.get_doc(
                {
                    "doctype": "Account Request",
                    "email": self.email,
                    "invite": self.name,
                    "login_count": 1,
                }
            ).insert(ignore_permissions=True)
            trivena.db.commit()
            user_exists = trivena.db.exists("User", self.email)

            if not user_exists:
                team_name = trivena.db.get_value("Drive Team", self.team, "title")
                url = f"/drive/signup?e={self.email}{'&t=' + team_name if team_name else ''}&r={req.name}"
                if isinstance(redirect, str):
                    url += f"&redirect-to={redirect}"
                trivena.local.response["location"] = url
                return

        # Otherwise, add the user to the team
        team = trivena.get_doc("Drive Team", self.team)
        team.append("users", {"user": self.email, "access_level": 0 if self.as_guest else 1})
        team.save(ignore_permissions=True)
        self.status = "Accepted"
        self.accepted_at = trivena.utils.now()
        self.save(ignore_permissions=True)
        trivena.db.commit()

        if trivena.session.user == "Guest":
            trivena.local.login_manager.login_as(self.email)

        trivena.local.response["location"] = "/drive/t/" + self.team
        return "/drive/t/" + self.team
