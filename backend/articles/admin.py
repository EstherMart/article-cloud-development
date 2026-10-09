from django.contrib import admin

from .models import Article, Author, Tag


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'area', 'processing_status', 'user', 'upload_datetime')
    list_filter = ('processing_status', 'area')
    search_fields = ('title', 'authors__name', 'tags__name')


admin.site.register(Author)
admin.site.register(Tag)
