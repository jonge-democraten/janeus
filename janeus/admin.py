from django.contrib import admin
from janeus.models import JaneusUser, JaneusRole


class JaneusRoleAdmin(admin.ModelAdmin):
    search_fields = ('role',)
    ordering = ('role',)
    filter_horizontal = ('groups', 'permissions', 'sites')


admin.site.register(JaneusUser)
admin.site.register(JaneusRole, JaneusRoleAdmin)
