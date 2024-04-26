"""""
The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views
from .views import UpdatePaperView

# out-commented paths for later scrum iterations
urlpatterns = [
    path('', views.dashboard, name='home'),
    path('dashboard', views.dashboard, name='dashboard'), # view dashboard with all checked papers and possibility to add new paper
    path('<int:id>', views.paper, name='paper'), # view paper with all checks if checked one, future: else all papers it got referenced in (& the checks), maybe different metrics
    path('set_score/<int:id>', views.set_score, name='set_score'), # set score for check
    path('set_false_positive/<int:id>/', views.set_false_positive, name='set_false_positive'), # set check false positive
    path('<int:id>/missing_sources', views.missing_sources, name='missing_sources'), # view missing sources for paper
    path('update_paper/<int:source_id>', UpdatePaperView.as_view(), name='update_paper'), # update missing source paper with file
    # path('all', views.list_papers, name='list_papers'), # view all owned papers (checked &source papers)
    # path('<int:id>/view/', views.view_paper, name='view_paper'),  # view original document, optional with parameter page or check_id
    # path('<int:id>/view/<int:page>', views.view_paper, name='view_paper'),  # view original document on specific page, maybe not url but parameter?
    # path('<int:id>/view/<str:passage>', views.view_paper, name='view_paper'),  # view original document (.txt) focused/highlightedon specific passage, maybe not url but parameter?
    path('<int:paper_id>/edit/<int:citation_id>', views.change_citation, name='change_citation'),
    # on GET view of chunk & neighbouring chunks to adjust scope, on POST change citation according to marked passages
    path('<int:id>/add_citation', views.add_citation, name='add_citation'), # to add citations not found by the llm
    # on GET view like change_citation of plain text to mark, but whole paper, on POST add citation according to marked passages and containing chunk
    path('citation_detail/', views.citation_detail, name='citation_detail'),
    path('edit_source/', views.edit_reference, name='edit_reference'),
    path('test/', views.test, name='test'),
]
