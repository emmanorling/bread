from django.shortcuts import render
from django.utils import timezone
from .models import BreadMachine, Loaf

def public_dashboard(request):
    now = timezone.now()
    
    # Active loaves (still baking)
    active_loaves = Loaf.objects.filter(ready_at__gt=now).select_related('machine')
    
    # History (finished baking)
    history_loaves = Loaf.objects.filter(ready_at__lte=now).order_by('-ready_at')[:20]
    
    # Machines currently in use
    active_machine_ids = active_loaves.values_list('machine_id', flat=True)
    all_machines = BreadMachine.objects.all()
    
    context = {
        'active_loaves': active_loaves,
        'history_loaves': history_loaves,
        'all_machines': all_machines,
        'active_machine_ids': active_machine_ids,
    }
    return render(request, 'dashboard.html', context)
