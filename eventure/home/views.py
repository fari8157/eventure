from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import UserProfile,Subscription
from .models import Event,EventTicket
from django.contrib.auth.hashers import check_password, make_password
from django.conf import settings
from django.utils.timezone import localtime
from datetime import datetime,timedelta
from django.core.mail import send_mail
import json
from django.http import JsonResponse
import random
from django.contrib.auth import authenticate, login
from django.views.decorators.cache import cache_control
from django.utils import timezone
import razorpay
from django.http import HttpResponseBadRequest
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import razorpay
from django.conf import settings
from .models import Event, EventTicket, UserProfile
from django.db.models import Sum
from django.db.models import Sum, F, Value
from django.utils.timezone import now


@cache_control(no_cache=True,must_revalidate=True,no_store=True)
def home(request):
    return render(request, 'user/home.html')

# auth views
@cache_control(no_cache=True,must_revalidate=True,no_store=True)
def user_login(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')

            try:
                user = UserProfile.objects.get(username=username)
            except UserProfile.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Invalid username or password.'})

           
            if check_password(password, user.password):  
                
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                request.session['email'] = user.email
                request.session['is_logged_in'] = True
                request.session['is_subscribed'] = user.is_subscribed

                return JsonResponse({'success': True, 'redirect_url': '/'})
            else:
                return JsonResponse({'success': False, 'error': 'Invalid username or password.'})
        except Exception as e:
            print("Error:", e)  
            return JsonResponse({'success': False, 'error': 'Something went wrong. Please try again.'})

    return render(request, 'user/login.html')

# registration views
def generate_otp():
    return random.randint(100000, 999999)
@cache_control(no_cache=True,must_revalidate=True,no_store=True)
def register(request):
    if request.method == "POST":
        data = json.loads(request.body)
        full_name = data.get('full_name')
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')

       
        if password != confirm_password:
            return JsonResponse({'success': False, 'error': 'Passwords do not match!'})

       
        if UserProfile.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'error': 'Username already exists.'})
        if UserProfile.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'Email already exists.'})

       
        hashed_password = make_password(password)

       
        otp = generate_otp()
        otp_expiry = datetime.now() + timedelta(minutes=1)  # OTP expires in 1 minute

       
        request.session['otp'] = otp
        request.session['otp_expiry'] = otp_expiry.isoformat()

        # Send OTP via email
        send_mail(
            'Your OTP for registration',
            f'Your OTP is: {otp}',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )

        # Store user data temporarily
        request.session['registration_data'] = {
            'full_name': full_name,
            'username': username,
            'email': email,
            'password': hashed_password
        }

      
        return JsonResponse({'success': True, 'redirect_url': '/verify-otp/'})

    return render(request, 'user/register.html')
@cache_control(no_cache=True,must_revalidate=True,no_store=True)
def verify_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get('otp')
        stored_otp = request.session.get('otp')
        otp_expiry = request.session.get('otp_expiry')

       
        if not stored_otp or not otp_expiry:
            messages.error(request, "OTP expired or not found!")
            return redirect('register')  

      
        otp_expiry = datetime.fromisoformat(otp_expiry)
        if datetime.now() > otp_expiry:
            messages.error(request, "OTP has expired! Please request a new one.")
            return redirect('verify_otp')

        
        if entered_otp == str(stored_otp):
            
            user_data = request.session.get('registration_data')
            if user_data:
                UserProfile.objects.create(
                    full_name=user_data['full_name'],
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password']
                )
                messages.success(request, "Registration successful!")
               
                request.session.pop('registration_data', None)
                request.session.pop('otp', None)
                request.session.pop('otp_expiry', None)
                return redirect('login')
            else:
                messages.error(request, "Error saving user data. Please try again.")
                return redirect('register')
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, 'user/otp.html')
@cache_control(no_cache=True,must_revalidate=True,no_store=True)
def resend_otp(request):
   
    user_data = request.session.get('registration_data')
    if not user_data:
        messages.error(request, "No active registration session found.")
        return redirect('register')

    
    otp = generate_otp()
    otp_expiry = datetime.now() + timedelta(minutes=1)  
    request.session['otp'] = otp
    request.session['otp_expiry'] = otp_expiry.isoformat()

    
    send_mail(
        'Your OTP for registration',
        f'Your OTP is: {otp}',
        settings.DEFAULT_FROM_EMAIL,
        [user_data['email']],
        fail_silently=False,
    )

    messages.success(request, "New OTP has been sent to your email.")
    return redirect('verify_otp')


# event views

