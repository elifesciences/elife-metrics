from os.path import join
from django.conf import settings
from django.shortcuts import get_object_or_404
from annoying.decorators import render_to
import logic, models

from rest_framework.decorators import api_view
from rest_framework.response import Response

@render_to('metrics/index.html')
def index(request):
    return {
        'readme': open(join(settings.PROJECT_DIR, 'README.md'), 'r').read()
    }
