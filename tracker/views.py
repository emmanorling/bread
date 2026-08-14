from django.utils import timezone
from django.utils.timezone import localtime
from django.http import JsonResponse
from .models import BreadMachine, Loaf
from .forms import CommentForm, LoafForm, LoafEditForm, BreadMachineForm, UserProfileForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

def api_bread_status(request):
    now = timezone.now()
    machines = BreadMachine.objects.all()
    data = []

    for machine in machines:
        active_loaf = Loaf.objects.filter(machine=machine, ready_at__gt=now).first()
        
        ready_str = None
        if active_loaf and active_loaf.ready_at:
            diff = active_loaf.ready_at - now
            total_minutes = int(diff.total_seconds() // 60)
            
            if total_minutes <= 0:
                ready_str = "Ready now"
            elif total_minutes < 60:
                ready_str = f"Ready in {total_minutes}m"
            else:
                ready_str = f"Ready at {localtime(active_loaf.ready_at).strftime("%H:%M")}"

        data.append({
            "name": machine.name,
            "status": "Baking" if active_loaf else "Idle",
            "loaf": active_loaf.bread_type if active_loaf else None,
            "ready_at": ready_str  # Returns e.g. "Ready in 45m" or "Ready in 1h 15m"
        })

    return JsonResponse({"machines": data})

def api_bread_history(request):
    now = timezone.now()
    history_loaves = Loaf.objects.filter(ready_at__lte=now).select_related('machine').order_by('-ready_at')[:20]
    data = []

    for loaf in history_loaves:
        # Combine comments into a formatted notes string for the badge
        comment_texts = [f"{c.author.username}: {c.text}" for c in loaf.comments.all()]
        notes_summary = "\n".join(comment_texts) if comment_texts else getattr(loaf, 'notes', 'No notes recorded.')

        data.append({
            "name": loaf.bread_type,
            "date": localtime(loaf.ready_at).strftime("%d %b %H:%M") if loaf.ready_at else "",
            "machine": loaf.machine.name if loaf.machine else "Unknown",
            "notes": notes_summary
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

@permission_required('tracker.add_loaf', raise_exception=True)
def add_loaf(request):
    # Get pre-selected machine ID from URL query params (if present)
    machine_id = request.GET.get('machine_id')
    initial_data = {}
    if machine_id:
        initial_data['machine'] = machine_id

    if request.method == 'POST':
        form = LoafForm(request.POST)
        if form.is_valid():
            loaf = form.save()
            
            # Save optional initial note as first comment
            note_text = form.cleaned_data.get('initial_note')
            if note_text:
                Comment.objects.create(
                    loaf=loaf,
                    author=request.user,
                    text=note_text
                )
                
            return redirect('dashboard')
    else:
        form = LoafForm(initial=initial_data)  # Pre-selects machine in form

    return render(request, 'loaf_form.html', {'form': form, 'action': 'Start New Loaf'})

@permission_required('tracker.change_loaf', raise_exception=True)
def edit_loaf(request, loaf_id):
    loaf = get_object_or_404(Loaf, id=loaf_id)
    if request.method == 'POST':
        form = LoafEditForm(request.POST, instance=loaf)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = LoafEditForm(instance=loaf)       
    return render(request, 'loaf_form.html', {'form': form, 'action': 'Edit Loaf'})

@permission_required('tracker.delete_loaf', raise_exception=True)
def delete_loaf(request, loaf_id):
    loaf = get_object_or_404(Loaf, id=loaf_id)
    if request.method == 'POST':
        loaf.delete()
        return redirect('dashboard')
    return render(request, 'loaf_confirm_delete.html', {'loaf': loaf})

@permission_required('tracker.add_breadmachine', raise_exception=True)
def add_machine(request):
    if request.method == 'POST':
        # Add request.FILES so uploaded photos are saved
        form = BreadMachineForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = BreadMachineForm()
    return render(request, 'machine_form.html', {'form': form})

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

@login_required
def edit_profile(request):
    if request.method == 'POST':
        # Enforce editing ONLY the currently logged-in user (request.user)
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'profile_form.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Keeps the user logged in after their password changes
            update_session_auth_hash(request, user)
            return redirect('dashboard')
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'password_change_form.html', {'form': form})

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

    # Check if there is at least one machine free to bake
    has_idle_machines = all_machines.exclude(id__in=active_machine_ids).exists()
    
    context = {
        'active_loaves': active_loaves,
        'history_loaves': history_loaves,
        'all_machines': all_machines,
        'active_machine_ids': active_machine_ids,
        'has_idle_machines': has_idle_machines,
    }
    return render(request, 'dashboard.html', context)
