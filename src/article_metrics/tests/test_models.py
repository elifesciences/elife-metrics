from .base import BaseCase
from article_metrics import models
from django.conf import settings
from django.core.exceptions import ValidationError

class One(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_doi_validator(self):
        valid_dois = [settings.DOI_PREFIX]
        for prefix in valid_dois:
            models.validate_doi(prefix) # raises ValidatorError if not supported

    def test_doi_validator_invalid(self):
        invalid_dois = ['', {}, [], None, 1, '00.0000/foo.bar']
        for invalid_prefix in invalid_dois:
            self.assertRaises(ValidationError, models.validate_doi, invalid_prefix)

    def test_doi_validator_with_models(self):
        valid_art = models.Article(doi=settings.DOI_PREFIX + '/foo.bar')
        valid_art.save() # no validation error

    def test_doi_validator_with_models_invalid(self):
        invalid_art = models.Article(doi='00.0000/foo.bar')
        self.assertRaises(ValidationError, invalid_art.save)
