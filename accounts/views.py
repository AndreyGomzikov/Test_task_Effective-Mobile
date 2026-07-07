from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import (
    AccessRoleRule,
    AppUser,
    BusinessElement,
    Role,
    Session,
    UserRole,
)
from accounts.permissions import (
    PERMISSION_FIELDS,
    get_current_session,
    get_current_user,
    has_access,
    user_is_admin,
)
from accounts.security import (
    check_password,
    create_token_for_user,
    hash_password,
)


MOCK_PRODUCTS = [
    {'id': 1, 'owner_id': 1, 'name': 'Laptop Lenovo', 'price': 95000},
    {'id': 2, 'owner_id': 2, 'name': 'Keyboard Logitech', 'price': 7000},
    {'id': 3, 'owner_id': 2, 'name': 'Monitor Samsung', 'price': 24000},
]


def error_response(message, code):
    return Response({'detail': message}, status=code)


def unauthorized():
    return error_response(
        'Пользователь не авторизован',
        status.HTTP_401_UNAUTHORIZED,
    )


def forbidden():
    return error_response(
        'Недостаточно прав доступа',
        status.HTTP_403_FORBIDDEN,
    )


def validate_required(data, fields):
    missing = [field for field in fields if not data.get(field)]
    return missing


def serialize_user(user):
    return {
        'id': user.id,
        'last_name': user.last_name,
        'first_name': user.first_name,
        'middle_name': user.middle_name,
        'email': user.email,
        'is_active': user.is_active,
    }


def serialize_role(role):
    return {
        'id': role.id,
        'code': role.code,
        'name': role.name,
        'description': role.description,
    }


def serialize_element(element):
    return {
        'id': element.id,
        'code': element.code,
        'name': element.name,
        'description': element.description,
    }


def serialize_rule(rule):
    result = {
        'id': rule.id,
        'role': serialize_role(rule.role),
        'element': serialize_element(rule.element),
    }

    for field in PERMISSION_FIELDS:
        result[field] = getattr(rule, field)

    return result


def require_admin(request):
    user = get_current_user(request)

    if user is None:
        return None, unauthorized()

    if not user_is_admin(user):
        return None, forbidden()

    return user, None


