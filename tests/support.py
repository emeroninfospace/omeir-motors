"""Minimal dependency doubles for local tests; never used by the application."""

import ast
import os
import sys
import types
from collections import OrderedDict
from pathlib import Path
from unittest.mock import Mock


class Row(dict):
	__getattr__ = dict.get
	__setattr__ = dict.__setitem__

	def update(self, *args, **kwargs):
		super().update(*args, **kwargs)
		return self

	def copy(self):
		return Row(self)


class Doc:
	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)

	def get(self, key, default=None):
		return getattr(self, key, default)

	def set(self, key, value):
		setattr(self, key, value)


def flt(value, precision=None):
	value = float(value or 0)
	return round(value, precision) if precision is not None else value


def module(name):
	result = types.ModuleType(name)
	result.__path__ = []
	sys.modules[name] = result
	if "." in name:
		parent, attr = name.rsplit(".", 1)
		if parent not in sys.modules:
			module(parent)
		setattr(sys.modules[parent], attr, result)
	return result


def install():
	frappe = module("frappe")
	frappe._dict = Row
	frappe.throw = Mock(side_effect=ValueError)
	frappe.db = Mock()
	frappe.db.exists.return_value = False
	frappe.get_doc = Mock()
	frappe.get_all = Mock()
	frappe.get_cached_value = Mock(return_value=0)
	utils = module("frappe.utils")
	utils.flt = flt
	utils.cint = lambda x: int(x or 0)
	module("frappe.custom.doctype.custom_field.custom_field").create_custom_fields = Mock()
	module("erpnext.stock.get_item_details").get_conversion_factor = lambda *_: {"conversion_factor": 1}
	standard = module("erpnext.accounts.report.gross_profit.gross_profit")
	path = os.environ.get("UPSTREAM_GP_SOURCE")
	if path:
		tree = ast.parse(Path(path).read_text())
		tree.body = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
		standard.__dict__.update(
			frappe=frappe,
			flt=flt,
			cint=utils.cint,
			scrub=lambda s: s.lower().replace(" ", "_"),
			OrderedDict=OrderedDict,
			_=lambda s: s,
			formatdate=lambda d, fmt: str(d)[:7],
			_get_incoming_rate=lambda args: 0,
		)
		exec(compile(tree, path, "exec"), standard.__dict__)
	else:

		class Base:
			def load_invoice_items(self):
				pass

			def get_buying_amount(self, row, item_code):
				return 77

		standard.GrossProfitGenerator = Base
	return frappe, standard


frappe, standard = install()
