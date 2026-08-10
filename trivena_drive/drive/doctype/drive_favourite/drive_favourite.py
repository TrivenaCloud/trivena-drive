# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from trivena_drive.api.permissions import user_has_permission
from trivena_framework.model.document import Document
import trivena_framework as trivena


class DriveFavourite(Document):
    def validate(self):
        """
        Users can only create favourite files they can access.
        """
        if trivena.session.user not in ["Administrator", self.user]:
            raise trivena.PermissionError("You can only create favourites for yourself.")

        file = trivena.get_doc("File", self.entity)
        if not user_has_permission(file, "read"):
            raise trivena.PermissionError("You cannot favourite this file.")
