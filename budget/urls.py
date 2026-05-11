from django.urls import path
from . import views

urlpatterns = [
    path("voice-command/", views.voice_command, name="voice_command"),
    path("", views.dashboard, name="dashboard"),
    path("login/", views.login_family, name="login_family"),
    path("register/", views.register_family, name="register_family"),
    path("logout/", views.logout_family, name="logout_family"),
    path("account/", views.account, name="account"),
    path("transactions/", views.transactions, name="transactions"),
    path("transactions/add/", views.add_transaction, name="add_transaction"),
    path("transactions/<int:pk>/edit/", views.edit_transaction, name="edit_transaction"),
    path("transactions/<int:pk>/delete/", views.delete_transaction, name="delete_transaction"),
    path("family/", views.family_members, name="family_members"),
    path("family/<int:pk>/delete/", views.delete_member, name="delete_member"),
    path("categories/", views.categories, name="categories"),
    path("categories/<int:pk>/delete/", views.delete_category, name="delete_category"),
    path("wallets/", views.wallets, name="wallets"),
    path("wallets/<int:pk>/delete/", views.delete_wallet, name="delete_wallet"),
    path("budget/", views.budget_limits, name="budget_limits"),
    path("analytics/", views.analytics, name="analytics"),
]


