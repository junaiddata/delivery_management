from django.urls import path
from . import views
from .views import *
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', home, name='home'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/search/', views.order_search, name='order_search'),  # New URL for AJAX search
    path('upload/', views.upload_file, name='upload_file'),
    path('vehicles/<int:vehicle_id>/update/', views.update_vehicle, name='update_vehicle'),
    path('vehicles/12/update/', views.update_vehicle, name='selfupdate_vehicle'),
    path('vehicles/13/update/', views.update_vehicle, name='grvupdate_vehicle'),
    path('vehicles/20/update/', views.update_vehicle, name='selfpartial_vehicle'),
    path('vehicles/21/update/', views.update_vehicle, name='hold_vehicle'),
    path('vehicles/22/update/', views.update_vehicle, name='cancelled_do'),
    path('update/<str:do_number>/', views.update_order, name='update_order'),
    path('export/', views.export_orders_to_excel, name='export_orders_to_excel'),
    path('delete_all/', views.delete_all_orders, name='delete_all_orders'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('delete_order/<str:do_number>', views.delete_order, name='delete_order'),

    path('security/vehicles/', views.security_vehicle_list, name='security_vehicle_list'),
    path('security/vehicles/<int:vehicle_id>/update_status/', views.update_vehicle_status, name='update_vehicle_status'),
    path('security/vehicles/<int:vehicle_id>/verify/', views.security_verify, name='security_verify'),

    path('salesman/orders/', salesman_orders, name='salesman_orders'),
    path('salesman/do/<str:do_number>/items/', do_items, name='do_items'),


    path('driver/vehicle/', views.driver_vehicle_list, name='driver_vehicle_list'),
    path('driver/vehicle/<int:vehicle_id>/update/', views.update_do_status, name='update_do_status'),


     path('warehouse/pending-dos/', pending_do_list, name='pending_do_list'),

     path('orders/add_vehicle/', add_vehicle, name='add_vehicle'),

          path('orders/bulk_update_do_status/', views.bulk_update_do_status, name='bulk_update_do_status'),
     path("webhook/", whatsapp_webhook, name="whatsapp-webhook"),

    path('accounts/delivered-orders/', account_delivered_orders, name='account_delivered_orders'),
    path('accounts/received-orders/', received_list, name='received_list'),
    path('accounts/delivered-orders/<int:order_id>/mark-received/', mark_received_by_accounts, name='mark_received_by_accounts'),
    path("messages-dashboard/", messages_dashboard, name="messages_dashboard"),



    path('transfers/', views.transfer_list, name='transfer_list'),
    path('transferupload/', views.transfer_upload_file, name='transfer_upload_file'),
    path('transfervehicles/<int:vehicle_id>/update/', views.transfer_update_vehicle, name='transfer_update_vehicle'),
    path('transfervehicles/', views.transfer_vehicle_list, name='transfer_vehicle_list'),

    ##############################################   CREDIT RELATED URLS  #############################################
    path('customers/', views.customer_list, name='customer_list'), #for customers list
    path('md/pending_requests/', views.md_pending_requests, name='md_pending_requests'), #for md pending requests
    path('md/approve_request/<int:entry_id>/', views.approve_credit_request, name='approve_credit_request'), #for approve credit request MD
    path('md-customer-entries/', views.md_customer_entries, name='md_customer_entries'), #for md customer entries
    path('customers/credit', views.customer_credit_list_and_update, name='customer_credit_list'), #for customer credit list and update



    path('customers/<int:customer_id>/payments/', payment_status_by_customer, name='payment_status_by_customer'),
    path('customer/<int:customer_id>/credit-entry/<int:entry_id>/', views.customer_credit_entries, name='customer_credit_entries'),
    path('customer/<int:customer_id>/credit-entry/<int:entry_id>/check-cheque-date/', views.check_cheque_date, name='check_cheque_date'),
    path('customer/<int:customer_id>/credit-entry/<int:entry_id>/mark-payment-received/', views.mark_payment_received, name='mark_payment_received'),

    path('customer/<int:customer_id>/credit-entry/<int:entry_id>/submit-to-md/', views.submit_request_to_md, name='submit_request_to_md'),
    path('creditdashboard/', views.md_dashboard, name='md_dashboard'), #for credit dashboard
    path('password-gate/', views.password_gate, name='password_gate'),
    path('upload/invoice',views.upload_invoices, name='upload_invoices'),
    path('export/customers/', views.export_customer_names, name='export_customer_names'),
    path('upload/customers/', views.upload_customer_limits, name='upload_customer_limits'),

    path('credit-dashboard/', credit_dashboard, name='credit_dashboard'),
    path(
        'customer/<int:customer_id>/combined-entries/',
        views.combined_customer_entries,
        name='combined_customer_entries'
    ),
    path('customer/<int:customer_id>/bulk-update-cheque-dates/',
         views.bulk_update_cheque_dates,
         name='bulk_update_cheque_dates'),
    path('customer/<int:customer_id>/bulk-mark-paid/',
         views.bulk_mark_paid,
         name='bulk_mark_paid'),
    path('customer/<int:customer_id>/bulk-submit-to-md/',
         views.bulk_submit_to_md,
         name='bulk_submit_to_md'),
    path('customer/<int:customer_id>/select-entries/',
         views.select_entries_for_combined_view,
         name='select_entries'),

    path('credit/bulk-upload', views.bulk_upload_credit_notes, name='bulk_upload_credit_notes'),
    path('do/manualwriting/', views.enter_do_number, name='enter_do_number'),
    path('entered-history/', entered_do_history, name='entered-do-history'),


    path('api/orders/json/',views.all_orders_json,name='orders_json'),
         path('md/approve-bulk/<int:bulk_id>/', views.approve_bulk_credit_request, name='approve_bulk_credit_request'),
    path('refresh-customer-stats/', views.refresh_customer_stats, name='refresh_customer_stats'),

    path("api/messages/status/", message_status_list, name="message_status_list"),
    path('customer-stats/', views.customer_frequency_analysis, name='customer_frequency_analysis'),



]


urlpatterns += [

path('sap-invoices/upload/', views.sap_invoices_upload, name='sap_invoices_upload'),
path('sap-invoices/', views.sap_invoices_list, name='sap_invoices_list'),
path('sap-invoices/credit-upload/', views.sap_credit_upload, name='sap_credit_upload'),
path('credit/customer-frequency-sap/', views.customer_frequency_analysis_sap, name='customer_frequency_analysis_sap'),
# optional CSV export of the frequency view
path('credit/customer-frequency-sap/export.csv', views.customer_frequency_export_sap, name='customer_frequency_export_sap'),
]