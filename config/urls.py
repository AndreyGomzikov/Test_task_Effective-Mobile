from django.urls import path
from accounts.views import (
    AccessRuleDetailView,
    AccessRuleListView,
    ElementListView,
    LoginView,
    LogoutView,
    ProductDetailView,
    ProductListView,
    ProfileView,
    RegisterView,
    RoleListView,
)

urlpatterns = [
    path('api/auth/register/', RegisterView.as_view()),
    path('api/auth/login/', LoginView.as_view()),
    path('api/auth/logout/', LogoutView.as_view()),
    path('api/auth/profile/', ProfileView.as_view()),

    path('api/admin/roles/', RoleListView.as_view()),
    path('api/admin/elements/', ElementListView.as_view()),
    path('api/admin/access-rules/', AccessRuleListView.as_view()),
    path('api/admin/access-rules/<int:rule_id>/', AccessRuleDetailView.as_view()),

    path('api/products/', ProductListView.as_view()),
    path('api/products/<int:product_id>/', ProductDetailView.as_view()),
]
