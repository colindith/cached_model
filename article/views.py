from rest_framework.decorators import api_view
from rest_framework.response import Response

from article.models import PlanPacket, Plan

@api_view()
def test(request):
    # pk is not setted, set pk to auto-increase integer
    PlanPacket.objects.all()

    article = PlanPacket('this is title', 'this is body')
    article.save()

    plan_dict = {
        'game': 1,
        'plan_packet': 2,
        'game_schedule': [123, 456, 678],
        '_bet_set': [{'code': 'p1_gr_2', 'display_name': '1', 'win': True}, {'code': 'p1_gr_3', 'display_name': '5'}],
        'vitality': 3,
        'issue_number_short': 1
    }
    plan = Plan.objects.create(**plan_dict)

    plan_qs = Plan.objects.all()

    aaa = list(PlanPacket.objects.all())

    # display the title and body here


    context = aaa
    print(plan_qs)
    return Response(context)
