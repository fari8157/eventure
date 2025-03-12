from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import qrcode
from io import BytesIO
import os
from django.core.files.base import ContentFile
import cloudinary.uploader
from django.core.mail import EmailMultiAlternatives
import base64
import uuid

class UserProfile(models.Model):
    full_name = models.CharField(max_length=255)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=False)
    is_active = models.BooleanField(default=True)
    password = models.CharField(max_length=128)  
    is_subscribed = models.BooleanField(default=False) 
    subscribed_date = models.DateTimeField(null=True, blank=True)
    image = models.ImageField(upload_to='static/media/profile_images/', blank=True, null=True)
    is_admin = models.BooleanField(default=False)



    def __str__(self):
        return self.username
    @property
    def active_subscription(self):
        # Returns the most recent active subscription, if any
        return self.subscriptions.order_by('-date').first()


class Subscription(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='subscriptions')
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateTimeField(default=timezone.now)  # Automatically set to the current date and time

    def __str__(self):
        return f"Subscription for {self.user_profile.username} on {self.date}"   

class Event(models.Model):
     CATEGORY_CHOICES = [
            ('music', 'Music'),
            ('sports', 'Sports'),
            ('art', 'Art'),
            ('tech', 'Technology'),
            ('food', 'Food & Drink'),
            ('other', 'Other'),
        ]

     title = models.CharField(max_length=255)
     description = models.TextField()
     date = models.DateTimeField()  # Event date provided by the creator
     price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
     location = models.CharField(max_length=255)
     category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
     image = models.ImageField(upload_to='static/media/statevent_images/', blank=True, null=True)
     created_at = models.DateTimeField(auto_now_add=True)  # Automatically set to the current date and time
     updated_at = models.DateTimeField(auto_now=True)  # Automatically updated on every save
     organizer = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='organized_events')
     ticket_count = models.PositiveIntegerField(default=0)
     def __str__(self):
            return self.title    

class EventTicket(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='tickets')
    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='tickets')
    ticket_count = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    booking_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
 
   
    

    def __str__(self):
        return f"{self.user_profile.username} - {self.event.title}"

    def save(self, *args, **kwargs):
        # Reduce the ticket count in the Event model
        if not self.pk:  # Only for new tickets
            self.event.ticket_count -= self.ticket_count
            self.event.save()
        super().save(*args, **kwargs)

        # Send email after successful booking
        if self.razorpay_payment_id:  # Ensure payment is successful
            self.send_confirmation_email()

    def send_confirmation_email(self):
    # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_data = f"Event: {self.event.title}\nDate: {self.event.date}\nLocation: {self.event.location}\nTickets: {self.ticket_count}"
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Save QR code to a BytesIO object
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        buffered.seek(0)

        # Upload QR code to Cloudinary
        upload_result = cloudinary.uploader.upload(
            buffered,
            folder="qr_codes",  # Optional: Organize images in a folder
            public_id=f"qr_code_{self.id}",  # Unique ID for the image
        )
        qr_code_url = upload_result['secure_url']  # Get the public URL of the uploaded image
        print("QR Code URL:", qr_code_url)  # Debugging

        # Render HTML email template
        html_message = render_to_string('emails/ticket_confirmation.html', {
            'ticket': self,
            'event': self.event,
            'user': self.user_profile,
            'qr_code_url': qr_code_url,  # Pass the QR code URL to the template
        })
        plain_message = strip_tags(html_message)

        # Send email
        email = EmailMultiAlternatives(
            subject=f"Your Ticket Confirmation for {self.event.title}",
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[self.user_profile.email],
        )
        email.attach_alternative(html_message, "text/html")
        email.send()
