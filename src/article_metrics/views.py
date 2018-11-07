from os.path import join
from django.conf import settings
from annoying.decorators import render_to
import codecs
import markdown

@render_to('metrics/index.html')
def index(request):
    input_file = join(settings.PROJECT_DIR, 'README.md')
    input_file = codecs.open(input_file, 'r', encoding="utf-8")
    return {
        'readme': markdown.markdown(input_file.read())
    }
