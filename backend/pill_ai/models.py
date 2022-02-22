from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models
from django.db.models import Q
from django.shortcuts import get_object_or_404
from pharmasee.models import Reminder, TimestampedModel, Pill

import os
import sys
import datetime
import uuid
from PIL import Image
import numpy as np
import requests
import json
import cv2

color_dict={
    'blue_color' : (255, 0, 0),
    'green_color' : (0, 255, 0),
    'red_color' : (0, 0, 255),
    'white_color' : (255, 255, 255)
}

pill_dict = {
    '1.0': '가블리메트',
    '4.0': '게므론골드',
    '5.0': '네오반플라스'
}

def make_path(type, filename):
    ext = filename.split('.')[-1]
    d = datetime.datetime.now()
    filepath = d.strftime(f'pill_ai/{type}/%Y/%m/%d')
    suffix = d.strftime("%Y%m%d%H%M%S")
    filename = "%s_%s.%s"%(uuid.uuid4().hex, suffix, ext)
    return os.path.join(filepath, filename)

def file_upload_path_input(instance, filename):
    return make_path('input', filename)

def file_upload_path_output(instance, filename):
    return make_path('output', filename)

def file_upload_path_for_db(instance, filename):
    pass

class DnnImage(TimestampedModel):
    input_image = models.ImageField(upload_to=file_upload_path_input)
    output_image = models.ImageField(upload_to=file_upload_path_output, blank=True, null=True)
    correct = models.BooleanField(default=False)
    status_mesg = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        self.predict_pills()
        super(DnnImage ,self).save(*args, **kwargs)

    def predict_pills(self, *args, **kwargs):
        output_image, correct, status_mesg = predict(self.input_image)

        self.output_image = InMemoryUploadedFile(
            file=output_image,
            field_name='ImageField',
            name=self.input_image.name,
            content_type='image/jpeg',
            size=sys.getsizeof(output_image),
            charset=None
        )

        self.correct = correct
        self.status_mesg = status_mesg

def predict(img):
    img = Image.open(img)
    h, w = img.height, img.width
    img = img.convert('RGB').resize((512, 512))
    img = np.array(img)
    img = np.expand_dims(img, axis=0)
    
    data = json.dumps({
        "instances": img.tolist()
    })
    headers = {"content/type": "application/json"}

    response = requests.post('http://localhost:8501/v1/models/pills_model:predict', data=data, headers=headers)
    
    status_mesg = ""
    predictions = response.json()['predictions'][0]
    opencv_img = cv2.cvtColor(np.squeeze(img), cv2.COLOR_RGB2BGR)
    status_mesg = draw_label_for_single_image(opencv_img, predictions, status_mesg, 0.8)
    opencv_img = cv2.cvtColor(opencv_img, cv2.COLOR_BGR2RGB)
    
    img = np.array(opencv_img)
    img = Image.fromarray(img)
    img = img.resize((w, h))
    return (img_to_bytes(img), False, status_mesg) 

def img_to_bytes(img):
    output = BytesIO()
    img.save(output, format='JPEG', quality=100)
    output.seek(0)
    return output

def draw_label_for_single_image(img, output_dict, status_mesg, score_threshold=0.5):
    #인식을 위한 미니멈 Threshold
    MIN_SCORE_THRESHOLD=score_threshold

    #output_dict/detection_boxes : 검출한 박스들, 사진의 비율로 이루어져잇음 ( 0<x<1)
    #output_dict/detection_scores : 검출한 박스의 유사도 점수
    boxes=np.squeeze(output_dict['detection_boxes'])
    scores=np.squeeze(output_dict['detection_scores'])
    classes = np.array(output_dict['detection_classes'])

    bboxes = boxes[scores > MIN_SCORE_THRESHOLD]
    classes = classes[scores > MIN_SCORE_THRESHOLD] 
        
    #img 높이와 너비 저장
    img_height, img_width, img_c= img.shape


    box_list = {}

    for idx, box in enumerate(bboxes):
        pill_class = pill_dict.get(str(classes[idx]))
        if not pill_class:
            continue

        y_min, x_min, y_max, x_max = box
        if box_list.get(pill_class):
            box_list[pill_class].append([x_min*img_width, x_max*img_width, y_min*img_height, y_max*img_height])
        else:
            box_list[pill_class] = [[x_min*img_width, x_max*img_width, y_min*img_height, y_max*img_height]]

    ok_box_list = {}
    ng_box_list = {}

    # now = datetime.datetime(1, 1, 1, 9, 5, 0)
    now = datetime.datetime(1, 1, 1, 19, 40, 0)
    objs_to_save = []
    for pill_class, boxes in box_list.items():
        pill_obj = get_object_or_404(Pill, name=pill_class)
        # qs = Reminder.objects.filter(pill_id=pill_obj.id).filter(is_taken_today=False).filter(Q(when_to_take__gte=(now-datetime.timedelta(hours=3)).time()) | Q(when_to_take__lte=(now+datetime.timedelta(hours=3)).time()))
        qs = Reminder.objects.filter(pill_id=pill_obj.id).filter(is_taken_today=False)

        if len(qs) == 0:
            ng_box_list[pill_class] = boxes
            status_mesg += f"{pill_class} {len(boxes)}정을 빼주세요.\n"
        else:
            obj = None
            for obj_temp in qs:
                dummy = datetime.date(1, 1, 1)
                when_to = datetime.datetime.combine(dummy, obj_temp.when_to_take)
                diff_hours = abs((now - when_to).total_seconds() / 3600)
                if diff_hours > 3:
                    # print(obj_temp, "Not this one.")
                    continue
                else:
                    # print(obj_temp, "this one")
                    obj = obj_temp

            if not obj:
                ng_box_list[pill_class] = boxes
                status_mesg += f"{pill_class} {len(boxes)}정을 빼주세요.\n" 

            num_of_pills = len(boxes)

            if num_of_pills > int(obj.dose):
                status_mesg += f"{pill_class} {num_of_pills - int(obj.dose)}정을 빼주세요.\n"
                ng_box_list[pill_class] = boxes
            elif num_of_pills < int(obj.dose):
                status_mesg += f"{pill_class} {int(obj.dose) - num_of_pills}정을 추가해주세요.\n"
                ng_box_list[pill_class] = boxes
            else:
                ok_box_list[pill_class] = boxes
                objs_to_save.append(obj)

    print(ok_box_list)
    print(ng_box_list)
    
    # ng가 없으면 저장
    if not ng_box_list:
        for obj_to_save in objs_to_save:
            obj_to_save.is_taken_today = True
            obj_to_save.dose_taken_today = int(obj.dose)
            obj_to_save.taken_time = now.time()
            obj_to_save.save()
        status_mesg += "약을 모두 잘 챙기셨습니다!\n리마인더에 체크해드리겠습니다."

    #Cricle 그리는 방법
    for pill_class, boxes in ok_box_list.items():
        for x in boxes:
            cv2.circle(img,(int((x[0]+x[1])/2),int((x[2]+x[3])/2)), 50, color_dict['green_color'], 12)

    #x 그리는 방법
    for pill_class, boxes in ng_box_list.items():
        for x in boxes:
            cv2.line(img, (int(x[0]),int(x[3])), (int(x[1]),int(x[2])), color_dict['red_color'], 12)
            cv2.line(img, (int(x[0]),int(x[2])), (int(x[1]),int(x[3])), color_dict['red_color'], 12) 

    return status_mesg