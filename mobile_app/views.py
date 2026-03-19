from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *

class PondListView(APIView):
    def get(self, request,id):
        cluster =Cluster.objects.get(id=id)
        serializer = ClusterPondSerializer(cluster)
        return Response(serializer.data, status=status.HTTP_200_OK)

class Task_Of_PondDeviceListView(APIView):
    def get(self, request,device,taskcatagory):
        task=Task.objects.filter(device=device,taskcatagory=taskcatagory)
        serializer = Task_Of_PondDeviceSerializer(task, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

