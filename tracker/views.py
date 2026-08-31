### views.py - all the views, in one handy place
###    * api_bread_status and api_bread_history - handy helpers for the tildagon app
###    * request_account
###    * loaf_detail
###    * add_loaf
###    * edit_loaf
###    * delete_loaf
###    * add_comment
###    * edit_comment
###    * delete_comment
###    * edit_profile
###    * change_password
###    * public_dashboard

from django.utils import timezone
from django.utils.timezone import localtime
from django.http import JsonResponse
from .models import BreadMachine, Loaf, Comment, SiteSetting
from .forms import CommentForm, LoafForm, LoafEditForm, BreadMachineForm, UserProfileForm, AccountRequestForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.db.models import Count
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.core.mail import send_mail
from django.contrib.auth.models import User, Group
from django.views.decorators.http import require_POST

# apt_bread_status - used to fetch data about bread machines for the tildagon app
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
                ready_str = f"Ready at {localtime(active_loaf.ready_at).strftime('%H:%M')}"

        data.append({
            "name": machine.name,
            "status": "Baking" if active_loaf else "Idle",
            "loaf": active_loaf.bread_type if active_loaf else None,
            "ready_at": ready_str  # Returns e.g. "Ready in 45m" or "Ready in 1h 15m"
        })

    return JsonResponse({"machines": data})

# api_bread_history - used to fetch data about completed loaves for the tildagon app
@never_cache
def api_bread_history(request):
    # Fetch only finished loaves
    history_loaves = Loaf.objects.filter(status='finished').select_related('machine')[:50]
    
    # Sort them by their actual completed time (descending)
    sorted_loaves = sorted(history_loaves, key=lambda l: l.completed_at, reverse=True)[:20]
    
    data = []
    for loaf in sorted_loaves:
        # Combine comments into a formatted notes string for the badge
        comment_texts = [f"{c.author.username}: {c.text}" for c in loaf.comments.all()]
        notes_summary = "\n".join(comment_texts) if comment_texts else getattr(loaf, 'notes', 'No notes recorded.')

        data.append({
            "name": loaf.bread_type,
            "date": localtime(loaf.completed_at).strftime("%d %b %H:%M") if loaf.completed_at else "",
            "machine": loaf.machine.name if loaf.machine else "Unknown",
            "notes": notes_summary
        })
        
    return JsonResponse({"history": data})

@user_passes_test(lambda u: u.is_superuser)
def toggle_dough_section(request):
    if request.method == 'POST':
        settings, _ = SiteSetting.objects.get_or_create(id=1)
        settings.show_dough_section = not settings.show_dough_section
        settings.save()
    
    # Redirect back to the page the user was previously viewing
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

def request_account(request):
    if request.method == 'POST':
        form = AccountRequestForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = False  # Disabled until admin approves
            user.save()

            # Retrieve the user's explanation
            reason = form.cleaned_data.get('reason', 'No explanation provided.')

            # Add to 'Bread Makers' group
            bread_maker_group, _ = Group.objects.get_or_create(name='Bread Makers')
            user.groups.add(bread_maker_group)

            # Notify Superusers
            superusers = User.objects.filter(is_superuser=True, email__isnull=False).values_list('email', flat=True)
            if superusers:
                send_mail(
                    subject='🍞 New Bread Maker Account Request',
                    message=(
                        f"New request from {user.first_name} {user.last_name} ({user.username}, {user.email}).\n\n"
                        f"--- Reason / Notes ---\n"
                        f"{reason}\n"
                        f"----------------------\n\n"
                        f"Approve or manage user here: https://{request.get_host()}/admin/auth/user/{user.id}/change/"
                    ),
                    from_email=None,  # Uses DEFAULT_FROM_EMAIL from settings
                    recipient_list=list(superusers),
                )

            messages.success(request, "Account request submitted! An admin will review and, if approved, enable your account shortly.")
            return redirect('dashboard')
    else:
        form = AccountRequestForm()

    return render(request, 'account_request.html', {'form': form})

