import frappe


DISCOUNT_LIMITS = {
    "Parts Incharge": 10,
    "Workshop Manager": 10,
    "Service Advisor": 5,
    "Parts Controller": 5,
}

FULL_ACCESS_ROLES = ["Invoice Full Access", "Administrator"]


def get_user_max_discount():
    user_roles = frappe.get_roles(frappe.session.user)

    for role in FULL_ACCESS_ROLES:
        if role in user_roles:
            return None
 
    max_discount = None
    for role, limit in DISCOUNT_LIMITS.items():
        if role in user_roles:
            if max_discount is None or limit > max_discount:
                max_discount = limit
    return max_discount


@frappe.whitelist()
def validate_discount(discount_percentage):
    discount_percentage = frappe.utils.flt(discount_percentage, 2)
    max_discount = get_user_max_discount()
    if max_discount is None:
        return {"allowed": True, "max_discount": None}

    if discount_percentage > max_discount:
        return {
            "allowed": False,
            "max_discount": max_discount,
            "message": f"You are not authorized to apply more than {max_discount}% discount. Your maximum allowed discount is {max_discount}%."
        }

    return {"allowed": True, "max_discount": max_discount}


def validate_invoice_discount(doc, method=None):
    discount = frappe.utils.flt(doc.additional_discount_percentage, 2)
    if discount <= 0:
        return

    max_discount = get_user_max_discount()
    if max_discount is None:
        return

    if discount > max_discount:
        frappe.throw(
            f"You are not authorized to apply more than {max_discount}% discount. "
            f"Your maximum allowed discount is {max_discount}%."
        )