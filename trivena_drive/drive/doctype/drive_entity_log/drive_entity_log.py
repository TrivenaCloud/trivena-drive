# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from trivena_framework.model.document import Document


class DriveEntityLog(Document):
    def validate(self):
        """
        Users can only create recent records for files they can access.
        """
        if trivena.session.user not in ["Administrator", self.user]:
            raise trivena.PermissionError("You can only create a recent record for yourself.")

        file = trivena.get_doc("File", self.entity_name)
        if not user_has_permission(file, "read"):
            raise trivena.PermissionError("You cannot create a recent record this file.")
