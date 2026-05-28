from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_view),
    path('batches/', views.batch_list_view),
    path('batches/<uuid:batch_id>/', views.batch_detail_view),
]
