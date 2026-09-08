"""
Registry مرکزی برای اتصال مدل‌ها به Policy و Resolverهای Scope.

هدف: Authorization Engine نباید بداند Member یا EmploymentAssignment
چگونه به HealthHouse وصل می‌شوند؛ هر اپ خودش این را در startup
register می‌کند.
"""

_POLICY_REGISTRY = {}
_HEALTH_HOUSE_RESOLVERS = {}
_QUERYSET_SCOPE_RESOLVERS = {}


def register_policy(model, policy_instance):
    _POLICY_REGISTRY[model] = policy_instance


def get_policy_for(obj):
    return _POLICY_REGISTRY.get(type(obj))


def register_health_house_resolver(model, resolver):
    """resolver(obj) -> QuerySet[HealthHouse] مرتبط با این آبجکت"""
    _HEALTH_HOUSE_RESOLVERS[model] = resolver


def get_object_health_houses(obj):
    resolver = _HEALTH_HOUSE_RESOLVERS.get(type(obj))
    if resolver is None:
        return None
    return resolver(obj)


def register_queryset_scope_resolver(model, resolver):
    """resolver(queryset, house_ids) -> QuerySet محدودشده"""
    _QUERYSET_SCOPE_RESOLVERS[model] = resolver


def get_queryset_scope_resolver(model):
    return _QUERYSET_SCOPE_RESOLVERS.get(model)