from django.core.management.base import BaseCommand

from accounts.models import (
    AccessRoleRule,
    AppUser,
    BusinessElement,
    Role,
    UserRole,
)
from accounts.security import hash_password


class Command(BaseCommand):
    help = (
        'Создает тестовые роли, ресурсы, правила доступа '
        'и пользователей'
    )

    def handle(self, *args, **options):
        roles = self._create_roles()
        elements = self._create_elements()

        self._create_rules(roles, elements)
        self._create_users(roles)

        self.stdout.write(self.style.SUCCESS('Тестовые данные созданы'))
        self.stdout.write('Admin: admin@example.com / Admin12345')
        self.stdout.write('User: user@example.com / User12345')

    @staticmethod
    def _create_roles():
        data = [
            ('admin', 'Администратор', 'Полный доступ к системе'),
            (
                'manager',
                'Менеджер',
                'Управление товарами без изменения правил доступа',
            ),
            (
                'user',
                'Пользователь',
                'Работа только с разрешенными объектами',
            ),
            ('guest', 'Гость', 'Минимальные права'),
        ]

        result = {}

        for code, name, description in data:
            role, _ = Role.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'description': description,
                },
            )
            result[code] = role

        return result

    @staticmethod
    def _create_elements():
        data = [
            ('users', 'Пользователи', 'Профили пользователей'),
            ('products', 'Товары', 'Mock-объекты бизнес-приложения'),
            ('orders', 'Заказы', 'Потенциальные заказы'),
            (
                'access_rules',
                'Правила доступа',
                'Роли, ресурсы и разрешения',
            ),
        ]

        result = {}

        for code, name, description in data:
            element, _ = BusinessElement.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'description': description,
                },
            )
            result[code] = element

        return result

    @staticmethod
    def _upsert_rule(role, element, **permissions):
        defaults = {
            'read_permission': False,
            'read_all_permission': False,
            'create_permission': False,
            'update_permission': False,
            'update_all_permission': False,
            'delete_permission': False,
            'delete_all_permission': False,
        }
        defaults.update(permissions)

        AccessRoleRule.objects.update_or_create(
            role=role,
            element=element,
            defaults=defaults,
        )

    def _create_rules(self, roles, elements):
        for element in elements.values():
            self._upsert_rule(
                roles['admin'],
                element,
                read_permission=True,
                read_all_permission=True,
                create_permission=True,
                update_permission=True,
                update_all_permission=True,
                delete_permission=True,
                delete_all_permission=True,
            )

        self._upsert_rule(
            roles['manager'],
            elements['products'],
            read_permission=True,
            read_all_permission=True,
            create_permission=True,
            update_permission=True,
            update_all_permission=True,
            delete_permission=False,
            delete_all_permission=False,
        )

        self._upsert_rule(
            roles['manager'],
            elements['orders'],
            read_permission=True,
            read_all_permission=True,
            update_permission=True,
            update_all_permission=True,
        )

        self._upsert_rule(
            roles['user'],
            elements['products'],
            read_permission=True,
            read_all_permission=True,
            create_permission=True,
            update_permission=True,
            delete_permission=True,
        )

        self._upsert_rule(
            roles['guest'],
            elements['products'],
            read_permission=False,
            read_all_permission=True,
        )

    @staticmethod
    def _create_users(roles):
        admin, _ = AppUser.objects.get_or_create(
            email='admin@example.com',
            defaults={
                'last_name': 'Admin',
                'first_name': 'System',
                'middle_name': '',
                'password_hash': hash_password('Admin12345'),
            },
        )

        user, _ = AppUser.objects.get_or_create(
            email='user@example.com',
            defaults={
                'last_name': 'User',
                'first_name': 'Test',
                'middle_name': '',
                'password_hash': hash_password('User12345'),
            },
        )

        UserRole.objects.get_or_create(
            user=admin,
            role=roles['admin'],
        )
        UserRole.objects.get_or_create(
            user=user,
            role=roles['user'],
        )
