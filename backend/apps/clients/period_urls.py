from django.urls import path
from . import period_views

urlpatterns = [
    path('', period_views.period_list_view),
    path('<uuid:period_id>/', period_views.period_detail_view),
    path('<uuid:period_id>/lock/', period_views.period_lock_view),
]
