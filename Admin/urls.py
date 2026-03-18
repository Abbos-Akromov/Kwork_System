from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('',                                views.AdminDashboardView.as_view(),        name='dashboard'),
    path('users/',                          views.AdminUserListView.as_view(),         name='user_list'),
    path('users/<int:pk>/',                 views.AdminUserDetailView.as_view(),       name='user_detail'),
    path('users/<int:pk>/block/',           views.AdminBlockUserView.as_view(),        name='user_block'),
    path('users/<int:pk>/role/',            views.AdminChangeRoleView.as_view(),       name='user_role'),
    path('payments/',                       views.AdminPaymentListView.as_view(),      name='payment_list'),
    path('payments/<uuid:pk>/release/',     views.AdminReleasePaymentView.as_view(),   name='payment_release'),
    path('payments/<uuid:pk>/refund/',      views.AdminRefundPaymentView.as_view(),    name='payment_refund'),
    path('arbitraj/',                       views.AdminArbitrajView.as_view(),         name='arbitraj'),
    path('arbitraj/<uuid:pk>/decide/',      views.AdminArbitrajView.as_view(),         name='arbitraj_decide'),
    path('complaints/',                     views.AdminComplaintListView.as_view(),    name='complaint_list'),
    path('complaints/<int:pk>/',            views.AdminComplaintDetailView.as_view(),  name='complaint_detail'),
    path('complaints/<int:pk>/resolve/',    views.AdminResolveComplaintView.as_view(), name='complaint_resolve'),
    path('settings/',                       views.AdminSettingsView.as_view(),         name='settings'),
]