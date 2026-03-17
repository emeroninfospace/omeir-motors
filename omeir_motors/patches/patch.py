import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from omeir_motors.omeir_motors.custom_and_property_setter.custom_field import CREATE_FIELDS

def execute():  
  
    create_custom_fields(CREATE_FIELDS, ignore_validate=True)
    