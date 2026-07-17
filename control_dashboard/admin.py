from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['email', 'full_name', 'position', 'role', 'status', 'created_at']
    list_filter = ['position', 'role', 'status']
    search_fields = ['email', 'full_name']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {
            'fields': ('email', 'full_name')
        }),
        ('Permissions', {
            'fields': ('position', 'role', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']