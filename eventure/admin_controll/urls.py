from django.urls import path
from admin_controll import views



urlpatterns = [
   path('login/',  views.admin_login_view, name='admin_login'),
   path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
   path('user-management/', views.user_management, name='user_management'),
   path('toggle-block/<int:user_id>/', views.toggle_block_user, name='toggle_block_user'),
   path('events/', views.event_list, name='admin_event_list'),
   path('subscriptions/',views.subscription_list, name='subscription_list'),
   path('event-tickets/', views.ticket_list, name='ticket_list'),
   path('admin/logout/',views.admin_logout_view, name='admin_logout'),
   
]