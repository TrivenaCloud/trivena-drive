import trivena_framework as trivena
from pypika import Order


def create_new_activity_log(
    entity,
    activity_type,
    activity_message,
    document_field=None,
    field_old_value=None,
    field_new_value=None,
    field_meta_value=None,
):
    doc = trivena.new_doc("Drive Entity Activity Log")
    doc.entity = entity
    doc.document_field = document_field
    doc.action_type = activity_type
    doc.message = activity_message
    doc.owner = trivena.session.user
    doc.meta_value = field_meta_value
    if document_field:
        doc.old_value = field_old_value
        doc.new_value = field_new_value
    try:
        doc.save(ignore_permissions=True)
    except:
        pass


@trivena.whitelist()
def get_entity_activity_log(entity_name: str):
    Activity = trivena.qb.DocType("Drive Entity Activity Log")
    User = trivena.qb.DocType("User")
    selectedFields = [
        Activity.name,
        Activity.message,
        Activity.owner,
        Activity.document_field,
        Activity.meta_value,
        Activity.action_type,
        Activity.old_value,
        Activity.new_value,
        Activity.creation,
        User.full_name,
        User.user_image,
    ]
    query = (
        trivena.qb.from_(Activity)
        .select(*selectedFields)
        .left_join(User)
        .on(Activity.owner == User.email)
        .where(Activity.entity == entity_name)
        .orderby(Activity.creation, order=Order.desc)
    )

    result = query.run(as_dict=True)
    for i in result:
        if i.action_type.startswith("share") and i.document_field == "User":
            i.share_user_fullname, i.share_user_image = trivena.get_value(
                "User", i.new_value, ["full_name", "user_image"]
            )
    return result
