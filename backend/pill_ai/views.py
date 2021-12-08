from io import StringIO
from django.db.models.query import QuerySet
from rest_framework import viewsets
from rest_framework.decorators import api_view, parser_classes
from django.conf import settings
from rest_framework.response import Response
from django.core.files import File

from pharmasee.models import Pill

import os
import pandas as pd
import urllib.request
import threading
from PIL import Image
import warnings
warnings.filterwarnings('ignore')

def populate_pills(csv_url):
    print("Started creating pills")
    df = pd.read_csv(csv_url)
    df = df.dropna(axis=0)

    keys = ["name", "side_effect", "effect"]
    for idx, row in df.iterrows(): 
        result = urllib.request.urlretrieve(row.itemImage)
        byte_file = File(open(result[0], 'rb'))
        vals = [row.itemName, row.seQesitm.replace('<p>', '').replace('</p>', ''), row.efcyQesitm.replace('<p>', '').replace('</p>', '')]
        data_dict = dict(zip(keys, vals))
        obj = Pill(**data_dict)
        obj.image_dir.save(os.path.basename(row.itemImage), byte_file)
        obj.save()
    
    print("Pill Create Complete!")

from .serializers import DnnImageSerializer

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

class DnnImageView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file = request.FILES.get('image')

        data = {
            'input_image': file
        }

        file_ser = DnnImageSerializer(data=data)
        if file_ser.is_valid():
            file_ser.save()
            data = file_ser.data
            return Response(data, status=status.HTTP_201_CREATED)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)