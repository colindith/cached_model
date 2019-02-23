from django.db import models

# Create your models here.
from cached_model.libs.cached_table import Model, Field
class Article(Model):
	title = Field()
	body = Field()
