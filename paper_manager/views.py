import asyncio

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse
from django.http import JsonResponse
import json

from paper_analytics.PaperChecker import PaperChecker
from .models import Paper, Source, Check, Author
from .forms import PaperForm, AddPaperFileForm

from paper_retriever.PaperImporter import PaperImporter
from paper_analytics.PaperExtractor import PaperExtractor

content_template = {
    'backlink': "request.META.get('HTTP_REFERER')",  # optional to specify page to return to (and show button)
    'title': 'Test Title Analyse der Praxis von',  # title of the page (h1) if not alternative header
    'subtitle': 'Test Subtitle like bachelor thesis',
    # subtitle/additional infos of the page, shown with title if not alternative header
    'button_onclick': 'reverse("check_paper_upload")',  # together with following optional to specify header button
    'button_icon': 'add',
    'button_text': 'Add Paper',
}

blocks_to_set = {
    'description': 'Test Description',  # optional to specify the pages description according to current page
    'site_title': 'TAB Title',  # title shown on browser tab and window
    'header': '<h1>{{ title }}</h1>',  # optional to use alternative header section
    'content': '<div>{{ page_content }}</div>',  # the sites content
}


def test(request):
    """
    Test view (playground)for testing things out.
    :param request:
    :return:
    """
    if request.user.is_authenticated:
        user_id = request.user.id
    else:
        user_id = None
    content = {
        'site_title': 'TAB Title',
        'backlink': reverse('dashboard'),
        'title': 'Test Title Analyse der Praxis von',
        'subtitle': 'Test Subtitle like bachelor thesis',
        # 'page_content': ['Test Content' for i in range(100)],
        'page_content': '<ul>' + '<li>Test Content</li>' * 100 + '</ul>',
        'button_onclick': "window.location.href = '/add_paper/'",
        'button_icon': 'add',
        'button_text': 'Add Paper',
    }
    # print(content['page_content'])
    return render(request, 'base/base.html', content)


@login_required
def dashboard(request):
    """
    View for displaying the dashboard and handling paper submissions to check.
    on POST loads and imports paper from user
    :param request: the HTTP request object, on POST loads and imports paper from submitted file
    :return: HttpResponse
    (on GET shows upload form for new check/missing reference (if id is set))
    """
    paper = None
    checks_with_user_score_count_percentage = None
    checks_with_score_count_percentage = None
    checked_papers = Paper.objects.filter(checks__isnull=False, user=request.user).distinct()
    # TODO: Possible solution for keeping selected file on validation fail: https://github.com/un1t/django-file-resubmit
    if request.method == 'POST':
        form = PaperForm(request.POST, request.FILES)
        if form.is_valid():
            paper = form.save(commit=False)
            paper.user = request.user
            paper.save()
            author, created = Author.objects.get_or_create(name=form.cleaned_data['author'])
            paper.authors.add(author)


            collection, chunks = asyncio.run(PaperImporter(paper).import_paper())
            # collection is actually a Chroma object/langchain db with correct initialized collection
            # _ calls underlying chromadb functions (not langchain) --> actual collection
            print(collection._collection, "after import")
            # print("chunks:\n",chunks, "\nend chunks\n")
            analyzer = PaperExtractor(paper, collection, chunks)
            asyncio.run(analyzer.extract())
            analyzer = PaperChecker(paper)
            asyncio.run(analyzer.score())

            return redirect('dashboard')
    else:
        form = PaperForm()

    context = {
        # 'title': 'Welcome to RefCheck',
        'subtitle': 'Get started quickly by entering the document to revise.',
        'papers': checked_papers,
        # 'non_false_positive_checks': non_false_positive_checks,
        'form': form,
        'paper': paper,
    }
    return render(request, 'paper_manager/dashboard.html', context)


