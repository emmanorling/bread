"""
URL configuration for bread_tracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from tracker import views
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.public_dashboard, name='dashboard'),
    path('loaf/<int:loaf_id>/', views.loaf_detail, name='loaf_detail'),
    path('api/status/', views.api_bread_status, name='api_bread_status'),
    path('api/history/', views.api_bread_history, name='api_bread_history'),
    path('loaf/add/', views.add_loaf, name='add_loaf'),
    path('loaf/<int:loaf_id>/edit/', views.edit_loaf, name='edit_loaf'),
    path('loaf/<int:loaf_id>/delete/', views.delete_loaf, name='delete_loaf'),
    path('machine/add/', views.add_machine, name='add_machine'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/password/', views.change_password, name='change_password'),
    path('request-account/', views.request_account, name='request_account'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
