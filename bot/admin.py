from django.contrib import admin
from .models import Project, ReferralUser, Settings


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False if self.model.objects.count() > 0\
                     else super().has_add_permission(request)


admin.site.register(Project)
admin.site.register(ReferralUser)
