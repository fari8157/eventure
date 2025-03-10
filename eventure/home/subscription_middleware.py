from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from .models import UserProfile
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_subscription_expired_email(user, login_url):
    subject = "Your Haven Subscription Has Expired"
    html_message = render_to_string('emails/subscription_expired.html', {
        'user': user,
        'login_url': login_url,  # Pass the login URL to the template
    })
    plain_message = strip_tags(html_message)  # Fallback for plain text
    from_email = 'support@haven.com'
    to_email = user.email

    email = EmailMessage(subject, html_message, from_email, [to_email])
    email.content_subtype = "html"  # Set the email content type to HTML
    email.send()
class SubscriptionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Check if the user is logged in using session
        if request.session.get('is_logged_in'):
            try:
                # Get the user's profile using the username stored in the session
                username = request.session.get('username')
                user_profile = UserProfile.objects.get(username=username)

                # Check if the user is subscribed
                if user_profile.is_subscribed and user_profile.subscribed_date:
                    # Calculate the subscription expiry date (1 month after subscribed_date)
                    expiry_date = user_profile.subscribed_date + timezone.timedelta(days=30)

                    # Check if the subscription has expired
                    if timezone.now() > expiry_date:
                        # Update the user's subscription status
                        user_profile.is_subscribed = False
                        user_profile.subscribed_date = None
                        user_profile.save()
                        request.session['is_subscribed'] =False
                        login_url = "http://127.0.0.1:8000/login/"  # Replace with your login URL
                        send_subscription_expired_email(user_profile, login_url)
            except UserProfile.DoesNotExist:
                pass  # Handle the case where the user profile does not exist

        return None