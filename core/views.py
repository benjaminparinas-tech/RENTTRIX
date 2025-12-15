from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse, Http404
from django.template.loader import render_to_string
from weasyprint import HTML
from decimal import Decimal
from .models import Room, RoomTenant, Payment, Receipt, LandlordProfile, AddOn
from .models import TenantSecurityProfile
from .forms import (
    RoomForm,
    RoomTenantForm,
    PaymentForm,
    AddOnForm,
    TenantCreationForm,
    TenantFirstLoginForm,
)
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from datetime import datetime
import calendar
from django.db.models import Q
from urllib.parse import quote

def is_landlord(user):
    return user.is_staff

@login_required
def home(request):
    if request.user.is_staff:
        return redirect('landlord_dashboard')
    return redirect('tenant_dashboard')

@login_required
@user_passes_test(is_landlord)
def landlord_dashboard(request):
    total_rooms = Room.objects.count()
    total_tenants = RoomTenant.objects.filter(status='active').count()
    total_payments = Payment.objects.filter(status='paid').count()
    recent_payments = Payment.objects.filter(status='paid').order_by('-payment_date')[:5]
    
    context = {
        'total_rooms': total_rooms,
        'total_tenants': total_tenants,
        'total_payments': total_payments,
        'recent_payments': recent_payments,
    }
    return render(request, 'core/landlord_dashboard.html', context)

@login_required
def tenant_dashboard(request):
    try:
        room_assignment = RoomTenant.objects.get(tenant=request.user, status='active')
        payments = Payment.objects.filter(tenant=request.user).order_by('-payment_date')
    except RoomTenant.DoesNotExist:
        room_assignment = None
        payments = None
    
    context = {
        'room_assignment': room_assignment,
        'payments': payments,
        'tenant_name': request.user.get_full_name(),
    }
    return render(request, 'core/tenant_dashboard.html', context)

@login_required
@user_passes_test(is_landlord)
def room_list(request):
    rooms = Room.objects.all().order_by('room_number')
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    if q:
        rooms = rooms.filter(Q(room_number__icontains=q))
    if status in ['vacant', 'full']:
        rooms = rooms.filter(status=status)

    context = {
        'rooms': rooms,
        'q': q,
        'status': status,
    }
    return render(request, 'core/room_list.html', context)

@login_required
@user_passes_test(is_landlord)
def room_add(request):
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            # ensure defaults
            if room.current_occupants is None:
                room.current_occupants = 0
            room.status = 'vacant'
            room.save()
            messages.success(request, 'Room created successfully!')
            return redirect('room_detail', room_id=room.id)
    else:
        form = RoomForm()
    return render(request, 'core/room_form.html', {'form': form, 'room': None})

