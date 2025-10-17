from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0)

from django import template
from datetime import datetime

register = template.Library()

@register.filter
def month_name(month_number):
    try:
        return datetime(2000, month_number, 1).strftime('%B')
    except:
        return ''