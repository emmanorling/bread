from django.utils import timezone
from django.http import JsonResponse
from .models import BreadMachine, Loaf
from .forms import CommentForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count

def api_bread_status(request):
    now = timezone.now()
    machines = BreadMachine.objects.all()
    data = []

    for machine in machines:
        # Match the dashboard logic: find an active loaf finishing in the future
        active_loaf = Loaf.objects.filter(machine=machine, ready_at__gt=now).first()
        
        data.append({
            "name": machine.name,
            "status": "Baking" if active_loaf else "Idle",
            "loaf": active_loaf.bread_type if active_loaf else None,
            "ready_at": active_loaf.ready_at.strftime("%H:%M") if (active_loaf and active_loaf.ready_at) else None
        })

    return JsonResponse({"machines": data})

def api_bread_history(request):
    now = timezone.now()
    history_loaves = Loaf.objects.filter(ready_at__lte=now).select_related('machine').order_by('-ready_at')[:20]
    data = []

    for loaf in history_loaves:
        data.append({
            "name": loaf.bread_type,
            "date": loaf.ready_at.strftime("%d %b") if loaf.ready_at else "",
            "machine": loaf.machine.name if loaf.machine else "Unknown",
            "notes": getattr(loaf, 'notes', '')  # Uses loaf.notes if field exists
        })
        
    return JsonResponse({"history": data})

def loaf_detail(request, loaf_id):
    loaf = get_object_or_404(Loaf, id=loaf_id)
    comments = loaf.comments.all()  # Fetches all comments for this loaf
    
    if request.method == 'POST':
        # Ensure only logged-in users can post
        if not request.user.is_authenticated:
            return redirect('login')
            
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.loaf = loaf
            comment.author = request.user
            comment.save()
            return redirect('loaf_detail', loaf_id=loaf.id)
    else:
        form = CommentForm()

    return render(request, 'loaf_detail.html', {
        'loaf': loaf,
        'comments': comments,
        'form': form
    })

@login_required
def add_comment(request, loaf_id):
    loaf = get_object_or_404(Loaf, id=loaf_id)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.loaf = loaf
            comment.author = request.user  # Automatically assigns the logged-in user
            comment.save()
    return redirect('loaf_detail', loaf_id=loaf.id)

def public_dashboard(request):
    now = timezone.now()
    
    # Active loaves (still baking)
    active_loaves = Loaf.objects.filter(ready_at__gt=now).select_related('machine')
    
    # History (finished baking)
    history_loaves = Loaf.objects.filter(ready_at__lte=now).annotate(
        comment_count=Count('comments')
        ).order_by('-ready_at')[:20]
    
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
