from django.urls import path
from . import views
from . import admin_views
from .api_views import api_get_user_config

urlpatterns = [
    # Custom Admin URLs
    path('portal/admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('portal/admin/analytics/', admin_views.admin_analytics, name='admin_analytics'),
    path('portal/admin/users/', admin_views.admin_user_list, name='admin_user_list'),
    path('portal/admin/users/<int:user_id>/', admin_views.admin_user_detail, name='admin_user_detail'),
    path('portal/admin/kyc/', admin_views.admin_kyc_list, name='admin_kyc_list'),
    path('portal/admin/kyc/action/', admin_views.admin_kyc_action, name='admin_kyc_action'),
    path('portal/admin/subscriptions/', admin_views.admin_subscription_list, name='admin_subscription_list'),
    path('portal/admin/payments/', admin_views.admin_payment_list, name='admin_payment_list'),
    path('portal/admin/payments/action/', admin_views.admin_payment_action, name='admin_payment_action'),

    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/privacy_policy/<str:email_prefix>/', views.privacy_policy_view, name='privacy_policy'),
    path('wallet/', views.wallet_view, name='wallet'),

    path('ai-agent/', views.ai_agent_view, name='ai_agent'),

    path('feed/', views.feed_view, name='feed'),
    path('create-post/', views.create_post_view, name='create_post'),
    path('report/', views.report_view, name='report'),
    path('report-data/', views.report_data_api, name='report_data_api'),
    path('delete-comment/', views.delete_comment_view, name='delete_comment'),
    path('kyc-required/', views.kyc_required_view, name='kyc_required'),

    
    # API endpoints
    path('api/user/<str:admin_password>/<str:email_prefix>/<str:field>/', api_get_user_config, name='api_user_config'),
    
    # Subscription
    path('subscription-expired/', views.subscription_expired, name='subscription_expired'),
]