@login_required
def paper(request, id):
    """
    View for rendering the paper details page with various context data.
    THE paper details page with all checks and metrics for a given paper for a manual revision.

    Parameters:
    - request: The HTTP request object.
    - id: The ID of the paper to be rendered.

    Returns:
    - A rendered HTTP response with the paper details page.
    """
    paper = get_object_or_404(Paper, id=id, user=request.user)
    request.session['last_visited_check_paper'] = id
    missing_sources_query = Source.objects.filter(Q(paper__chroma_collection='') | Q(paper__chroma_collection=None), referenced_in=paper)
    non_false_positive_checks = paper.checks.exclude(false_positive=True)

    context = {
        'backlink': request.META.get('HTTP_REFERER') if request.META.get('HTTP_REFERER') else reverse('dashboard'),
        'title': f'"{paper.title}"',
        'subtitle': f"{', '.join([str(author) for author in paper.authors.all()])}",
        'paper': paper,
        'no_false_pos': no_false_pos(paper),
        'score_overall': get_all_scores(paper),
        'score_negative': 100 - get_all_scores(paper),
        'Ref': no_references(paper),
        'Cit': no_citations(paper),
        'rpc': ref_per_cit(paper),
        'Sources': no_sources(paper),
        'imp_Sources': no_imp_source(paper),
        'imp_sour_Sourc': src_ratio(paper),
        'autochecked': (get_score(paper) / no_citations_2(paper)) * 100,
        'manuchecked': (get_user_score(paper) / no_citations_2(paper)) * 100,
        'checked': get_score(paper),
        'checkedm': get_user_score(paper),
        'missing_sources': missing_sources_query,
        'non_false_positive_checks': non_false_positive_checks,
    }
    return render(request, 'paper_manager/paper.html', context=context)


@csrf_exempt
@login_required
@require_POST
def set_score(request, id):
    """
    Sets the user score for a given check as way to offer manual correction.

    Parameters:
    - request: The HTTP request object.
    - id: The ID of the check.

    Returns:
    - JsonResponse: A JSON response indicating the status of the score setting.
    """
    data = json.loads(request.body)
    score_str = data.get('score').strip()

    if score_str == 'null':
        score = None
    else:
        try:
            score = float(score_str)
        except ValueError:
            return JsonResponse({'error': 'Invalid score format'})

        if not (0 <= score <= 100):
            return JsonResponse({'error': 'Score must be between 0 and 100'})

    check = get_object_or_404(Check, id=id, paper__user=request.user)
    check.user_score = score
    check.save()
    return JsonResponse({'status': 'success'})


def set_false_positive(request, id):
    """
    Set the false positive flag for a check associated with the given ID as way to offer manual correction, that
    given text is not a citation.

    Parameters:
    - request: The request object.
    - id: The ID of the check.

    Returns:
    - JsonResponse: A JSON response indicating the success of the operation.
    """
    try:
        check = get_object_or_404(Check, id=id, paper__user=request.user)
        if check:
            check.false_positive = True
            check.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'No citation associated with this check'})
    except Check.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Check not found'})


@login_required  # TODO: ownership restriction
def missing_sources(request, id):
    """
    A view to display all missing sources for a given paper with all its important attributes for fast manual search.

    Parameters:
    - request: The HTTP request.
    - id: The ID of the paper.

    Returns:
    - A rendered HTTP response.
    """
    paper = Paper.objects.get(id=id)
    checks_for_paper = Check.objects.filter(paper=paper)
    missing_sources_query = Source.objects.filter(Q(paper__chroma_collection='') | Q(paper__chroma_collection=None), referenced_in=paper)
    missing_sources = missing_sources_query.annotate(
        num_references=Count('reference', filter=Q(reference__of_check__in=checks_for_paper))
    )
    full_text_link = paper.attributes.filter(label='full_text_link')

    context = {
        'paper': paper,
        'title': 'Missing Sources of "' + str(paper.title) + '"',
        'subtitle': f'{len(missing_sources)} Missing Source{"" if len(missing_sources) == 1 else "s"}',
        'site_title': 'Missing Sources',
        'missing_sources': missing_sources,
        'fullTextLink': full_text_link,
    }
    return render(request, 'paper_manager/missing_sources.html', context=context)

