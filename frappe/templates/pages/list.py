# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from frappe.website.render import resolve_path
from frappe import _

no_cache = 1
no_sitemap = 1

def get_context(context):
	"""Returns context for a list standard list page.
	Will also update `get_list_context` from the doctype module file"""
	doctype = frappe.local.form_dict.doctype

	context.update(get_list_context(context, doctype) or {})

	context.doctype = doctype
	context.txt = frappe.local.form_dict.txt

	context.update(get(**frappe.local.form_dict))

@frappe.whitelist(allow_guest=True)
def get(doctype, txt=None, limit_start=0, **kwargs):
	"""Returns processed HTML page for a standard listing."""
	limit_start = cint(limit_start)
	limit_page_length = 20
	next_start = limit_start + limit_page_length

	filters = frappe._dict(kwargs)
	if filters.pathname:
		# resolve additional filters from path
		resolve_path(filters.pathname)
		for key, val in frappe.local.form_dict.items():
			if key in ("cmd", "pathname", "doctype", "txt", "limit_start"):
				if key in filters:
					del filters[key]

			elif key not in filters:
				filters[key] = val

	meta = frappe.get_meta(doctype)
	list_context = get_list_context({}, doctype)

	if list_context.filters:
		filters.update(list_context.filters)

	_get_list = list_context.get_list or get_list

	raw_result = _get_list(doctype=doctype, txt=txt, filters=filters,
		limit_start=limit_start, limit_page_length=limit_page_length)

	show_more = (_get_list(doctype=doctype, txt=txt, filters=filters,
		limit_start=next_start, limit_page_length=1) and True or False)

	if txt:
		list_context.default_subtitle = _('Filtered by "{0}"').format(txt)

	result = []
	row_template = list_context.row_template or "templates/includes/list/row_template.html"
	for doc in raw_result:
		doc.doctype = doctype
		new_context = { "doc": doc, "meta": meta, "pathname": frappe.local.request.path.strip("/ ") }
		new_context.update(list_context)
		rendered_row = frappe.render_template(row_template, new_context, is_path=True)
		result.append(rendered_row)

	return {
		"result": result,
		"show_more": show_more,
		"next_start": next_start
	}

def get_list_context(context, doctype):
	from frappe.modules import load_doctype_module
	module = load_doctype_module(doctype)
	if hasattr(module, "get_list_context"):
		return frappe._dict(module.get_list_context(context) or {})

	return frappe._dict()

def get_list(doctype, txt, filters, limit_start, limit_page_length=20, ignore_permissions=False):
	meta = frappe.get_meta(doctype)
	if not filters:
		filters = []

	or_filters = []

	if txt:
		if meta.search_fields:
			for f in meta.get_search_fields():
				or_filters.append([doctype, f.strip(), "like", "%" + txt + "%"])
		else:
			if isinstance(filters, dict):
				filters["name"] = ("like", "%" + txt + "%")
			else:
				filters.append([doctype, "name", "like", "%" + txt + "%"])

	return frappe.get_list(doctype, fields = "distinct *",
		filters=filters, or_filters=or_filters, limit_start=limit_start,
		limit_page_length = limit_page_length, ignore_permissions=ignore_permissions)

