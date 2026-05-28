from django.urls import path
from . import admin_views

urlpatterns = [
    path('batches/<uuid:batch_id>/finalize/', admin_views.finalize_batch_view),
    path('periods/<uuid:period_id>/lock/', admin_views.lock_period_view),
]
