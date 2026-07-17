# ICDD/urls.py

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

# Root view redirect
def home_view(request):
    """Redirect to login page."""
    return redirect('adminboard/login/')

urlpatterns = [
    # Root path - redirect to login
    path('', home_view, name='home'),
    
    # Django admin
    path('admin/', admin.site.urls),
    
    # Your app URLs at adminboard/
    path('adminboard/', include('control_dashboard.urls')),
]