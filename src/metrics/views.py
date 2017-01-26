from os.path import join
from django.conf import settings
from annoying.decorators import render_to

@render_to('metrics/index.html')
def index(request):
    return {
        'readme': open(join(settings.PROJECT_DIR, 'README.md'), 'r').read()
    }
