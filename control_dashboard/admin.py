# control_dashboard/admin.py

from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['email', 'full_name', 'position', 'role', 'status', 'created_at']
    list_filter = ['role', 'position', 'status']
    search_fields = ['email', 'full_name']
    readonly_fields = ['created_at', 'updated_at']
    fields = ['email', 'full_name', 'position', 'role', 'status']