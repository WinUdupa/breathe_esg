from django.urls import path
from . import views

urlpatterns = [
    path('rows/', views.row_list_view),
    path('rows/<uuid:row_id>/', views.row_detail_view),
    path('rows/<uuid:row_id>/edit/', views.row_edit_view),
    path('rows/<uuid:row_id>/accept/', views.row_accept_view),
    path('rows/<uuid:row_id>/reject/', views.row_reject_view),
    path('bulk-accept/', views.bulk_accept_view),
    # Legacy batch-level (backward compat)
    path('batches/<uuid:batch_id>/submit/', views.batch_submit_view),
    path('batches/<uuid:batch_id>/set-in-review/', views.batch_set_in_review_view),
    # Submission-level
    path('submissions/<uuid:submission_id>/set-in-review/', views.submission_set_in_review_view),
    path('submissions/<uuid:submission_id>/submit/', views.submission_analyst_submit_view),
]
