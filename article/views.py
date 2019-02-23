from rest_framework.decorators import api_view
from rest_framework.response import Response

from article.models import Article

@api_view()
def test(request):
    # pk is not setted, set pk to auto-increase integer
    Article.objects.all()

    article = Article('this is title', 'this is body')
    article.save()

    Article.objects.all()

    # display the title and body here


    context = []
    return Response(context)
