from django.urls import path
from . import views

urlpatterns = [
    path('',                            views.overview,     name='dashboard_overview'),
    path('users/',                      views.users,        name='dashboard_users'),
    path('users/<int:user_id>/',        views.user_detail,  name='dashboard_user_detail'),
    path('users/<int:user_id>/action/', views.user_action,  name='dashboard_user_action'),
    path('translations/',               views.translations, name='dashboard_translations'),
    path('settings/',                   views.settings_view,name='dashboard_settings'),
]
