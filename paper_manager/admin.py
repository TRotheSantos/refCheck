from django.contrib import admin
from .models import Paper, Source, Citation, Check, Reference, PaperAttribute, Author

"""
Admin models to modify admin pages
"""


# Register your models here.
class PaperAttributeInline(admin.TabularInline):
    can_delete = True
    can_edit = True
    model = PaperAttribute
    extra = 1
    fields = ('label', 'value',)


class PaperAdmin(admin.ModelAdmin):
    inlines = (PaperAttributeInline,)


class CitationInline(admin.TabularInline):
    model = Citation
    fields = ('replaced', 'text', 'type',)
    extra = 0


class ReferenceInline(admin.TabularInline):
    model = Reference
    fields = ('replaced', 'citation_marker', 'source',)
    extra = 0


class CheckAdmin(admin.ModelAdmin):
    list_display = ('reference', 'citation', 'chunk_id', 'paper', 'difference_short', 'score', 'user_score', 'false_positive')
    list_filter = ('paper', 'false_positive', 'score', 'user_score')
    search_fields = ('paper', 'citation', 'reference', 'chunk_id', 'difference_short', 'semantic_difference', 'score', 'user_score', 'false_positive')
    inlines = (CitationInline, ReferenceInline,)


# admin.site.register(PaperAttribute)  # currently accessible via the parent Paper, for uniformity, can be registered separately too
admin.site.register(Author)
admin.site.register(Paper, PaperAdmin)
admin.site.register(Source)
admin.site.register(Citation)
admin.site.register(Check, CheckAdmin)
admin.site.register(Reference)
