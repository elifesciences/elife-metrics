from django.contrib import admin
from metrics import models

registrar = [
    (models.Article,),
    (models.Metric,),
    (models.Citation,),
]

[admin.site.register(*row) for row in registrar]
