import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.hashers import check_password 
from django.middleware.csrf import get_token
from home.models import UserProfile,Subscription,Event,EventTicket
from django.db.models import Sum, Count
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta


def admin_login_view(request):
    if request.method == "POST":
        try:
          
            data = json.loads(request.body)
            username = data.get("username")
            password = data.get("password")

         
            try:
                user = UserProfile.objects.get(username=username)
            except UserProfile.DoesNotExist:
                return JsonResponse({"success": False, "error": "User not found."}, status=400)

           
            if not user.is_admin:
                return JsonResponse({"success": False, "error": "Access denied. Admins only."}, status=403)

           
            if not check_password(password, user.password):
                return JsonResponse({"success": False, "error": "Invalid credentials."}, status=401)

           
            request.session["admin_id"] = user.id
            request.session["admin_username"] = user.username
            request.session["is_admin"] = True
            request.session.set_expiry(86400)  

           
            return JsonResponse({"success": True, "redirect_url": "/site_admin/dashboard/"})

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON data."}, status=400)

  
    return render(request, "admin/login.html", {"csrf_token": get_token(request)})

def admin_dashboard(request):
    if not request.session.get('is_admin', False):
       return redirect('home')
    total_events = Event.objects.count()
    total_subscriptions = Subscription.objects.count()
    total_event_revenue = EventTicket.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    total_subscription_revenue = total_subscriptions * 100  # Assuming premium is $100 per user

   
    monthly_revenue = EventTicket.objects.extra(select={'month': "DATE_TRUNC('month', booking_date)"}).values('month').annotate(total=Sum('amount')).order_by('month')
    month_labels = [entry['month'].strftime("%b") for entry in monthly_revenue]
    revenue_data = [entry['total'] for entry in monthly_revenue]

    
    subscription_types = ['Premium']
    subscription_data = [total_subscriptions]

    
    event_categories = Event.objects.values('category').annotate(event_count=Count('id'))
    event_category_labels = [category['category'] for category in event_categories]
    event_category_data = [category['event_count'] for category in event_categories]

   
    recent_tickets = EventTicket.objects.select_related('user_profile', 'event').order_by('-booking_date')[:5]

    context = {
        'total_events': total_events,
        'total_subscriptions': total_subscriptions,
        'total_event_revenue': total_event_revenue,
        'total_subscription_revenue': total_subscription_revenue,
        'month_labels': month_labels,
        'revenue_data': revenue_data,
        'subscription_types': subscription_types,
        'subscription_data': subscription_data,
        'event_category_labels': event_category_labels,
        'event_category_data': event_category_data,
        'recent_tickets': recent_tickets,
    }

    return render(request, 'admin/dashboard.html', context)


def user_management(request):
    if not request.session.get('is_admin', False):
         return redirect('home')
    users = UserProfile.objects.all()
    return render(request, 'admin/user.html', {'users': users})


def toggle_block_user(request, user_id):
    if not request.session.get('is_admin', False):
       return redirect('home')
    try:
        user = UserProfile.objects.get(id=user_id)
        user.is_active = not user.is_active  
        user.save()
        
       
        if user.is_active:
            messages.success(request, f'User {user.full_name} has been unblocked.')
        else:
            messages.success(request, f'User {user.full_name} has been blocked.')
    except UserProfile.DoesNotExist:
        messages.error(request, 'User not found.')

    return redirect('user_management')

def event_list(request):
    if not request.session.get('is_admin', False):
      
        return redirect('home')
    events = Event.objects.all() 
    return render(request, 'admin/event.html', {'events': events})
def subscription_list(request):
    if not request.session.get('is_admin', False):
       
        return redirect('home')
    now = timezone.now()
    subscriptions = Subscription.objects.select_related('user_profile').all()
    print(subscriptions)
   
    for subscription in subscriptions:
        subscription.end_date = subscription.date + timedelta(days=30)

    return render(request, 'admin/Subscription.html', {
        'subscriptions': subscriptions,
        'now': now
    })

def ticket_list(request):
    if not request.session.get('is_admin', False):
       
        return redirect('home')
    tickets = EventTicket.objects.select_related('user_profile', 'event').all()
    return render(request, 'admin/event_ticket.html', {'event_tickets': tickets})


def admin_logout_view(request):
  
    request.session.flush()
    return redirect("/site_admin/login/")