from django.urls import path
from home import views

urlpatterns = [
     path('',  views.home, name='home'),    
     path('login/',  views.user_login, name='login'),
     path('register/',  views.register, name='register'),
     
     path('forgot-password/',  views.forgot_password, name='forgot-password'),
     path('forgot-otp/', views.forgot_otp, name='forgot_otp'),
     path('forgot-resend-otp/', views.forgot_resend_otp, name='forgot-resend-otp'),
     path('reset-password/', views.reset_password, name='reset-password'),
     path('subscription/',  views.subscription, name='subscription'),
     path('verify-otp/', views.verify_otp, name='verify_otp'),
     path('resend-otp/', views.resend_otp, name='resend_otp'),
     path('logout/', views.logout_view, name='logout'),
     path('create-razorpay-order/', views.create_razorpay_order, name='create_razorpay_order'),
     path('payment-success/', views.payment_success, name='payment_success'),
     path('create-event/', views.create_event, name='create_event'),
     path('event/<int:event_id>/', views.event_detail, name='event_detail'),
     path('events/', views.event_list, name='event_list'),
     path('ticket-create-razorpay-order/', views.ticket_create_razorpay_order, name='ticket_create_razorpay_order'),
     path('ticket-payment-success/', views.ticket_payment_success, name='ticket_payment_success'),
     path('booking-success/', views.booking_success, name='booking_success'),
     path('user-profile/', views.profile, name='user_profile'),
     path('update-profile-image/', views.update_profile_image, name='update_profile_image'),
     path('update-profile-details/', views.update_profile_details, name='update_profile_details'),
     path('event/edit/<int:event_id>/', views.edit_event, name='edit_event'),
     path('about-us/', views.static_page, name='about_page'),

]