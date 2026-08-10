# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import trivena_framework as trivena
from trivena_framework.model.document import Document


class DriveToken(Document):
    def autoname(self):
        # The name is the secret capability itself.
        self.name = trivena.generate_hash(length=43)