class RegisterView(APIView):
    def post(self, request):
        data = request.data
        missing = validate_required(
            data,
            [
                'last_name',
                'first_name',
                'email',
                'password',
                'password_repeat',
            ],
        )

        if missing:
            return error_response(
                {'missing_fields': missing},
                status.HTTP_400_BAD_REQUEST,
            )

        if data['password'] != data['password_repeat']:
            return error_response(
                'Пароли не совпадают',
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = AppUser.objects.create(
                last_name=data['last_name'],
                first_name=data['first_name'],
                middle_name=data.get('middle_name', ''),
                email=data['email'].lower(),
                password_hash=hash_password(data['password']),
            )
            default_role = Role.objects.filter(code='user').first()

            if default_role:
                UserRole.objects.create(user=user, role=default_role)
        except IntegrityError:
            return error_response(
                'Пользователь с таким email уже существует',
                status.HTTP_400_BAD_REQUEST,
            )

        return Response(serialize_user(user), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    def post(self, request):
        data = request.data
        missing = validate_required(data, ['email', 'password'])

        if missing:
            return error_response(
                {'missing_fields': missing},
                status.HTTP_400_BAD_REQUEST,
            )

        user = AppUser.objects.filter(
            email=data['email'].lower(),
            is_active=True,
        ).first()

        if user is None or not check_password(
            data['password'],
            user.password_hash,
        ):
            return error_response(
                'Неверный email или пароль',
                status.HTTP_401_UNAUTHORIZED,
            )

        token, session = create_token_for_user(user)

        return Response(
            {
                'token_type': 'Bearer',
                'access_token': token,
                'expires_at': session.expires_at,
                'user': serialize_user(user),
            },
        )


class LogoutView(APIView):
    def post(self, request):
        session = get_current_session(request)

        if session is None:
            return unauthorized()

        session.close()

        return Response({'detail': 'Выход выполнен'})


class ProfileView(APIView):
    def get(self, request):
        user = get_current_user(request)

        if user is None:
            return unauthorized()

        return Response(serialize_user(user))

    def patch(self, request):
        user = get_current_user(request)

        if user is None:
            return unauthorized()

        allowed_fields = ['last_name', 'first_name', 'middle_name', 'email']

        for field in allowed_fields:
            if field in request.data:
                setattr(user, field, request.data[field])

        try:
            user.save(update_fields=allowed_fields + ['updated_at'])
        except IntegrityError:
            return error_response(
                'Такой email уже используется',
                status.HTTP_400_BAD_REQUEST,
            )

        return Response(serialize_user(user))

    def delete(self, request):
        user = get_current_user(request)

        if user is None:
            return unauthorized()

        user.soft_delete()

        Session.objects.filter(
            user=user,
            is_active=True,
        ).update(
            is_active=False,
            logged_out_at=timezone.now(),
        )

        return Response(
            {
                'detail': (
                    'Аккаунт мягко удален. '
                    'Повторный вход запрещен.'
                ),
            },
        )


class RoleListView(APIView):
    def get(self, request):
        _, admin_error = require_admin(request)

        if admin_error:
            return admin_error

        roles = Role.objects.all().order_by('id')

        return Response([serialize_role(role) for role in roles])

    def post(self, request):
        _, admin_error = require_admin(request)

        if admin_error:
            return admin_error

        missing = validate_required(request.data, ['code', 'name'])

        if missing:
            return error_response(
                {'missing_fields': missing},
                status.HTTP_400_BAD_REQUEST,
            )

        role = Role.objects.create(
            code=request.data['code'],
            name=request.data['name'],
            description=request.data.get('description', ''),
        )

        return Response(serialize_role(role), status=status.HTTP_201_CREATED)


class ElementListView(APIView):
    def get(self, request):
        _, admin_error = require_admin(request)

        if admin_error:
            return admin_error

        elements = BusinessElement.objects.all().order_by('id')

        return Response(
            [serialize_element(element) for element in elements],
        )

    def post(self, request):
        _, admin_error = require_admin(request)

        if admin_error:
            return admin_error

        missing = validate_required(request.data, ['code', 'name'])

        if missing:
            return error_response(
                {'missing_fields': missing},
                status.HTTP_400_BAD_REQUEST,
            )

        element = BusinessElement.objects.create(
            code=request.data['code'],
            name=request.data['name'],
            description=request.data.get('description', ''),
        )

        return Response(
            serialize_element(element),
            status=status.HTTP_201_CREATED,
        )


class AccessRuleListView(APIView):
    def get(self, request):
        _, admin_error = require_admin(request)

        if admin_error:
            return admin_error

        rules = AccessRoleRule.objects.select_related(
            'role',
            'element',
        ).all().order_by('id')

        return Response([serialize_rule(rule) for rule in rules])

    def post(self, request):
        _, admin_error = require_admin(request)

        if admin_error:
            return admin_error

        missing = validate_required(request.data, ['role_id', 'element_id'])

        if missing:
            return error_response(
                {'missing_fields': missing},
                status.HTTP_400_BAD_REQUEST,
            )

        rule_data = self._extract_rule_data(request.data)

        try:
            rule = AccessRoleRule.objects.create(
                role_id=request.data['role_id'],
                element_id=request.data['element_id'],
                **rule_data,
            )
        except IntegrityError:
            return error_response(
                'Правило для этой роли и ресурса уже существует',
                status.HTTP_400_BAD_REQUEST,
            )

        return Response(serialize_rule(rule), status=status.HTTP_201_CREATED)

    @staticmethod
    def _extract_rule_data(data):
        result = {}

        for field in PERMISSION_FIELDS:
            if field in data:
                result[field] = bool(data[field])

        return result


class AccessRuleDetailView(APIView):
    def patch(self, request, rule_id):
        _, admin_error = require_admin(request)

        if admin_error:
            return admin_error

        rule = AccessRoleRule.objects.select_related(
            'role',
            'element',
        ).filter(
            id=rule_id,
        ).first()

        if rule is None:
            return error_response(
                'Правило не найдено',
                status.HTTP_404_NOT_FOUND,
            )

        for field in PERMISSION_FIELDS:
            if field in request.data:
                setattr(rule, field, bool(request.data[field]))

        rule.save(update_fields=PERMISSION_FIELDS)

        return Response(serialize_rule(rule))

    def delete(self, request, rule_id):
        _, admin_error = require_admin(request)

        if admin_error:
            return admin_error

        deleted, _ = AccessRoleRule.objects.filter(id=rule_id).delete()

        if deleted == 0:
            return error_response(
                'Правило не найдено',
                status.HTTP_404_NOT_FOUND,
            )

        return Response({'detail': 'Правило удалено'})


class ProductListView(APIView):
    element_code = 'products'

    def get(self, request):
        allowed, error_code = has_access(
            get_current_user(request),
            self.element_code,
            'read_all',
        )

        if not allowed:
            return unauthorized() if error_code == 401 else forbidden()

        return Response(MOCK_PRODUCTS)

    def post(self, request):
        user = get_current_user(request)
        allowed, error_code = has_access(
            user,
            self.element_code,
            'create',
        )

        if not allowed:
            return unauthorized() if error_code == 401 else forbidden()

        product = {
            'id': max(item['id'] for item in MOCK_PRODUCTS) + 1,
            'owner_id': user.id,
            'name': request.data.get('name', 'New product'),
            'price': request.data.get('price', 0),
        }

        return Response(product, status=status.HTTP_201_CREATED)


class ProductDetailView(APIView):
    element_code = 'products'

    def get(self, request, product_id):
        product = self._find_product(product_id)

        if product is None:
            return error_response(
                'Товар не найден',
                status.HTTP_404_NOT_FOUND,
            )

        allowed, error_code = has_access(
            get_current_user(request),
            self.element_code,
            'read',
            product['owner_id'],
        )

        if not allowed:
            return unauthorized() if error_code == 401 else forbidden()

        return Response(product)

    def patch(self, request, product_id):
        product = self._find_product(product_id)

        if product is None:
            return error_response(
                'Товар не найден',
                status.HTTP_404_NOT_FOUND,
            )

        allowed, error_code = has_access(
            get_current_user(request),
            self.element_code,
            'update',
            product['owner_id'],
        )

        if not allowed:
            return unauthorized() if error_code == 401 else forbidden()

        updated = {**product, **request.data}

        return Response(updated)

    def delete(self, request, product_id):
        product = self._find_product(product_id)

        if product is None:
            return error_response(
                'Товар не найден',
                status.HTTP_404_NOT_FOUND,
            )

        allowed, error_code = has_access(
            get_current_user(request),
            self.element_code,
            'delete',
            product['owner_id'],
        )

        if not allowed:
            return unauthorized() if error_code == 401 else forbidden()

        return Response({'detail': 'Mock-товар удален'})

    @staticmethod
    def _find_product(product_id):
        return next(
            (
                item
                for item in MOCK_PRODUCTS
                if item['id'] == product_id
            ),
            None,
        )
