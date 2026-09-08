from django import template

from .. import selectors

register = template.Library()


@register.simple_tag
def reaction_summary(user, target):
    return selectors.get_reaction_summary(user, target)