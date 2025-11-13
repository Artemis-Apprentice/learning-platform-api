from django.http.response import HttpResponseServerError
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from LearningAPI.models.skill import CoreSkill, CoreSkillRecord, CoreSkillRecordEntry
from LearningAPI.models.people import NssUser
from prometheus_client import Counter, Histogram
import time
import structlog 

core_skill_update_duration = Histogram(
    'learning_api_core_skill_update_seconds',
    'Time to update core skill level',
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0)
)

core_skill_update_total = Counter(
    'learning_api_core_skill_update_total',
    'Total core skill updates',
    ['status']  # 'success' or 'error'
)

logger = structlog.get_logger("LearningAPI") 
class CoreSkillRecordViewSet(ModelViewSet):
    """
    A simple ViewSet for viewing and editing learning records.
    """
    queryset = CoreSkillRecord.objects.all()
    permission_classes = [IsAdminUser]

    def retrieve(self, request, pk=None):
        """Not supported"""

        return Response(None, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def list(self, request):
        """Not supported"""
        student_id = request.query_params.get('studentId', None)

        if student_id is not None:
            student = NssUser.objects.get(pk=student_id)
            records = CoreSkillRecord.objects.filter(student=student).order_by("skill__label")
            json_data = CoreSkillRecordSerializer(records, many=True).data
            return Response(json_data, status=status.HTTP_200_OK)

        return Response({'reason': 'Missing `studendId` query parameter.'}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request):
        """Handle POST operations

        Returns:
            Response -- JSON serialized instance
        """
        record = CoreSkillRecord()
        record.student = NssUser.objects.get(pk=request.data["student"])
        record.skill = CoreSkill.objects.get(pk=request.data["skill"])
        record.level = request.data["level"]

        try:
            record.save()
            entry = CoreSkillRecordEntry()
            entry.record = record
            entry.instructor = NssUser.objects.get(user=request.auth.user)
            note = request.data["note"]
            if note == "":
                entry.note = "Record initiated"
            else:
                entry.note = request.data["note"]

            entry.save()

            serializer = CoreSkillRecordSerializer(record)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as ex:
            return Response({"reason": ex.args[0]}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        """Handle PUT requests to update core skill level"""
        start_time = time.time()

        try:
            record = CoreSkillRecord.objects.get(pk=pk)
            
            if request.auth.user.is_staff:
                record.level = request.data["level"]
                record.save()
                
                # Record metrics
                duration = time.time() - start_time
                core_skill_update_duration.observe(duration)
                core_skill_update_total.labels(status='success').inc()
                
                logger.info(
                    "Skill level successfully updated",
                    record_level=record.level,
                    skill_id=request.data["skill_id"],
                    student_id=request.data["student_id"],
                )
                return Response(None, status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(None, status=status.HTTP_401_UNAUTHORIZED)

        except CoreSkillRecord.DoesNotExist:
            duration = time.time() - start_time
            core_skill_update_duration.observe(duration)
            core_skill_update_total.labels(status='error').inc()
            
            logger.error(
                f"Core skill record of {pk} could not be found",
            )
            return Response(None, status=status.HTTP_404_NOT_FOUND)

        except Exception as ex:
            duration = time.time() - start_time
            core_skill_update_duration.observe(duration)
            core_skill_update_total.labels(status='error').inc()
            
            logger.error(
                "Skill update failed",
                message=ex.args[0],
            )
            return HttpResponseServerError(ex)

    def delete(self, request, pk=None):
        """Handle PUT requests to update core skill level"""
        try:
            record = CoreSkillRecord.objects.get(pk=pk)

            if request.auth.user.is_staff:
                record.delete()

                return Response(None, status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(None, status=status.HTTP_401_UNAUTHORIZED)

        except CoreSkillRecord.DoesNotExist:
            return Response(None, status=status.HTTP_404_NOT_FOUND)

        except Exception as ex:
            return HttpResponseServerError(ex)

    @action(methods=['delete', 'post'], detail=False)
    def entries(self, request, entry_id=None):
        """ Manage learning record entries """

        if request.method == "POST":
            # Handle POST operations
            try:
                record = CoreSkillRecord.objects.get(pk=request.data["record"])
            except CoreSkillRecord.DoesNotExist:
                return Response({"reason": "Core skill record not found"}, status=status.HTTP_404_NOT_FOUND)

            try:
                entry = CoreSkillRecordEntry()
                entry.record = record
                entry.instructor = NssUser.objects.get(user=request.auth.user)
                entry.note = request.data["note"]
                entry.save()

                serializer = CoreSkillRecordSerializer(
                    record, context={'request': request})
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as ex:
                return Response({"reason": ex.args[0]}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "DELETE":

            try:
                entry = CoreSkillRecordEntry.objects.get(pk=entry_id)
                record_id = entry.record_id
                entry.delete()

                record_entries = CoreSkillRecordEntry.objects.filter(
                    record_id=record_id)
                any_left = len(record_entries)
                if not any_left:
                    record = CoreSkillRecord.objects.get(pk=record_id)
                    record.delete()

            except CoreSkillRecordEntry.DoesNotExist:
                return Response(None, status=status.HTTP_404_NOT_FOUND)

            return Response(None, status=status.HTTP_204_NO_CONTENT)


class CoreSkillRecordSerializer(serializers.ModelSerializer):
    """Serializer for Core Skill Record"""

    class Meta:
        model = CoreSkillRecord
        fields = ('id', 'skill', 'level',)
        depth = 1