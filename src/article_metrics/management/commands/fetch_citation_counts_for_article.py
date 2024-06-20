from django.core.management.base import BaseCommand
from article_metrics.crossref.citations import count_for_doi
from article_metrics.models import Article
from article_metrics.utils import msid2doi, get_article_versions

class Command(BaseCommand):
    help = 'A utility to fetch citation counts for all versions of a given article'

    def add_arguments(self, parser):
        parser.add_argument('article_id', type=int, help='Article id to fetch citations for e.g. 85111')

    @staticmethod
    def get_article_by_doi(article_doi):
        try:
            article = Article.objects.get(doi=article_doi)
            return article
        except Article.DoesNotExist:
            return None

    @staticmethod
    def get_citations_for_all_versions(article_id):
        results = []

        umbrella_doi = msid2doi(article_id)
        umbrella_doi_results = count_for_doi(umbrella_doi)
        if not umbrella_doi_results:
            return results

        results.append(umbrella_doi_results)

        for version in get_article_versions(article_id):
            doi = f"{msid2doi(article_id)}.{version}"
            count_data = count_for_doi(doi)
            results.append(count_data)

        return results

    def handle(self, *args, **options):
        article_id = options['article_id']

        article = self.get_article_by_doi(msid2doi(article_id))
        if not article:
            self.stdout.write(f'Article with doi {article_id} does not exist')
            return

        self.stdout.write(f'Article with id {article_id} exists')

        citation_data = self.get_citations_for_all_versions(article_id)
        self.stdout.write(f'Citation data for {article_id}: {citation_data}')

        combined_citation_data = count_for_doi(msid2doi(article_id), include_all_versions=True)
        self.stdout.write(f'Combined citation data for {article_id}: {combined_citation_data}')
