import frappe
from frappe.utils import cint, cstr, flt, random_string
import json
from erpnext.setup.doctype.item_group.item_group import (
	get_parent_item_groups,
	invalidate_cache_for,
)
from frappe.website.doctype.website_slideshow.website_slideshow import get_slideshow
from erpnext.e_commerce.doctype.item_review.item_review import get_item_reviews
from erpnext.e_commerce.doctype.website_item.website_item import WebsiteGenerator, set_attribute_context, get_context, check_if_user_is_customer

class WebsiteItem(WebsiteGenerator):

    def set_attribute_context(self, context):
            if not self.has_variants:
                return

            attribute_values_available = {}
            context.attribute_values = {}
            context.selected_attributes = {}

            # load attributes
            for v in context.variants:
                v.attributes = frappe.get_all("Item Variant Attribute",
                    fields=["attribute", "attribute_value"],
                    filters={"parent": v.name})
                # make a map for easier access in templates
                v.attribute_map = frappe._dict({})
                for attr in v.attributes:
                    v.attribute_map[attr.attribute] = attr.attribute_value

                for attr in v.attributes:
                    values = attribute_values_available.setdefault(attr.attribute, [])
                    if attr.attribute_value not in values:
                        values.append(attr.attribute_value)

                    if v.name == context.variant.name:
                        context.selected_attributes[attr.attribute] = attr.attribute_value

            # filter attributes, order based on attribute table
            for attr in self.attributes:
                values = context.attribute_values.setdefault(attr.attribute, [])

                if cint(frappe.db.get_value("Item Attribute", attr.attribute, "numeric_values")):
                    for val in sorted(attribute_values_available.get(attr.attribute, []), key=flt):
                        values.append(val)

                else:
                    # get list of values defined (for sequence)
                    for attr_value in frappe.db.get_all("Item Attribute Value",
                        fields=["attribute_value"],
                        filters={"parent": attr.attribute}, order_by="idx asc"):

                        if attr_value.attribute_value in attribute_values_available.get(attr.attribute, []):
                            values.append(attr_value.attribute_value)

            context.variant_info = json.dumps(context.variants)

    def get_context(self, context):
            context.show_search = True
            context.search_link = "/search"
            context.body_class = "product-page"

            context.variants = frappe.db.get_all("Item", fields=["item_code"], filters={"variant_of": self.item_code})
            if self.has_variants:
                context.variant = context.variants[0]
            context.parents = get_parent_item_groups(self.item_group, from_item=True)  # breadcumbs

            context.attributes = self.attributes = frappe.get_all(
                "Item Variant Attribute",
                fields=["attribute", "attribute_value"],
                filters={"parent": self.item_code},
            )
            set_attribute_context(self, context)

            if self.slideshow:
                context.update(get_slideshow(self))

            self.set_metatags(context)
            self.set_shopping_cart_data(context)

            settings = context.shopping_cart.cart_settings

            self.get_product_details_section(context)

            if settings.get("enable_reviews"):
                reviews_data = get_item_reviews(self.name)
                context.update(reviews_data)
                context.reviews = context.reviews[:4]

            context.wished = False
            if frappe.db.exists(
                "Wishlist Item", {"item_code": self.item_code, "parent": frappe.session.user}
            ):
                context.wished = True

            context.user_is_customer = check_if_user_is_customer()

            context.recommended_items = None
            if settings and settings.enable_recommendations:
                context.recommended_items = self.get_recommended_items(settings)

            return context

    def check_if_user_is_customer(user=None):
        from frappe.contacts.doctype.contact.contact import get_contact_name

        if not user:
            user = frappe.session.user

        contact_name = get_contact_name(user)
        customer = None

        if contact_name:
            contact = frappe.get_doc("Contact", contact_name)
            for link in contact.links:
                if link.link_doctype == "Customer":
                    customer = link.link_name
                    break

        return True if customer else False