@login_required
@user_passes_test(is_landlord)
def room_detail(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    tenants = RoomTenant.objects.filter(room=room, status='active')
    return render(request, 'core/room_detail.html', {'room': room, 'tenants': tenants})

@login_required
@user_passes_test(is_landlord)
def room_edit(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            updated_room = form.save()
            # sync status with occupants/capacity
            updated_room.update_status()
            messages.success(request, 'Room updated successfully!')
            return redirect('room_detail', room_id=room.id)
    else:
        form = RoomForm(instance=room)
    return render(request, 'core/room_form.html', {'form': form, 'room': room})

@login_required
@user_passes_test(is_landlord)
def room_delete(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if request.method == 'POST':
        room_number = room.room_number
        room.delete()
        messages.success(request, f'Room {room_number} deleted successfully!')
        return redirect('room_list')
    messages.error(request, 'Invalid request method for deleting a room.')
    return redirect('room_detail', room_id=room.id)

@login_required
@user_passes_test(is_landlord)
def roomtenant_add(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if request.method == 'POST':
        form = RoomTenantForm(request.POST)
        if form.is_valid():
            assignment = form.save()
            # update room occupancy
            assignment.room.current_occupants = RoomTenant.objects.filter(room=assignment.room, status='active').count()
            assignment.room.update_status()
            messages.success(request, f'Tenant added to Room {assignment.room.room_number}!')
            return redirect('room_detail', room_id=assignment.room.id)
    else:
        form = RoomTenantForm(initial={'room': room})
    return render(request, 'core/roomtenant_form_fixed.html', {'form': form, 'room': room})

@login_required
@user_passes_test(is_landlord)
def roomtenant_edit(request, room_id, assignment_id):
    room = get_object_or_404(Room, id=room_id)
    try:
        assignment = get_object_or_404(RoomTenant, id=assignment_id, room=room, status='active')
    except Http404:
        messages.error(request, 'Cannot edit an archived tenant.')
        return redirect('tenant_list')
    old_room = assignment.room  # Store the old room before potential change
    
    # Get add-ons for this assignment
    addons = AddOn.objects.filter(room_tenant=assignment).order_by('-created_at')
    
    # Initialize forms
    form = RoomTenantForm(instance=assignment)
    addon_form = AddOnForm()
    
    # Handle POST requests
    if request.method == 'POST':
        # Handle add-on creation
        if 'add_addon' in request.POST:
            addon_form = AddOnForm(request.POST)
            if addon_form.is_valid():
                addon = addon_form.save(commit=False)
                addon.room_tenant = assignment
                addon.save()
                messages.success(request, 'Add-on added successfully!')
                return redirect('roomtenant_edit', room_id=room.id, assignment_id=assignment.id)
        
        # Handle assignment update
        elif 'save_assignment' in request.POST:
            form = RoomTenantForm(request.POST, instance=assignment)
            if form.is_valid():
                updated_assignment = form.save()
                new_room = updated_assignment.room
                
                # Update occupancy for both old and new rooms if room changed
                if old_room.id != new_room.id:
                    # Update old room
                    old_room.current_occupants = RoomTenant.objects.filter(room=old_room, status='active').count()
                    old_room.update_status()
                    # Update new room
                    new_room.current_occupants = RoomTenant.objects.filter(room=new_room, status='active').count()
                    new_room.update_status()
                    messages.success(request, f'Tenant moved to Room {new_room.room_number}!')
                    return redirect('room_detail', room_id=new_room.id)
                else:
                    # Room didn't change, just update the current room
                    room.current_occupants = RoomTenant.objects.filter(room=room, status='active').count()
                    room.update_status()
                    messages.success(request, 'Room tenant updated!')
                    return redirect('room_detail', room_id=room.id)
    
    return render(request, 'core/roomtenant_form_fixed.html', {
        'form': form, 
        'room': room, 
        'assignment': assignment,
        'addon_form': addon_form,
        'addons': addons
    })

@login_required
@user_passes_test(is_landlord)
def roomtenant_archive(request, room_id, assignment_id):
    room = get_object_or_404(Room, id=room_id)
    try:
        assignment = get_object_or_404(RoomTenant, id=assignment_id, room=room, status='active')
    except Http404:
        messages.error(request, 'Tenant is already archived.')
        return redirect('tenant_list')
    if request.method == 'POST':
        assignment.status = 'inactive'
        assignment.save()
        room.current_occupants = RoomTenant.objects.filter(room=room, status='active').count()
        room.update_status()
        messages.success(request, 'Tenant moved to archive.')
        return redirect('room_detail', room_id=room.id)
    return render(request, 'core/confirm_archive.html', {'room': room, 'assignment': assignment})

@login_required
@user_passes_test(is_landlord)
def tenant_list(request):
    assignments = RoomTenant.objects.select_related('tenant', 'room').order_by('room__room_number', 'tenant__first_name')
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    if q:
        assignments = assignments.filter(
            Q(tenant__first_name__icontains=q) |
            Q(tenant__last_name__icontains=q) |
            Q(tenant__username__icontains=q) |
            Q(tenant__email__icontains=q) |
            Q(room__room_number__icontains=q)
        )
    if status in ['active', 'inactive']:
        assignments = assignments.filter(status=status)

    context = {
        'tenants': assignments,
        'q': q,
        'status': status,
    }
    return render(request, 'core/tenant_list.html', context)

@login_required
@user_passes_test(is_landlord)
def archived_tenants(request):
    assignments = RoomTenant.objects.select_related('tenant', 'room').filter(status='inactive').order_by('tenant__first_name')
    return render(request, 'core/archived_tenants.html', {'tenants': assignments})

@login_required
@user_passes_test(is_landlord)
def roomtenant_restore(request, assignment_id):
    assignment = get_object_or_404(RoomTenant, id=assignment_id, status='inactive')
    rooms = Room.objects.all().order_by('room_number')
    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        target_room = get_object_or_404(Room, id=room_id)
        # Move assignment to new room and activate
        assignment.room = target_room
        assignment.status = 'active'
        assignment.save()
        # Recompute occupancy for both rooms
        try:
            previous_room = Room.objects.get(id=request.POST.get('previous_room_id'))
            previous_room.current_occupants = RoomTenant.objects.filter(room=previous_room, status='active').count()
            previous_room.update_status()
        except Exception:
            pass
        target_room.current_occupants = RoomTenant.objects.filter(room=target_room, status='active').count()
        target_room.update_status()
        messages.success(request, 'Tenant restored and moved to the selected room.')
        return redirect('room_detail', room_id=target_room.id)
    return render(request, 'core/restore_tenant.html', {'assignment': assignment, 'rooms': rooms})

@login_required
@user_passes_test(is_landlord)
def payment_list(request):
    payments = Payment.objects.all().select_related('tenant', 'room').order_by('-payment_date')
    return render(request, 'core/payment_list.html', {'payments': payments})

@login_required
@user_passes_test(is_landlord)
def payment_edit(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Payment updated successfully!')
            return redirect('payment_list')
    else:
        form = PaymentForm(instance=payment)
    return render(request, 'core/payment_form.html', {'form': form, 'payment': payment})

@login_required
@user_passes_test(is_landlord)
def add_payment(request, tenant_id):
    tenant = get_object_or_404(User, id=tenant_id)
    room_assignment = get_object_or_404(RoomTenant, tenant=tenant, status='active')
    
    # Calculate base amount (1350) + add-ons
    base_amount = Decimal('1350.00')
    addons = AddOn.objects.filter(room_tenant=room_assignment)
    addon_total = sum(addon.amount for addon in addons) if addons else Decimal('0.00')
    total_amount = base_amount + addon_total
    
    if request.method == 'POST':
        payment_month = request.POST.get('payment_month')
        
        # Convert YYYY-MM to datetime object
        payment_month = datetime.strptime(f"{payment_month}-01", "%Y-%m-%d")
        
        try:
            # Create payment with calculated total
            payment = Payment.objects.create(
                tenant=tenant,
                room=room_assignment.room,
                amount=total_amount,
                payment_month=payment_month,
                payment_date=timezone.now(),
                status='paid'
            )
            
            # Then create receipt
            receipt = Receipt.objects.create(
                payment=payment,
                receipt_number=payment.receipt_number,
                tenant_name=tenant.get_full_name(),
                room_number=room_assignment.room.room_number,
                amount=total_amount,
                payment_month=payment_month,
                payment_date=payment.payment_date,
                landlord_signature='signatures/signature.png'
            )
            
            messages.success(request, f'Payment of ₱{total_amount:,.2f} recorded successfully!')
            return redirect('payment_tracking')
            
        except Exception as e:
            messages.error(request, f'Error recording payment: {str(e)}')
            return render(request, 'core/add_payment.html', {
                'tenant': tenant, 
                'room': room_assignment.room,
                'base_amount': base_amount,
                'addons': addons,
                'addon_total': addon_total,
                'total_amount': total_amount
            })
    
    return render(request, 'core/add_payment.html', {
        'tenant': tenant, 
        'room': room_assignment.room,
        'base_amount': base_amount,
        'addons': addons,
        'addon_total': addon_total,
        'total_amount': total_amount
    })

@login_required
def payment_history(request):
    payments = Payment.objects.filter(tenant=request.user).order_by('-payment_date')
    return render(request, 'core/payment_history.html', {'payments': payments})

@login_required
@user_passes_test(is_landlord)
def manage_signature(request):
    profile, created = LandlordProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        if 'signature' in request.FILES:
            profile.signature = request.FILES['signature']
            profile.save()
            messages.success(request, 'Signature updated successfully!')
            return redirect('manage_signature')
    
    return render(request, 'core/manage_signature.html', {'profile': profile})

@login_required
def download_receipt(request, receipt_id):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    
    # Check if user is authorized to view this receipt
    if not request.user.is_staff and receipt.payment.tenant != request.user:
        messages.error(request, 'You are not authorized to view this receipt.')
        return redirect('home')
    
    # Get landlord profile for signature
    try:
        landlord_profile = LandlordProfile.objects.get(user__is_staff=True)
        receipt.landlord_signature = landlord_profile.signature
    except LandlordProfile.DoesNotExist:
        receipt.landlord_signature = None
    
    # Generate PDF
    html_string = render_to_string('core/receipt_template.html', {'receipt': receipt})
    pdf = HTML(string=html_string).write_pdf()
    
    # Create response
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{receipt.receipt_number}.pdf"'
    
    return response

@login_required
def dashboard_redirect(request):
    if request.user.is_staff:
        return redirect('landlord_dashboard')
    return redirect('tenant_dashboard')

@login_required
@user_passes_test(is_landlord)
def tenant_payment_history(request, tenant_id):
    tenant = get_object_or_404(User, id=tenant_id)
    payments = Payment.objects.filter(tenant=tenant).order_by('-payment_date')
    return render(request, 'core/tenant_payment_history.html', {'tenant': tenant, 'payments': payments})

@login_required
@user_passes_test(is_landlord)
def payment_tracking(request):
    # Get the selected year from query parameters, default to 2025
    selected_year = int(request.GET.get('year', 2025))
    
    # Get all active tenants with their room assignments and add-ons
    active_tenants = RoomTenant.objects.filter(status='active').select_related('tenant', 'room').prefetch_related('addons').order_by('room__room_number')
    
    # Get all months in the selected year
    months = list(calendar.month_name)[1:]  # Get list of month names
    
    # Get all payments for the selected year
    payments = Payment.objects.filter(
        payment_month__year=selected_year,
        tenant__in=[tenant.tenant for tenant in active_tenants]
    ).select_related('tenant', 'room')
    
    # Create a dictionary to store payment status for each tenant and month
    payment_status = {}
    for tenant in active_tenants:
        payment_status[tenant.tenant.id] = {}
        for month in range(1, 13):
            payment_status[tenant.tenant.id][month] = None
    
    # Ensure current_year and available_years are defined
    current_year = timezone.now().year
    available_years = request.session.get('persisted_years', list(range(2025, current_year + 1)))

    # Ensure payments for the selected year and month are displayed
    for payment in payments:
        month = payment.payment_month.month
        payment_status[payment.tenant.id][month] = 'paid'

    # Include future years in available years
    if selected_year > current_year:
        if selected_year not in available_years:
            available_years.append(selected_year)
            available_years.sort()
            request.session['persisted_years'] = available_years

    # Validate payment input for specific months in the selected year
    for tenant in active_tenants:
        for month in range(1, 13):
            if tenant.move_in_date.year > selected_year or (
                tenant.move_in_date.year == selected_year and tenant.move_in_date.month > month
            ):
                payment_status[tenant.tenant.id][month] = 'invalid'
    
    context = {
        'active_tenants': active_tenants,
        'months': months,
        'payment_status': payment_status,
        'selected_year': selected_year,
        'available_years': available_years,
    }
    
    return render(request, 'core/payment_tracking.html', context)


@login_required
@user_passes_test(is_landlord)
def addon_add(request, room_id, assignment_id):
    room = get_object_or_404(Room, id=room_id)
    try:
        assignment = get_object_or_404(RoomTenant, id=assignment_id, room=room, status='active')
    except Http404:
        messages.error(request, 'Cannot add add-ons to an archived tenant.')
        return redirect('tenant_list')
    
    if request.method == 'POST':
        form = AddOnForm(request.POST)
        if form.is_valid():
            addon = form.save(commit=False)
            addon.room_tenant = assignment
            addon.save()
            messages.success(request, 'Add-on added successfully!')
            return redirect('room_detail', room_id=room.id)
    else:
        form = AddOnForm()
    
    addons = AddOn.objects.filter(room_tenant=assignment).order_by('-created_at')
    return render(request, 'core/addon_form.html', {
        'form': form, 
        'room': room, 
        'assignment': assignment,
        'addons': addons
    })

@login_required
@user_passes_test(is_landlord)
def addon_delete(request, room_id, assignment_id, addon_id):
    room = get_object_or_404(Room, id=room_id)
    try:
        assignment = get_object_or_404(RoomTenant, id=assignment_id, room=room, status='active')
    except Http404:
        messages.error(request, 'Cannot remove add-ons from an archived tenant.')
        return redirect('tenant_list')
    addon = get_object_or_404(AddOn, id=addon_id, room_tenant=assignment)
    
    if request.method == 'POST':
        addon.delete()
        messages.success(request, 'Add-on deleted successfully!')
        return redirect('room_detail', room_id=room.id)
    
    return render(request, 'core/addon_confirm_delete.html', {
        'room': room,
        'assignment': assignment,
        'addon': addon
    })


@login_required
@user_passes_test(is_landlord)
def tenant_create(request):
    """
    Landlord creates a tenant account and shares initial credentials.
    """
    created_user = None
    initial_password = None

    if request.method == 'POST':
        form = TenantCreationForm(request.POST)
        if form.is_valid():
            created_user = form.save()
            # Ensure a security profile exists and is set to force password change
            profile, _ = TenantSecurityProfile.objects.get_or_create(user=created_user)
            profile.force_password_change = True
            profile.save()
            initial_password = form.cleaned_data['password']
            messages.success(request, 'Tenant account created. Share the credentials below.')
            form = TenantCreationForm()  # reset form
    else:
        form = TenantCreationForm()

    return render(request, 'core/tenant_create.html', {
        'form': form,
        'created_user': created_user,
        'initial_password': initial_password,
    })


@login_required
def force_password_change(request):
    """
    Prompt tenants to change their password on first login.
    """
    user = request.user
    # Landlords do not need to pass through this flow
    if user.is_staff:
        return redirect('dashboard')

    profile, _ = TenantSecurityProfile.objects.get_or_create(user=user)
    initial = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
    }
    form = TenantFirstLoginForm(user=user, data=request.POST or None, initial=initial)

    if request.method == 'POST' and form.is_valid():
        form.save()
        profile.force_password_change = False
        profile.save()
        messages.success(request, 'Password updated. Welcome!')
        return redirect('dashboard')

    return render(request, 'account/force_password_change.html', {'form': form})

@login_required
def search_api(request):
    query = request.GET.get('q', '').strip()
    results = []
    if len(query) >= 2:
        matched_rooms = Room.objects.filter(Q(room_number__icontains=query))[:5]
        for room in matched_rooms:
            results.append({
                'type': 'Room',
                'title': f"Room {room.room_number}",
                'icon': 'fa-door-open',
                'url': f"/rooms/{room.id}/",
            })

        matched_assignments = RoomTenant.objects.select_related('tenant', 'room').filter(
            Q(tenant__first_name__icontains=query) |
            Q(tenant__last_name__icontains=query) |
            Q(tenant__username__icontains=query) |
            Q(tenant__email__icontains=query)
        )[:5]
        for a in matched_assignments:
            results.append({
                'type': 'Tenant',
                'title': a.tenant.get_full_name() or a.tenant.username,
                'icon': 'fa-user',
                'url': f"/tenants/?q={quote(query)}",
            })

    return JsonResponse(results, safe=False)


@login_required
def tenant_room_list(request):
    """
    Tenant-facing read-only list of rooms matching landlord design.
    """
    rooms = Room.objects.all().order_by('room_number')
    return render(request, 'core/tenant_room_list.html', {
        'rooms': rooms,
    })


@login_required
def tenant_room_detail(request, room_id):
    """
    Tenant-facing read-only room detail matching landlord view.
    """
    room = get_object_or_404(Room, id=room_id)
    tenants = RoomTenant.objects.filter(room=room, status='active').select_related('tenant', 'room').order_by('tenant__first_name')
    return render(request, 'core/tenant_room_detail.html', {
        'room': room,
        'tenants': tenants,
    })


@login_required
def tenant_payment_tracker(request):
    """
    Tenant-facing payment tracker with receipt downloads for paid months.
    """
    payments = (
        Payment.objects.filter(tenant=request.user)
        .select_related('receipt')
        .order_by('-payment_month')
    )
    return render(request, 'core/payment_tracker.html', {'payments': payments})