# TODO login and ownership restriction
class UpdatePaperView(View):
    # TODO: maybe alter to JSON only view like set_false_positive
    def get(self, request, source_id):
        """
        Retrieves a specific source object using the provided source_id and renders an update paper form
        using the retrieved source and its associated paper.
        Parameters:
        - request: The HTTP request.
        - source_id: The unique identifier of the source object to retrieve.
        Returns:
        - The rendered update_paper.html template with the update paper form and the retrieved source.
        """
        source = get_object_or_404(Source, id=source_id)
        form = AddPaperFileForm(instance=source.paper)
        return render(request, 'update_paper.html', {'form': form, 'source': source})

    def post(self, request, source_id):
        """
        Handles the POST request to update a paper, including the logic for handling missing sources,
        by uploading a file to the paper object of the missing source.
        Parameters:
        - self: The instance of the class.
        - request: The HTTP request object.
        - source_id: The ID of the source to be updated.
        Returns:
        - HTTP response, including redirection based on the 'redirect_to' parameter.
        """
        source = get_object_or_404(Source, id=source_id)
        redirect_to = request.GET.get('redirect_to')
        form = AddPaperFileForm(request.POST, request.FILES, instance=source.paper)

        if form.is_valid():
            form.save()
            collection, chunks = asyncio.run(PaperImporter(source.paper).import_paper())
            PaperChecker.score_source_paper(source.paper)  # TODO add spinner or something to indicate processing

            if redirect_to == 'missing_sources':
                return redirect('missing_sources', id=source.referenced_in.id)
            else:
                return redirect('paper', id=source.referenced_in.id)

        return render(request, 'update_paper.html', {'form': form, 'source': source})


def info(request):
    """
    View to handle the 'info' request and render the 'info.html' template with the given context.

    Parameters:
    - request: the request object

    Returns:
    - the rendered 'info.html' template with the given context
    """
    context = {
        'title': 'About RefCheck',
        'subtitle': 'Get to know us and our project.',
        'site_title': 'Info',
    }
    return render(request, 'info.html', context=context)


