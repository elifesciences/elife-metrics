import base
from os.path import join

class PM(base.BaseCase):
    def test_response_parsing(self):
        join(self.fixture_dir, 'pm', 'pm-citation-response.json')