def create_event(request):
     if not request.session.get('username'):
        return redirect('login') 

    
     if not request.session.get('is_subscribed'):
       return redirect('login')
     
     if request.method == 'POST':
       
        title = request.POST.get('title')
        description = request.POST.get('description')
        date = request.POST.get('date')
        price = request.POST.get('price')
        location = request.POST.get('location')
        category = request.POST.get('category')
        image = request.FILES.get('image')
        ticket_count = request.POST.get('ticket_count')

       
        if date:
           
            naive_datetime = timezone.datetime.fromisoformat(date)
          
            aware_datetime = timezone.make_aware(naive_datetime)
            if aware_datetime < timezone.now():
                return render(request, 'user/create_event.html', {
                    'error': 'The event date cannot be in the past.'
                })
        try:
            user_profile = UserProfile.objects.get(username=request.session['username'])
        except UserProfile.DoesNotExist:
            return render(request, 'user/create_event.html', {
                'error': 'User profile not found.'
            })   

       
        event = Event(
            title=title,
            description=description,
            date=date,
            price=price,
            location=location,
            category=category,
            image=image,
            organizer=user_profile , 
            ticket_count=ticket_count
        )
        event.save()

        return redirect('/') 
     return render(request, 'user/create_event.html')

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, 'user/event_detail.html', {'event': event})
def event_list(request):
    events = Event.objects.filter(date__gte=timezone.now()).order_by('-date')
    return render(request, 'user/events.html', {'events': events})
# forgot_password
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get('email')

       
        try:
            user = UserProfile.objects.get(email=email)
        except UserProfile.DoesNotExist:
            return render(request, 'user/forgot_password.html', {'error': 'Email not found'})

       
        otp = generate_otp()
        otp_expiry = datetime.now() + timedelta(minutes=1)  
        
        request.session['otp'] = otp
        request.session['otp_expiry'] = otp_expiry.isoformat()
        request.session['email'] = email  

       
        send_mail(
            'Your OTP for Password Reset',
            f'Your OTP is: {otp}',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )

       
        return redirect('forgot_otp')

    return render(request, 'user/forgot_password.html')


def forgot_otp(request):
    if request.method == "POST":
        user_otp = request.POST.get('otp')
        stored_otp = request.session.get('otp')
        otp_expiry = datetime.fromisoformat(request.session.get('otp_expiry'))
        print(stored_otp,user_otp)
       
        if datetime.now() > otp_expiry:
            return render(request, 'user/forgot_otp.html', {'error': 'OTP has expired. Please try again.'})

      
        if user_otp == str(stored_otp):
          
            return redirect('reset-password')
        else:
            return render(request, 'user/forgot_otp.html', {'error': 'Invalid OTP. Please try again.'})

    return render(request, 'user/forgot_otp.html')

