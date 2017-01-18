from os.path import join
from django.conf import settings
from django.shortcuts import get_object_or_404
from annoying.decorators import render_to
import logic, models

from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def metrics(request, type, id, metric):
    pass
