from django.urls import include, path
from . import views

# TODO: Document the API here? Sphinx best practices?

urlpatterns = [
    path('names/', views.TestSpecCreatorNamesPage.as_view(), name='names'),
    path('upload', views.TestSpecCreatorUploadPDFPage.as_view(), name='upload'),
    # path('id_page/<str:slug>', views.TestSpecCreatorIDPage.as_view(), name='id_page'),
    path('id_page/', views.TestSpecCreatorIDPage.as_view(), name='id_page'),
    path('questions/', views.TestSpecCreatorQuestionsPage.as_view(), name='questions'),
    path('questions/<int:q_idx>', views.TestSpecCreatorQuestionDetailPage.as_view(), name='q_detail'),
    path('dnm_pages/', views.TestSpecCreatorDNMPage.as_view(), name='dnm_page'),
    path('summary/', views.TestSpecSummaryView.as_view(), name='summary'),
    path('reset/', views.test_spec_reset_view_pdf, name='reset'),
    path('pages/<int:num_pages>', views.test_spec_creator_view_pdf, name='pages'),
    path('pages/<str:slug>', views.test_spec_creator_image_view, name='pages_img'),
]