def loaf_detail(request, loaf_id):
    loaf = get_object_or_404(Loaf, id=loaf_id)
    comments = loaf.comments.all().order_by('created_at')  # Fetches all comments for this loaf, in chronological order
    
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
@require_POST
def mark_loaf_removed(request, loaf_id):
    loaf = get_object_or_404(Loaf, pk=loaf_id)
    loaf.is_removed = True
    loaf.removed_from_machine_at = timezone.now()
    
    if loaf.is_dough_only:
        loaf.status = 'proving'
    else:
        loaf.status = 'finished'

    loaf.save()
    return redirect('dashboard')

@login_required
@require_POST
def start_oven_bake(request, loaf_id):
    loaf = get_object_or_404(Loaf, pk=loaf_id)
    loaf.status = 'baking_in_oven'
    loaf.started_oven_bake_at = timezone.now()
    loaf.save()
    return redirect('dashboard')

@login_required
@require_POST
def finish_loaf(request, loaf_id):
    loaf = get_object_or_404(Loaf, pk=loaf_id)
    loaf.status = 'finished'
    loaf.finished_at = timezone.now()  # <-- ADD THIS LINE

    loaf.save()
    return redirect('dashboard')

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
            loaf = form.save(commit=False)
            loaf.created_by = request.user
            loaf.save()
            
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

@login_required
@permission_required('tracker.change_loaf', raise_exception=True)
def edit_loaf(request, loaf_id):
    loaf = get_object_or_404(Loaf, id=loaf_id)

    # Trigger a warning message if someone else created this loaf
    if loaf.created_by and loaf.created_by != request.user:
        messages.warning(
            request, 
            f"⚠️ Ownership Warning: This loaf was originally logged by {loaf.created_by.username}. Don't edit it unless you are sure you should."
        )

    if request.method == 'POST':
        form = LoafEditForm(request.POST, instance=loaf)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = LoafEditForm(instance=loaf)       

    return render(request, 'loaf_form.html', {
        'form': form, 
        'loaf': loaf, 
        'action': 'Edit Loaf'
    })

@login_required
@permission_required('tracker.delete_loaf', raise_exception=True)
def delete_loaf(request, loaf_id):
    loaf = get_object_or_404(Loaf, id=loaf_id)
    if request.method == 'POST':
        loaf.delete()
        return redirect('dashboard')
    return render(request, 'loaf_confirm_delete.html', {'loaf': loaf})

@login_required
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
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Restrict access to original author or superuser
    if request.user != comment.author and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this comment.")
        return redirect('loaf_detail', loaf_id=comment.loaf.id)

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, "Comment updated successfully.")
            return redirect('loaf_detail', loaf_id=comment.loaf.id)
    else:
        form = CommentForm(instance=comment)

    return render(request, 'comment_form.html', {'form': form, 'comment': comment})

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Restrict access to original author or superuser
    if request.user != comment.author and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this comment.")
        return redirect('loaf_detail', loaf_id=comment.loaf.id)

    if request.method == 'POST':
        loaf_id = comment.loaf.id
        comment.delete()
        messages.success(request, "Comment deleted.")
        return redirect('loaf_detail', loaf_id=loaf_id)

    return render(request, 'comment_confirm_delete.html', {'comment': comment})

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
    all_machines = BreadMachine.objects.all()
    
    # Active loaves are any loaves not yet marked as removed
    active_loaves = Loaf.objects.exclude(status='finished')

    # ONLY occupy the machine if it's still inside the bread machine
    active_machine_ids = Loaf.objects.filter(
        status='baking_in_machine'
    ).values_list('machine_id', flat=True)
    
    # History shows loaves after they're finished
    history_loaves = Loaf.objects.filter(status='finished').order_by('-ready_at')

    context = {
        'all_machines': all_machines,
        'active_loaves': active_loaves,
        'active_machine_ids': active_machine_ids,
        'history_loaves': history_loaves,
    }
    return render(request, 'dashboard.html', context)
