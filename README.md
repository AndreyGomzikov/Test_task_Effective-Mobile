# Custom Auth Backend

Backend-приложение реализует собственную систему аутентификации и авторизации на Django REST Framework и PostgreSQL.

## Идея

В проекте не используется стандартная модель Django User, Django Groups и Django Permissions как основа разграничения доступа. Вместо этого созданы собственные таблицы:

- `app_users` — пользователи системы.
- `sessions` — активные сессии пользователей. После login создается запись в этой таблице, а JWT содержит `sid` с идентификатором сессии.
- `roles` — роли пользователей: `admin`, `manager`, `user`, `guest`.
- `user_roles` — связь пользователей с ролями.
- `business_elements` — ресурсы приложения, к которым применяется доступ: `users`, `products`, `orders`, `access_rules`.
- `access_roles_rules` — правила доступа роли к ресурсу.

## Смысл permission-полей

Таблица `access_roles_rules` содержит следующие boolean-поля:

- `read_permission` — можно читать собственные объекты.
- `read_all_permission` — можно читать все объекты ресурса.
- `create_permission` — можно создавать объекты ресурса.
- `update_permission` — можно изменять собственные объекты.
- `update_all_permission` — можно изменять все объекты ресурса.
- `delete_permission` — можно удалять собственные объекты.
- `delete_all_permission` — можно удалять все объекты ресурса.

Под собственным объектом понимается объект, у которого `owner_id` совпадает с `id` текущего пользователя. В демонстрационной части бизнес-таблицы не создаются, поэтому товары реализованы как mock-объекты в коде.

## Правила ошибок

- Если endpoint требует пользователя, но по токену невозможно определить активного пользователя, возвращается `401 Unauthorized`.
- Если пользователь определен, но по таблице `access_roles_rules` у него нет права на действие, возвращается `403 Forbidden`.
- Если пользователь мягко удален, его `is_active=False`, все активные сессии закрываются, и повторный login невозможен.

## API

### Пользователь

- `POST /api/auth/register/` — регистрация.
- `POST /api/auth/login/` — вход, возвращает Bearer JWT.
- `POST /api/auth/logout/` — выход, закрывает текущую сессию.
- `GET /api/auth/profile/` — получить профиль.
- `PATCH /api/auth/profile/` — обновить профиль.
- `DELETE /api/auth/profile/` — мягко удалить аккаунт.

### Администрирование доступа

Доступно только пользователю с ролью `admin`.

- `GET /api/admin/roles/` — список ролей.
- `POST /api/admin/roles/` — создать роль.
- `GET /api/admin/elements/` — список ресурсов.
- `POST /api/admin/elements/` — создать ресурс.
- `GET /api/admin/access-rules/` — список правил доступа.
- `POST /api/admin/access-rules/` — создать правило доступа.
- `PATCH /api/admin/access-rules/{id}/` — изменить правило доступа.
- `DELETE /api/admin/access-rules/{id}/` — удалить правило доступа.

### Mock-бизнес-объекты

- `GET /api/products/` — список товаров. Требуется `read_all_permission` для ресурса `products`.
- `POST /api/products/` — создать mock-товар. Требуется `create_permission`.
- `GET /api/products/{id}/` — получить mock-товар. Требуется `read_all_permission` или `read_permission`, если объект свой.
- `PATCH /api/products/{id}/` — изменить mock-товар. Требуется `update_all_permission` или `update_permission`, если объект свой.
- `DELETE /api/products/{id}/` — удалить mock-товар. Требуется `delete_all_permission` или `delete_permission`, если объект свой.

## Запуск

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

docker compose up -d
python manage.py makemigrations
python manage.py migrate
python manage.py seed_access
python manage.py runserver
```

Для Windows вместо `source venv/bin/activate` используйте:

```bash
venv\Scripts\activate
```

## Тестовые пользователи

После команды `seed_access` создаются:

- Администратор: `admin@example.com` / `Admin12345`
- Обычный пользователь: `user@example.com` / `User12345`

## Пример login

```http
POST /api/auth/login/
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "Admin12345"
}
```

В последующих запросах нужно передавать токен:

```http
Authorization: Bearer <access_token>
```

