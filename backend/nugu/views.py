from pharmasee.models import Reminder, Pill

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.shortcuts import get_object_or_404

import datetime

version = ""
action = {}
action_name = ""
params = {}
output = {}

def parse_play_request(body):
    global version, action, action_name, params, output
    try:
        version = body.get('version')
        action = body.get('action')
        action_name = action.get('actionName')
        params = action.get('parameters')
        output = dict(zip(params.keys(), [val.get('value') for val in params.values()]))
    except:
        return Response(status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def answer_taken_pills(request):
    parse_play_request(request.data)

    if action_name != "answer.taken_pills":
        return Response(status=status.HTTP_400_BAD_REQUEST)

    context = {
        "version": version,
        "resultCode": "OK",
        "output": output,
        "directives":[]
    }

    response_taken = ""

    # if len(Reminder.objects.filter(User=~~~)) == 0:
    if len(Reminder.objects.all()) == 0:
        response_taken = "복용 리스트에 등록된 약이 없습니다."
        context['output']['response_taken'] = response_taken
        return Response(context)
    
    # 오늘 먹은 약: 제시간에 복용한 약 / 복용은 했으나 제시간에 복용하지 않은 약 
    qs_taken = Reminder.objects.filter(is_taken_today=True).order_by('taken_time')

    num_taken = len(qs_taken)
    late_pills = ""
    if num_taken == 0:
        response_taken = "오늘 복용한 약이 없습니다."

    elif num_taken > 0:
        taken_dict = {}
        for obj in qs_taken:
            pill_obj = get_object_or_404(Pill, id=obj.pill_id.id)
            if response_taken: 
                response_taken += ", "

            ampm = '오전' if obj.taken_time.strftime("%p") == "AM" else "오후"
            takentime = ampm + obj.taken_time.strftime(" %I시 %M분")

            if taken_dict.get(takentime):
                taken_dict[takentime].append(pill_obj.name +  " " + str(obj.dose_taken_today) + "정")
            else:
                taken_dict[takentime] = [pill_obj.name +  " " + str(obj.dose_taken_today) + "정"]

            dummy = datetime.date(1, 1, 1)
            when_to_take = datetime.datetime.combine(dummy, obj.when_to_take)
            taken_time = datetime.datetime.combine(dummy, obj.taken_time)
            diff_hours = (taken_time - when_to_take).total_seconds() / 3600
            
            if diff_hours > 2:
                if late_pills:
                    late_pills += ", "
                ampm = '오전' if obj.when_to_take.strftime("%p") == "AM" else "오후"
                late_pills += ampm + obj.when_to_take.strftime(" %I시 %M분") + '에 예정된 ' + pill_obj.name + " " + str(obj.dose) + "정"   

        responses = []
        for time, taken_pills in taken_dict.items():
            responses.append(time + "에 " + ",".join(taken_pills))

        # response_taken += "을 복용하셨습니다."
        response_taken += ", ".join(responses) + "을 복용하셨습니다."

        if late_pills:
            response_taken += (late_pills + "을, 2시간 이상 늦게 복용하셨으니 주의 부탁드립니다.")

    else:
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    context['output']['response_taken'] = response_taken
    
    return Response(context)

@api_view(['POST'])
def answer_not_taken_pills(request):
    parse_play_request(request.data)

    if action_name != "answer.not_taken_pills":
        return Response(status=status.HTTP_400_BAD_REQUEST)

    context = {
        "version": version,
        "resultCode": "OK",
        "output": output,
        "directives":[]
    }

    response_not_taken = ""
    response_overdue = ""
    response_scheduled = ""

    if len(Reminder.objects.all()) == 0:
        response_not_taken = "복용 리스트에 등록된 약이 없습니다."
        context['output']['response_not_taken'] = response_not_taken
        return Response(context)
    
    # assume time is 6pm for sake of demo.
    now = datetime.time(19, 40, 0)

    # qs_overdue = Reminder.objects.filter(when_to_take__lte=datetime.datetime.now().time()).filter(is_taken_today=False).order_by('when_to_take')
    # qs_scheduled = Reminder.objects.filter(when_to_take__gt=datetime.datetime.now().time()).filter(is_taken_today=False).order_by('when_to_take')
    qs_overdue = Reminder.objects.filter(when_to_take__lte=now).filter(is_taken_today=False).order_by('when_to_take')
    qs_scheduled = Reminder.objects.filter(when_to_take__gt=now).filter(is_taken_today=False).order_by('when_to_take')

    overdue_dict = {}
    if len(qs_overdue) > 0:        
        for obj in qs_overdue:
            pill_obj = get_object_or_404(Pill, id=obj.pill_id.id)
            
            ampm = '오전' if obj.when_to_take.strftime("%p") == "AM" else "오후"
            timetotake = ampm + obj.when_to_take.strftime(" %I시 %M분")
            
            if overdue_dict.get(timetotake):
                overdue_dict[timetotake].append(pill_obj.name + " " + str(obj.dose) + "정")
            else:
                overdue_dict[timetotake] = [pill_obj.name + " " + str(obj.dose) + "정"]
        
        responses = []
        for time, pills_to_take in overdue_dict.items():
            responses.append(time + "에 예정된 " + ", ".join(pills_to_take))
            
        response_overdue += ", ".join(responses) + "을 아직 복용하지 않았습니다. 확인 부탁드립니다."

    scheduled_dict = {}
    if len(qs_scheduled) > 0:
        for obj in qs_scheduled:
            pill_obj = get_object_or_404(Pill, id=obj.pill_id.id)
        
            ampm = '오전' if obj.when_to_take.strftime("%p") == "AM" else "오후"
            timetotake = ampm + obj.when_to_take.strftime(" %I시 %M분")

            if scheduled_dict.get(timetotake):
                scheduled_dict[timetotake].append(pill_obj.name + " " + str(obj.dose) + "정")
            else:
                scheduled_dict[timetotake] = [pill_obj.name + " " + str(obj.dose) + "정"]
        
        responses = []
        for time, pills_to_take in scheduled_dict.items():
            responses.append(time + "에 " + ", ".join(pills_to_take))
        
        response_scheduled += ", ".join(responses) + "을 복용할 예정입니다."

    if len(qs_overdue) == 0 and len(qs_scheduled) == 0:
        response_not_taken = "오늘 예정된 모든 약을 복용하셨습니다."
    else:
        response_not_taken = response_overdue + response_scheduled
    
    context['output']['response_not_taken'] = response_not_taken
    
    return Response(context)

@api_view(['POST'])
def answer_total_status(request):
    parse_play_request(request.data)

    if action_name != "answer.total_status":
        return Response(status=status.HTTP_400_BAD_REQUEST)

    context = {
        "version": version,
        "resultCode": "OK",
        "output": output,
        "directives":[]
    }

    response_total_status = ""

    if len(Reminder.objects.all()) == 0:
        response_total_status = "복용 리스트에 등록된 약이 없습니다."
        context['output']['response_total_status'] = response_total_status
        return Response(context)

    qs_taken = Reminder.objects.filter(is_taken_today=True).order_by('taken_time')
    qs_overdue = Reminder.objects.filter(when_to_take__lte=datetime.datetime.now().time()).filter(is_taken_today=False).order_by('when_to_take')
    qs_scheduled = Reminder.objects.filter(when_to_take__gt=datetime.datetime.now().time()).filter(is_taken_today=False).order_by('when_to_take')

    response_taken = ""
    late_pills = ""
    num_taken = len(qs_taken) 
    if num_taken == 0:
            response_taken = "오늘 복용한 약이 없습니다."

    elif num_taken > 0:
        for obj in qs_taken:
            pill_obj = get_object_or_404(Pill, id=obj.pill_id.id)
            if response_taken:
                response_taken += ", "
            ampm = '오전' if obj.when_to_take.strftime("%p") == "AM" else "오후"
            response_taken +=  ampm + obj.taken_time.strftime(" %I시 %M분") + '에 ' + pill_obj.name +  " " + str(obj.dose_taken_today) + "정" 
            
            dummy = datetime.date(1, 1, 1)
            when_to_take = datetime.datetime.combine(dummy, obj.when_to_take)
            taken_time = datetime.datetime.combine(dummy, obj.taken_time)
            diff_hours = (taken_time - when_to_take).total_seconds() / 3600
            
            if diff_hours > 2:
                if late_pills:
                    late_pills += ", "
                ampm = '오전' if obj.when_to_take.strftime("%p") == "AM" else "오후"
                late_pills += ampm+ obj.when_to_take.strftime(" %I시 %M분") + '에 예정된 ' + pill_obj.name + " " + str(obj.dose) + "정"     

        response_taken += "을 복용하셨습니다."

        if late_pills:
            response_taken += (late_pills + "을, 2시간 이상 늦게 복용하셨으니 주의 부탁드립니다.")

    response_total_status += response_taken

    response_not_taken = ""
    response_overdue = ""
    response_scheduled = ""
    if len(qs_overdue) > 0:        
        for obj in qs_overdue:
            pill_obj = get_object_or_404(Pill, id=obj.pill_id.id)
            if response_overdue:
                response_overdue += ", "
            ampm = '오전' if obj.when_to_take.strftime("%p") == "AM" else "오후"
            response_overdue += ampm + obj.when_to_take.strftime(" %I시 %M분") + "에 예정된 " + pill_obj.name + " " + str(obj.dose) + "정"
        
        response_overdue += "을 아직 복용하지 않았으니, 확인 부탁드립니다."

    if len(qs_scheduled) > 0:
        for obj in qs_scheduled:
            pill_obj = get_object_or_404(Pill, id=obj.pill_id.id)
            if response_scheduled:
                response_scheduled += ", "
            ampm = '오전' if obj.when_to_take.strftime("%p") == "AM" else "오후"
            response_scheduled += ampm+ obj.when_to_take.strftime(" %I시 %M분") + "에 " + pill_obj.name + " " + str(obj.dose) + "정"
        response_scheduled += "을 복용할 예정입니다."

    if len(qs_overdue) == 0 and len(qs_scheduled) == 0:
        response_not_taken = "오늘 예정된 모든 약을 복용하셨습니다."
    else:
        response_not_taken = response_overdue + response_scheduled
    
    response_total_status += response_not_taken

    context['output']['response_total_status'] = response_total_status
    return Response(context)


@api_view(['GET'])
def health(request):
    return Response("OK")