app_name = "omeir_motors"
app_title = "Omeir Motors"
app_publisher = "Emeron Infospace"
app_description = "Omeir Motors"
app_email = "info@emeron.io"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "omeir_motors",
# 		"logo": "/assets/omeir_motors/logo.png",
# 		"title": "Omeir Motors",
# 		"route": "/omeir_motors",
# 		"has_permission": "omeir_motors.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/omeir_motors/css/omeir_motors.css"
# app_include_js = "/assets/omeir_motors/js/omeir_motors.js"

# include js, css files in header of web template
# web_include_css = "/assets/omeir_motors/css/omeir_motors.css"
# web_include_js = "/assets/omeir_motors/js/omeir_motors.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "omeir_motors/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Quotation" : "public/js/quotation.js",
              "Sales Invoice": "public/js/sales_invoice.js",
              "Purchase Receipt": "public/js/purchase_receipt.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "omeir_motors/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "omeir_motors.utils.jinja_methods",
# 	"filters": "omeir_motors.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "omeir_motors.install.before_install"
# after_install = "omeir_motors.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "omeir_motors.uninstall.before_uninstall"
# after_uninstall = "omeir_motors.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "omeir_motors.utils.before_app_install"
# after_app_install = "omeir_motors.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "omeir_motors.utils.before_app_uninstall"
# after_app_uninstall = "omeir_motors.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "omeir_motors.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	# "Material Request": "omeir_motors.overrides.material_request.CustomMaterialRequest",
    "Sales Invoice": "omeir_motors.overrides.sales_invoice.CustomSalesInvoice",
}

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------
scheduler_events = {
    "daily": [
        "omeir_motors.omeir_motors.doctype.prepaid_expense.prepaid_expense.post_scheduled_amortization"
    ]
}
# scheduler_events = {
# 	"all": [
# 		"omeir_motors.tasks.all"
# 	],
# 	"daily": [
# 		"omeir_motors.tasks.daily"
# 	],
# 	"hourly": [
# 		"omeir_motors.tasks.hourly"
# 	],
# 	"weekly": [
# 		"omeir_motors.tasks.weekly"
# 	],
# 	"monthly": [
# 		"omeir_motors.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "omeir_motors.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "omeir_motors.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "omeir_motors.task.get_dashboard_data"
# }

override_doctype_dashboards = {
	"Quotation": "omeir_motors.overrides.quotation_dashboard.get_data"
}

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["omeir_motors.utils.before_request"]
# after_request = ["omeir_motors.utils.after_request"]

# Job Events
# ----------
# before_job = ["omeir_motors.utils.before_job"]
# after_job = ["omeir_motors.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"omeir_motors.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

fixtures = [
    {
        "dt": "Custom HTML Block",
        "filters": [
            ["name", "in", [
                "Vehicle Service Dashboard",
                "Workshop Dashboard",
                "Overview Dashboard"
            ]]
        ]
    }
]