def landing_page(request):
    """
    View for handling the landing page request.

    Parameters:
    - request: the HTTP request object

    Returns:
    - HTTP response object
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        context = {
            'title': 'About RefCheck',
            'subtitle': 'Explore RefCheck',
            'site_title': 'Landing Page',
        }
        return render(request, 'landing_page.html', context=context)


"""
Further planned placeholder views
------------------------------------------------------------------------------------------------
"""

def list_papers(request):
    """
    View to list all papers available.
    Parameters:
    - request: The HTTP request object.
    Returns:
    - Rendered HTTP response displaying a list of papers.
    """
    papers = Paper.objects.all()
    context = {
        'papers': papers
    }
    return render(request, 'paper_manager/dashboard.html', context)


def view_paper(request, id, page=None, passage=None):
    """
    View to display a paper in detail or its original document.
    Parameters:
    - request: The HTTP request object.
    - id: The ID of the paper to be displayed.
    - page: Optional parameter for pagination.
    - passage: Optional parameter for displaying specific passages containing given passage eg. citation.
    Returns:
    - Rendered HTTP response displaying the paper in detail or its original document.
    """
    paper = Paper.objects.get(id=id)
    return HttpResponse("Paper Document")  # Placeholder for displaying paper in detail/original document


def add_citation(request, id):
    """
    View to handle adding a citation to a given paper.
    Parameters:
    - request: The HTTP request object.
    - id: The ID of the paper to which the citation is being added.
    Returns:
    - JSON response indicating success.
    """
    # Logic for processing the citation addition
    return JsonResponse({'result': 'success'})  # Placeholder JSON response

def change_citation(request, paper_id, citation_id):
    """
    View to handle changing a citation.
    Parameters:
    - request: The HTTP request object.
    - paper_id: The ID of the paper associated with the citation.
    - citation_id: The ID of the citation to be changed.
    Returns:
    - HTTP response object.
    """
    return HttpResponse("Change citation")  # Placeholder for changing citation


def citation_detail(request):
    """
    View to display detailed information about a citation.
    Parameters:
    - request: The HTTP request object.
    Returns:
    - HTTP response object.
    """
    return HttpResponse("Citation detail")  # Placeholder for displaying citation detail/context


def edit_reference(request):
    """
    View to handle editing a reference.
    Parameters:
    - request: The HTTP request object.
    Returns:
    - HTTP response object.
    """
    return HttpResponse("Edit source")  # Placeholder for editing reference specification


# Helper functions

def no_references(paper):
    """
    Counts the number of unique references for a given paper.
    Parameters:
    - paper: The paper object.
    Returns:
    - The count of unique references.
    """
    list_of_ref = []
    for check in Check.objects.filter(paper_id=paper.id):
        to_add = check.references.all()
        for solo_to_add in to_add:
            if solo_to_add not in list_of_ref:
                list_of_ref.append(solo_to_add)

    return len(list_of_ref)


def language(paper):
    """
    Retrieves the full language name for a given paper.
    Parameters:
    - paper: The paper object.
    Returns:
    - The full language name.
    """
    instance = Paper.objects.get(id=paper.id)
    full_language_name = instance.get_full_language_name()
    return full_language_name


def no_citations(paper):
    """
    Counts the number of citations for a given paper.
    Parameters:
    - paper: The paper object.
    Returns:
    - The count of citations.
    """
    list_of_cit = []
    for check in Check.objects.filter(paper_id=paper.id):
        if check not in list_of_cit and not check.false_positive:
            list_of_cit.append(check)
    return len(list_of_cit)


def no_citations_2(paper):
    """
    Counts the number of citations for a given paper.
    Parameters:
    - paper: The paper object.
    Returns:
    - The count of citations.
    """
    list_of_cit = []
    for check in Check.objects.filter(paper_id=paper.id):
        if check not in list_of_cit and not check.false_positive:
            list_of_cit.append(check)
    if len(list_of_cit) != 0:
        return len(list_of_cit)
    else:
        return 1


def get_user_score(paper):
    """
    Retrieves the user score for a given paper.
    Parameters:
    - paper: The paper object.
    Returns:
    - The user score.
    """
    i = 0
    for checks in Check.objects.filter(paper_id=paper.id):
        if checks.user_score is not None and not checks.false_positive:
            i += 1
    return(i)


def get_score(paper):
    """
    Retrieves the score for a given paper.
    Parameters:
    - paper: The paper object.
    Returns:
    - The score.
    """
    i = 0
    for checks in Check.objects.filter(paper_id=paper.id):
        if checks.score is not None and not checks.false_positive:
            i += 1
    return(i)


def get_all_scores(paper):
    """
    Retrieves the average score for all checks associated with a given paper.
    Parameters:
    - paper: The paper object.
    Returns:
    - The average score.
    """
    k = 0
    i = 0
    for check in Check.objects.filter(paper_id=paper.id):
        if check.user_score is not None and not check.false_positive:
            k += check.user_score
            i += 1
        else:
            if check.score is not None and not check.false_positive:
                k += check.score
                i += 1
    if i != 0:
        return (int(k / i))
    else:
        return (0)


def no_sources(paper):
    """
    Counts the total number of sources referenced in a given paper.
    Parameters:
    - paper: The paper object.
    Returns:
    - The count of sources.
    """
    i = 0
    for source in Source.objects.filter(referenced_in=paper.id):
        i += 1
    return (i)


def no_imp_source(paper):
    """
    Counts the number of important sources referenced in a given paper.
    Parameters:
    - paper: The paper object.
    Returns:
    - The count of important sources.
    """
    k = 0
    for source in Source.objects.filter(referenced_in=paper.id):
        if source.paper.chroma_collection is not None:
            k += 1
    return (k)


def no_false_pos(paper):
    """
    Counts the number of false positive checks for a given paper.
    Parameters:
    - paper: The paper object.
    Returns:
    - The count of false positive checks.
    """
    k = 0
    for check in Check.objects.filter(paper_id=paper.id):
        if check.false_positive:
            k += 1
    return (k)


def src_ratio(paper):
    """
    Calculates the source ratio for a given paper.
    Parameters:
    - paper: The paper object.
    Returns:
    - The source ratio.
    """
    if no_sources(paper) != 0:
        return (no_imp_source(paper) / no_sources(paper) * 100)
    else:
        return (0)


def ref_per_cit(paper):
    """
    Calculates the references per citation ratio for a given paper.
    Parameters:
    - paper: The paper object.
    Returns:
    - The references per citation ratio.
    """
    cit = []
    src = []

    for check in Check.objects.filter(paper_id=paper.id):
        checks = check.citations.all()
        for _cit_ in checks:
            if check.citation not in cit and not check.false_positive:
                cit.append(check.citation)

    for source in Source.objects.filter(referenced_in=paper.id):
        if source not in src:
            src.append(source)

    if len(src) != 0:
        result = round(len(cit) / len(src), 2)
        formatted_result = "{:.2f}".format(result)
        return (formatted_result)
    else:
        result = 0
        formatted_result = "{:.2f}".format(result)
        return (formatted_result)