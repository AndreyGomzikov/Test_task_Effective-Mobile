from accounts.models import AccessRoleRule, UserRole


PERMISSION_FIELDS = [
    'read_permission',
    'read_all_permission',
    'create_permission',
    'update_permission',
    'update_all_permission',
    'delete_permission',
    'delete_all_permission',
]


def get_current_user(request):
    user = getattr(request, 'current_user', None)

    if user is None and hasattr(request, '_request'):
        user = getattr(request._request, 'current_user', None)

    return user


def get_current_session(request):
    session = getattr(request, 'current_session', None)

    if session is None and hasattr(request, '_request'):
        session = getattr(request._request, 'current_session', None)

    return session


def user_is_admin(user) -> bool:
    if user is None:
        return False

    return UserRole.objects.filter(
        user=user,
        role__code='admin',
    ).exists()


def get_rules_for_user(user, element_code):
    role_ids = UserRole.objects.filter(
        user=user,
    ).values_list(
        'role_id',
        flat=True,
    )

    return AccessRoleRule.objects.filter(
        role_id__in=role_ids,
        element__code=element_code,
    )


def has_access(
    user,
    element_code: str,
    action: str,
    owner_id=None,
) -> tuple[bool, int | None]:
    if user is None:
        return False, 401

    rules = list(get_rules_for_user(user, element_code))

    if not rules:
        return False, 403

    is_owner = owner_id is not None and int(owner_id) == int(user.id)
    allowed = False

    if action == 'read':
        allowed = any(
            rule.read_all_permission
            or (is_owner and rule.read_permission)
            for rule in rules
        )
    elif action == 'read_all':
        allowed = any(
            rule.read_all_permission
            for rule in rules
        )
    elif action == 'create':
        allowed = any(
            rule.create_permission
            for rule in rules
        )
    elif action == 'update':
        allowed = any(
            rule.update_all_permission
            or (is_owner and rule.update_permission)
            for rule in rules
        )
    elif action == 'delete':
        allowed = any(
            rule.delete_all_permission
            or (is_owner and rule.delete_permission)
            for rule in rules
        )

    if allowed:
        return True, None

    return False, 403