def forgot_resend_otp(request):
    
    email = request.session.get('email')
    if not email:
        return redirect('forgot-password')  

    
    otp = generate_otp()
    otp_expiry = datetime.now() + timedelta(minutes=1)  

    
    request.session['otp'] = otp
    request.session['otp_expiry'] = otp_expiry.isoformat()

   
    send_mail(
        'Your New OTP for Password Reset',
        f'Your new OTP is: {otp}',
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

   
    return redirect('forgot_otp')

def reset_password(request):
    if request.method == "POST":
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

       
        if new_password != confirm_password:
            return render(request, 'user/reset_password.html', {'error': 'Passwords do not match!'})

       
        email = request.session.get('email')
        if not email:
            return render(request, 'user/reset_password.html', {'error': 'Session expired. Please try again.'})

      
        try:
            user = UserProfile.objects.get(email=email)
            user.password = make_password(new_password)
            user.save()

           
            request.session.pop('otp')
            request.session.pop('otp_expiry')
            request.session.pop('email')

            
            return redirect('login')
        except UserProfile.DoesNotExist:
            return render(request, 'user/reset_password.html', {'error': 'User not found. Please try again.'})

    return render(request, 'user/reset_password.html')

# subsctipon views
def send_subscription_confirmation_email(user, subscription_plan, subscription_amount, subscription_date, expiry_date, login_url):
    subject = "Your Haven Subscription Confirmation"
    html_message = render_to_string('emails/subscription_confirmation.html', {
        'user': user,
        'subscription_plan': subscription_plan,
        'subscription_amount': subscription_amount,
        'subscription_date': subscription_date,
        'expiry_date': expiry_date,
        'login_url': login_url,
    })
    plain_message = strip_tags(html_message)  
    from_email = 'support@haven.com'
    to_email = user.email

    email = EmailMessage(subject, html_message, from_email, [to_email])
    email.content_subtype = "html"  
    email.send()

def subscription(request):
    if not request.session.get('is_logged_in'):
        return redirect('login')
    return render(request, 'user/subscription.html')

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
def create_razorpay_order(request):
    if not request.session.get('is_logged_in'):
        return JsonResponse({'error': 'User not logged in'}, status=403)

   
    amount = 10000  # ₹100
    currency = 'INR'

   
    razorpay_order = razorpay_client.order.create({
        'amount': amount,
        'currency': currency,
        'payment_capture': '1'  
    })

   
    return JsonResponse({
        'id': razorpay_order['id'],
        'amount': razorpay_order['amount'],
        'currency': razorpay_order['currency']
    })
def payment_success(request):
    if not request.session.get('is_logged_in'):
        return JsonResponse({'error': 'User not logged in'}, status=403)
    if request.method == 'POST':
        data = json.loads(request.body)
        # Get payment details from Razorpay
        razorpay_payment_id =data['razorpay_payment_id']
        razorpay_order_id =data['razorpay_order_id']
        razorpay_signature =data['razorpay_signature']
       
        # Verify the payment signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        try:
            razorpay_client.utility.verify_payment_signature(params_dict)
            print("Signature verification successful!")
        except razorpay.errors.SignatureVerificationError:
            print("Signature verification failed:")
            return HttpResponseBadRequest('Invalid payment signature')
        print("hiiii2222")
       
      
        user_profile = UserProfile.objects.get(username=request.session['username'])

       
        user_profile.is_subscribed = True
        user_profile.subscribed_date = timezone.now()
        user_profile.save()
        request.session['is_subscribed'] = user_profile.is_subscribed

        subscription_plan = "Basic Plan"
        subscription_amount = "₹100"  # Replace with the actual amount
        subscription_date = user_profile.subscribed_date.strftime('%d %b %Y')
        expiry_date = (user_profile.subscribed_date + timezone.timedelta(days=30)).strftime('%d %b %Y')
        login_url = "https://yourdomain.com/login/"  # Replace with your login URL

        send_subscription_confirmation_email(
                user_profile, subscription_plan, subscription_amount, subscription_date, expiry_date, login_url
            )

        # Save subscription details
        Subscription.objects.create(
            user_profile=user_profile,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_order_id=razorpay_order_id,
            razorpay_signature=razorpay_signature
        )

        # Return success response
        return JsonResponse({'status': 'success'})
    return HttpResponseBadRequest('Invalid request')


def ticket_create_razorpay_order(request):
    if not request.session.get('is_logged_in'):
        return JsonResponse({'error': 'User not logged in'}, status=403)
    if request.method == 'POST':
        try:
           
            data = json.loads(request.body)
            event_id = data.get('event_id')
            ticket_count = int(data.get('ticket_count', 0))  

            
            if not event_id or ticket_count <= 0:
                return JsonResponse({'error': 'Invalid data provided'}, status=400)

           
            try:
                event = Event.objects.get(id=event_id)
                if event.date < timezone.now():
                   return JsonResponse({'error': 'This event has already passed.'}, status=400)
                if event.ticket_count == 0:
                   return JsonResponse({'error': 'Tickets are sold out.'}, status=400)
            except Event.DoesNotExist:
                return JsonResponse({'error': 'Event not found'}, status=404)

          
            amount = event.price * ticket_count  

            # Create Razorpay Order
            order = razorpay_client.order.create({
                'amount': int(amount * 100), 
                'currency': 'INR',
                'payment_capture': '1',
            })

            return JsonResponse({
                'order_id': order['id'],
                'amount': amount,
            })

        except (ValueError, TypeError, json.JSONDecodeError) as e:
            return JsonResponse({'error': 'Invalid data format'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)




razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

@csrf_exempt
def ticket_payment_success(request):
    if not request.session.get('is_logged_in'):
        return JsonResponse({'error': 'User not logged in'}, status=403)
    if request.method == 'POST':
        try:
          
            data = json.loads(request.body)
            razorpay_payment_id = data['razorpay_payment_id']
            razorpay_order_id = data['razorpay_order_id']
            razorpay_signature = data['razorpay_signature']
            event_id = data['event_id']
            ticket_count = int(data['ticket_count'])

            print("Received Data:", {
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_order_id': razorpay_order_id,
                'razorpay_signature': razorpay_signature,
                'event_id': event_id,
                'ticket_count': ticket_count,
            })

           
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            }

            try:
                print("Attempting to verify payment signature...")
                razorpay_client.utility.verify_payment_signature(params_dict)
                print("Payment signature verified successfully!")
            except razorpay.errors.SignatureVerificationError as e:
                print("Signature verification failed:", str(e))
                return JsonResponse({'status': 'error', 'message': 'Payment verification failed'}, status=400)
            except Exception as e:
                print("Unexpected error during verification:", str(e))
                return JsonResponse({'status': 'error', 'message': 'Payment verification failed'}, status=400)

            
            username = request.session.get('username')
            print("user",username)
            if not username:
                return JsonResponse({'status': 'error', 'message': 'User not logged in'}, status=400)

            try:
               
                user_profile = UserProfile.objects.get(username=username)
                print("UserProfile fetched successfully:", user_profile.username)
            except UserProfile.DoesNotExist as e:
                print("Error fetching UserProfile:", str(e))
                return JsonResponse({'status': 'error', 'message': 'User profile not found'}, status=400)

           
            event = Event.objects.get(id=event_id)
            ticket = EventTicket(
                user_profile=user_profile,
                event=event,
                ticket_count=ticket_count,
                amount=event.price * ticket_count,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_order_id=razorpay_order_id,
                razorpay_signature=razorpay_signature,
            )
            ticket.save()

            return JsonResponse({'status': 'success'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
        except KeyError as e:
            return JsonResponse({'status': 'error', 'message': f'Missing key: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

def booking_success(request):
    if not request.session.get('is_logged_in'):
        return JsonResponse({'error': 'User not logged in'}, status=403)
    return render(request, 'user/booking_success.html')



def profile(request):
   
    if not request.session.get('is_logged_in'):
        messages.error(request, 'User not logged in')
        return redirect('home')

   
    username = request.session.get('username')
    user_profile = get_object_or_404(UserProfile, username=username)

   
    organized_events = user_profile.organized_events.annotate(
        total_tickets_sold=Sum(F('tickets__ticket_count'), default=Value(0)),  
        total_revenue=Sum(F('tickets__amount'), default=Value(0))  
    )

   
    return render(request, 'user/profile.html', {
        'user_profile': user_profile,
        'organized_events': organized_events, 
         'now': now(),
    })





def update_profile_image(request):
    if request.method == 'POST' and request.FILES.get('image'):
        if 'username' in request.session:
            username = request.session['username']
        else:
            return JsonResponse({'success': False, 'message': 'User not logged in'})

        try:
            user_profile = UserProfile.objects.get(username=username)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User profile not found'})

        image = request.FILES['image']
        user_profile.image = image
        user_profile.save()

        # Log the image URL for debugging
        print("Updated Image URL:", user_profile.image.url)

        return JsonResponse({
            'success': True,
            'image_url': user_profile.image.url  # Ensure this URL is correct
        })

    return JsonResponse({'success': False, 'message': 'Invalid request'})


def update_profile_details(request):
    if request.method == 'POST':
       
        if 'username' not in request.session:
            return JsonResponse({'success': False, 'message': 'User not found '})

        username = request.session['username']

        try:
          
            user_profile = UserProfile.objects.get(username=username)

          
            data = json.loads(request.body)
            fullname = data.get('fullname')
            phone_number = data.get('phone_number')

            if not fullname or not phone_number:
                return JsonResponse({'success': False, 'message': 'Both fields are required'})

          
            user_profile.full_name = fullname
            user_profile.phone_number = phone_number
            user_profile.save()

            return JsonResponse({
                'success': True,
                'fullname': user_profile.full_name,
                'phone_number': user_profile.phone_number
            })

        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User profile not found'})

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid request method'})


def edit_event(request, event_id):
   
    event = get_object_or_404(Event, id=event_id)

   
    if 'username' not in request.session:
        return JsonResponse({'success': False, 'message': 'User not logged in'})

   
    if event.date < timezone.now():
        return JsonResponse({'success': False, 'message': 'Event has already passed and cannot be edited'})

   
    total_sold_tickets = EventTicket.objects.filter(event=event).aggregate(total_sold=Sum('ticket_count'))['total_sold'] or 0
    if total_sold_tickets > 0:
        return JsonResponse({'success': False, 'message': 'Event tickets have already been sold, cannot edit'})

    if request.method == 'POST':
      
        event.title = request.POST.get('title', event.title)
        event.description = request.POST.get('description', event.description)
        event.date = request.POST.get('date', event.date)
        event.price = request.POST.get('price', event.price)
        event.location = request.POST.get('location', event.location)
        event.category = request.POST.get('category', event.category)
        event.ticket_count = request.POST.get('ticket_count', event.ticket_count)
        
      
        if 'image' in request.FILES:
            event.image = request.FILES['image']

        event.save()

      
        return JsonResponse({'success': True, 'message': 'Event updated successfully'})

    return render(request, 'user/edit_event.html', {'event': event})

def static_page(request):
   
    return render(request, 'user/about.html')

def logout_view(request):
    request.session.flush()  
    return redirect('home')