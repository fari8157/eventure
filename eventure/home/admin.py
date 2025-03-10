from django.contrib import admin
from .models import UserProfile,Subscription,Event,EventTicket

admin.site.register(UserProfile)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user_profile', 'razorpay_payment_id', 'razorpay_order_id', 'razorpay_signature', 'date')
    list_filter = ('date', 'user_profile')
    search_fields = ('user_profile__username', 'razorpay_payment_id', 'razorpay_order_id')
    date_hierarchy = 'date'
    ordering = ('-date',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_profile')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):

    list_display = ('title', 'organizer', 'date', 'category', 'created_at')
    
    list_filter = ('category', 'date', 'created_at')
    
   
    search_fields = ('title', 'description', 'location')
    
   
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'date', 'price', 'location', 'category', 'image', 'organizer', 'ticket_count')
        }),
        ('Advanced Options', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),  # Collapse this section by default
        }),
    )
    
    # Read-only fields in the admin form
    readonly_fields = ('created_at', 'updated_at')
    
 
    # Customize the organizer field to show usernames in the dropdown
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'organizer':
            kwargs['queryset'] = UserProfile.objects.all().order_by('username')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    


@admin.register(EventTicket)
class EventTicketAdmin(admin.ModelAdmin):
    # List of fields to display in the admin list view
    list_display = ('id', 'user_profile', 'event', 'ticket_count', 'booking_date', 'amount', 'razorpay_payment_id', 'razorpay_order_id', 'razorpay_signature')
    
    # Fields to filter by in the admin list view
    list_filter = ('event', 'booking_date', 'user_profile')
    
    # Fields to search by in the admin list view
    search_fields = ('user_profile__username', 'event__title', 'razorpay_payment_id', 'razorpay_order_id')
    
    # Fields to make editable directly in the admin list view
    list_editable = ('ticket_count', 'amount')
    
    # Fields to group in the admin detail view
    fieldsets = (
        ('User Details', {
            'fields': ('user_profile', 'event'),
        }),
        ('Booking Details', {
            'fields': ('ticket_count', 'booking_date', 'amount'),
        }),
        ('Payment Details', {
            'fields': ('razorpay_payment_id', 'razorpay_order_id', 'razorpay_signature'),
        }),
    )
    
    # Automatically populate fields based on other fields
    readonly_fields = ('booking_date',)  # Make booking_date read-only
    
    # Add a date hierarchy for easy navigation by date
    date_hierarchy = 'booking_date'
