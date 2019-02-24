from django.db import models

# Create your models here.
from cached_model.libs import models as c_models
from django.db import models

class PlanPacket(c_models.Model):
	scheme = c_models.Field()	# TODO: This should be a foreignkey to a real django model
	game_schedule = c_models.Field()	 # list or many-to-many to GameSchedule
	created_at = c_models.Field(auto_now_add=True)
	plan_packet_number = c_models.Field()	# int


class Plan(c_models.Model):
	OPEN = 0  # 待開
	CLOSE = 1  # 過開獎時間未開
	WIN = 2  # 中
	LOSE = 3  # 掛
	CANCELLED = 4
	VOID = 5
	DELAYED = 6  # 已產生新計畫但未開
	STATUS_OPTIONS = (
		(OPEN, 'Open'),
		(CLOSE, 'Close'),
		(WIN, 'Win'),
		(LOSE, 'Lose'),
		(CANCELLED, 'Cancelled'),
		(VOID, 'Void'),
		(DELAYED, 'Delayed')
	)


	game = c_models.Field()
	plan_packet = c_models.ForeignKey(PlanPacket, related_name='plans')
	game_schedule = c_models.Field() 	# list or many-to-many to GameSchedule
	_bet_set = c_models.Field(default=dict)
	# [{'code': 'p1_gr_2', 'display_name': '1', 'win': True}, {'code': 'p1_gr_3', 'display_name': '5'}....]
	status = c_models.Field(default=OPEN, choices=STATUS_OPTIONS)	 # TODO: choice field
	vitality = c_models.Field(default=1)  # 表示Plan可存續的期數
	created_at = c_models.Field(auto_now_add=True)
	plan_number = c_models.Field(default=0)
	issue_number_short = c_models.Field()
