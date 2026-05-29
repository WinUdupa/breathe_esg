from django.urls import path
from . import views

urlpatterns = [
    # Submission-based flow
    path('submissions/', views.submission_list_view),
    path('submissions/create/', views.submission_create_view),
    path('submissions/<uuid:submission_id>/', views.submission_detail_view),
    path('submissions/<uuid:submission_id>/upload/', views.submission_upload_view),
    path('submissions/<uuid:submission_id>/submit/', views.submission_uploader_submit_view),
    path('files/<uuid:file_id>/delete/', views.file_delete_view),

    # Legacy single-file endpoints (backward compat)
    path('upload/', views.upload_view),
    path('batches/', views.batch_list_view),
    path('batches/<uuid:batch_id>/', views.batch_detail_view),
]
