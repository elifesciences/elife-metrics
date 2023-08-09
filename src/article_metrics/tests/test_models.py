import pytest
from article_metrics import models
from django.conf import settings
from django.core.exceptions import ValidationError

def test_doi_validator():
    valid_dois = [settings.DOI_PREFIX]
    for prefix in valid_dois:
        models.validate_doi(prefix) # raises ValidatorError if not supported

def test_doi_validator_invalid():
    invalid_dois = ['', {}, [], None, 1, '00.0000/foo.bar']
    for invalid_prefix in invalid_dois:
        with pytest.raises(ValidationError):
            models.validate_doi(invalid_prefix)

@pytest.mark.django_db
def test_doi_validator_with_models():
    valid_art = models.Article(doi=settings.DOI_PREFIX + '/foo.bar')
    valid_art.save() # no validation error

def test_doi_validator_with_models_invalid():
    invalid_art = models.Article(doi='00.0000/foo.bar')
    with pytest.raises(ValidationError):
        invalid_art.save()
