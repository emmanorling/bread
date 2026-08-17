from .models import SiteSetting

def site_settings(request):
    settings, _ = SiteSetting.objects.get_or_create(id=1)
    return {
        'show_dough_section': settings.show_dough_section
    }
