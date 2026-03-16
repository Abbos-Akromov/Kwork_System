from django.urls import path
from . import views

app_name = 'programmer'

urlpatterns = [
    path('services/',             views.ServiceListView.as_view(),   name='service_list'),
    path('services/create/',      views.ServiceCreateView.as_view(), name='service_create'),
    path('services/<int:pk>/edit/',   views.ServiceUpdateView.as_view(), name='service_edit'),
    path('services/<int:pk>/delete/', views.ServiceDeleteView.as_view(), name='service_delete'),
    path('portfolio/',                views.PortfolioListView.as_view(),  name='portfolio_list'),
    path('portfolio/create/',         views.PortfolioCreateView.as_view(), name='portfolio_create'),
    path('portfolio/<int:pk>/edit/',  views.PortfolioUpdateView.as_view(), name='portfolio_edit'),
    path('portfolio/<int:pk>/delete/', views.PortfolioDeleteView.as_view(), name='portfolio_delete'),
]