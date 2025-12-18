"""Student view module"""
import os
import statistics
import logging
import structlog
import time
import psutil
from prometheus_client import Counter, Histogram

import requests
from django.db.models import Count, Q, Case, When
from django.db.models.fields import IntegerField
from django.http import HttpResponseServerError
from django.utils.decorators import method_decorator
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from LearningAPI.decorators import is_instructor
from LearningAPI.models import Tag
from LearningAPI.models.coursework import Capstone, StudentProject, Book, Project, CohortCourse
from LearningAPI.models.people import (Cohort, StudentNote, NssUser, StudentAssessment,
                                       OneOnOneNote, StudentPersonality, Assessment,
                                       StudentAssessmentStatus, StudentTag)
from LearningAPI.models.skill import (CoreSkillRecord, LearningRecord,
                                      LearningRecordEntry)
from .personality import myers_briggs_persona


team_assignment_duration = Histogram(
    'learning_api_team_assignment_seconds',
    'Time to assign students to teams',
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

team_assignment_total = Counter(
    'learning_api_team_assignment_total',
    'Total team assignments',
    ['status']  # 'success' or 'error'
)
student_project_move_duration = Histogram(
    'learning_api_student_project_move_seconds',
    'Time to move student to different project',
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

student_project_move_total = Counter(
    'learning_api_student_project_move_total',
    'Total student project moves',
    ['status']  # 'success' or 'error'
)

# ORM Query Resource Monitoring Metrics
orm_query_cpu_usage = Histogram(
    'learning_api_orm_query_cpu_percent',
    'CPU usage percentage during ORM queries',
    ['query_type'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0)
)

orm_query_memory_usage = Histogram(
    'learning_api_orm_query_memory_mb',
    'Memory usage in MB during ORM queries',
    ['query_type'],
    buckets=(1, 5, 10, 25, 50, 100, 250, 500)
)

orm_query_total = Counter(
    'learning_api_orm_query_total',
    'Total ORM queries executed',
    ['query_type', 'status']
)

logger = structlog.get_logger(__name__)


class ORMQueryMonitor:
    """Context manager to monitor CPU and memory usage for ORM queries"""
    
    def __init__(self, query_type: str):
        self.query_type = query_type
        self.process = psutil.Process(os.getpid())
        self.start_cpu = None
        self.start_memory = None
        
    def __enter__(self):
        # Record starting metrics
        self.start_cpu = self.process.cpu_percent()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # Convert to MB
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Calculate resource usage
        end_cpu = self.process.cpu_percent()
        end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        cpu_used = end_cpu - self.start_cpu
        memory_used = end_memory - self.start_memory
        
        # Record metrics
        orm_query_cpu_usage.labels(query_type=self.query_type).observe(cpu_used)
        orm_query_memory_usage.labels(query_type=self.query_type).observe(abs(memory_used))
        
        # Record success/failure
        status = 'error' if exc_type else 'success'
        orm_query_total.labels(query_type=self.query_type, status=status).inc()


class StudentPagination(PageNumberPagination):
    """Pagination for student resource"""
    page_size = 40
    page_size_query_param = 'page_size'
    max_page_size = 80


class StudentViewSet(ModelViewSet):
    """Student viewset"""

    pagination_class = StudentPagination

    def create(self, request):
        """Handle POST operations"""
        return Response(None, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def retrieve(self, request, pk=None):
        """Handle GET requests for single item

        Returns:
            Response -- JSON serialized instance
        """
        logger = logging.getLogger("LearningPlatform")

        try:
            try:
                student = NssUser.objects.get(pk=pk)

            except ValueError:
                student = NssUser.objects.get(slack_handle=pk)

            try:
                personality = StudentPersonality.objects.get(student=student)
            except StudentPersonality.DoesNotExist:
                personality = StudentPersonality()
                personality.briggs_myers_type = ""
                personality.bfi_extraversion = 0
                personality.bfi_agreeableness = 0
                personality.bfi_conscientiousness = 0
                personality.bfi_neuroticism = 0
                personality.bfi_openness = 0
                personality.student = student
                personality.save()
            except Exception as ex:
                logger.exception(getattr(ex, 'message', repr(ex)))

            if request.auth.user == student.user or request.auth.user.is_staff:
                serializer = StudentSerializer(
                    student, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"message": "You are not authorized to view this student profile."},
                    status=status.HTTP_401_UNAUTHORIZED)

        except NssUser.DoesNotExist:
            return Response(
                {"message": "That student does not exist."},
                status=status.HTTP_404_NOT_FOUND)

        except Exception as ex:
            logger.exception(getattr(ex, 'message', repr(ex)))
            return HttpResponseServerError(ex)

    def update(self, request, pk=None):
        """Handle PUT requests

        Returns:
            Response -- Empty body with 204 status code
        """
        try:
            student = NssUser.objects.get(pk=pk)

            if request.auth.user == student.user or request.auth.user.is_staff:
                if "slack_handle" in request.data:
                    student.slack_handle = request.data["slack_handle"]
                if "gitub_handle" in request.data:
                    student.gitub_handle = request.data["gitub_handle"]

                student.save()

                return Response(None, status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(None, status=status.HTTP_401_UNAUTHORIZED)

        except NssUser.DoesNotExist:
            return Response(None, status=status.HTTP_404_NOT_FOUND)

        except Exception as ex:
            return HttpResponseServerError(ex)

    @method_decorator(is_instructor())
    def destroy(self, request, pk=None):
        """Handle DELETE requests for a single student

        Returns:
            Response -- 200, 404, or 500 status code
        """
        try:
            student = NssUser.objects.get(pk=pk)
            student.delete()

            return Response(None, status=status.HTTP_204_NO_CONTENT)

        except NssUser.DoesNotExist as ex:
            return Response({'message': ex.args[0]}, status=status.HTTP_404_NOT_FOUND)

        except Exception as ex:
            return Response({'message': ex.args[0]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request):
        """Handle GET requests for all students

        Returns:
            Response -- JSON serialized array with query timings
        """
        start_list_method = time.time()
        student_status = self.request.query_params.get('status', None)
        cohort = self.request.query_params.get('cohort', None)
        search_terms = self.request.query_params.get('q', None)

        students = NssUser.objects.none() # Initialize an empty queryset

        if student_status == "unassigned":
            start_unassigned_query = time.time()
            with ORMQueryMonitor('nssuser_unassigned'):
                students = NssUser.objects.\
                    annotate(cohort_count=Count('assigned_cohorts')).\
                    filter(user__is_staff=False,
                           user__is_active=True, cohort_count=0)
            duration_unassigned_query = time.time() - start_unassigned_query
            logger.debug(f"list_method: NssUser unassigned query took {duration_unassigned_query:.4f} seconds")
        else:
            start_initial_query = time.time()
            with ORMQueryMonitor('nssuser_initial_filter'):
                students = NssUser.objects.filter(
                    user__is_active=True, user__is_staff=False)
            duration_initial_query = time.time() - start_initial_query
            logger.debug(f"list_method: NssUser initial query took {duration_initial_query:.4f} seconds")

        # Define `serializer_data` to ensure it's always available for pagination
        serializer_data = []

        if search_terms is not None:
            start_search_query = time.time()
            with ORMQueryMonitor('nssuser_search_filter'):
                for letter in list(search_terms):
                    students = students.filter(
                        Q(user__first_name__icontains=letter)
                        | Q(user__last_name__icontains=letter)
                    )
            duration_search_query = time.time() - start_search_query
            logger.debug(f"list_method: NssUser search query took {duration_search_query:.4f} seconds")

            start_single_student_serializer_data = time.time()
            serializer_data = SingleStudent(students, many=True).data
            duration_single_student_serializer_data = time.time() - start_single_student_serializer_data
            logger.debug(f"list_method: SingleStudent serializer.data for search took {duration_single_student_serializer_data:.4f} seconds")
            
            return Response(serializer_data, status=status.HTTP_200_OK)

        if cohort is not None:
            start_cohort_filter_get = time.time()
            with ORMQueryMonitor('cohort_get'):
                cohort_filter = Cohort.objects.get(pk=cohort)
            duration_cohort_filter_get = time.time() - start_cohort_filter_get
            logger.debug(f"list_method: Cohort.objects.get took {duration_cohort_filter_get:.4f} seconds")

            start_cohort_students_filter = time.time()
            with ORMQueryMonitor('nssuser_cohort_filter'):
                students = students.filter(assigned_cohorts__cohort=cohort_filter)
            duration_cohort_students_filter = time.time() - start_cohort_students_filter
            logger.debug(f"list_method: NssUser cohort filter took {duration_cohort_students_filter:.4f} seconds")

            # This loop can lead to N+1 queries. Consider prefetching or select_related if performance is an issue.
            for student in students:
                start_personality_get_or_create = time.time()
                try:
                    with ORMQueryMonitor('student_personality_get'):
                        personality = StudentPersonality.objects.get(student=student)
                    logger.debug(f"list_method: StudentPersonality.objects.get for student {student.id} took {time.time() - start_personality_get_or_create:.4f} seconds")
                except StudentPersonality.DoesNotExist:
                    with ORMQueryMonitor('student_personality_create'):
                        personality = StudentPersonality()
                        personality.briggs_myers_type = ""
                        personality.bfi_extraversion = 0
                        personality.bfi_agreeableness = 0
                        personality.bfi_conscientiousness = 0
                        personality.bfi_neuroticism = 0
                        personality.bfi_openness = 0
                        personality.student = student
                        personality.save()
                    logger.debug(f"list_method: StudentPersonality.objects.create for student {student.id} took {time.time() - start_personality_get_or_create:.4f} seconds")

            start_micro_students_serializer_data = time.time()
            serializer_data = MicroStudents(students, many=True).data
            duration_micro_students_serializer_data = time.time() - start_micro_students_serializer_data
            logger.debug(f"list_method: MicroStudents serializer.data for cohort took {duration_micro_students_serializer_data:.4f} seconds")
            
            # Use the data directly for pagination
            page = self.paginate_queryset(serializer_data)
            paginated_response = self.get_paginated_response(page)

            end_list_method = time.time()
            total_list_method_duration = end_list_method - start_list_method
            logger.info(f"list_method: Total execution of list method took {total_list_method_duration:.4f} seconds")
            return paginated_response

        # If no search terms or cohort filter, proceed with initial serializer
        start_single_student_serializer_data_default = time.time()
        serializer_data = SingleStudent(students, many=True).data # Access .data here to trigger serialization and query execution
        duration_single_student_serializer_data_default = time.time() - start_single_student_serializer_data_default
        logger.debug(f"list_method: SingleStudent serializer.data (default) took {duration_single_student_serializer_data_default:.4f} seconds")

        page = self.paginate_queryset(serializer_data)
        paginated_response = self.get_paginated_response(page)

        end_list_method = time.time()
        total_list_method_duration = end_list_method - start_list_method
        logger.info(f"list_method: Total execution of list method took {total_list_method_duration:.4f} seconds")
        return paginated_response

    @method_decorator(is_instructor())
    @action(methods=['post', 'put'], detail=True)
    def assess(self, request, pk):
        """POST when a student starts working on book assessment. PUT to change status."""

        if request.method == "PUT":
            student = NssUser.objects.get(pk=pk)
            assessment_status = StudentAssessmentStatus.objects.get(
                pk=request.data['statusId'])
            latest_assessment = StudentAssessment.objects.filter(
                student=student).last()

            if latest_assessment is not None:
                latest_assessment.status = assessment_status
                latest_assessment.save()

                try:
                    if latest_assessment.status.status == 'Reviewed and Complete':
                        headers = {
                            "Content-Type": "application/x-www-form-urlencoded"
                        }
                        channel_payload = {
                            "text": request.data.get(
                                "text",
                                f':fox-yay-woo-hoo: Self-Assessment Review Complete\n\n\n:white_check_mark: Your coaching team just marked {latest_assessment.assessment.name} as completed.\n\nVisit https://learning.nss.team to view your messages.'),
                            "token": os.getenv("SLACK_BOT_TOKEN"),
                            "channel": latest_assessment.student.slack_handle
                        }

                        requests.post(
                            "https://slack.com/api/chat.postMessage",
                            data=channel_payload,
                            headers=headers,
                            timeout=10
                        )
                except Exception:
                    return Response({'message': 'Updated, but no Slack message sent'}, status=status.HTTP_204_NO_CONTENT)

                return Response(None, status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({'message': 'Students has no assessments assigned'}, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == "POST":
            try:
                try:
                    assessment = Assessment.objects.get(book__id=int(request.data['bookId']))
                except Assessment.DoesNotExist:
                    return Response({'message': 'There is no assessment for this book.'}, status=status.HTTP_404_NOT_FOUND)


                student_assessment = StudentAssessment()
                student_assessment.student = NssUser.objects.get(pk=pk)
                student_assessment.instructor = NssUser.objects.get(
                    user=request.auth.user)
                student_assessment.status = StudentAssessmentStatus.objects.get(
                    status="In Progress")
                student_assessment.assessment = assessment
                student_assessment.save()
            except Exception as ex:
                return Response({'message': ex.args[0]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({'message': 'Success'}, status=status.HTTP_201_CREATED)

    @method_decorator(is_instructor())
    @action(methods=['post'], detail=True)
    def project(self, request, pk):
        """Add to the list of projects being worked on by student"""
        
        if request.method == "POST":
            start_time = time.time()
            
            try:
                student_project = StudentProject()
                student_project.student = NssUser.objects.get(pk=pk)
                student_project.project = Project.objects.get(
                    pk=int(request.data['projectId']))
                student_project.save()
                
                # Record metrics
                duration = time.time() - start_time
                student_project_move_duration.observe(duration)
                student_project_move_total.labels(status='success').inc()
                
                logger.info(
                    "Student moved successfully",
                    student_id=student_project.student.id, 
                    project=student_project.project.id, 
                    moved_by=request.auth.user.username if request.auth.user.is_authenticated else 'anonymous',
                )
                return Response({'message': 'Success'}, status=status.HTTP_201_CREATED)
                
            except Exception as ex:
                # Record failure
                duration = time.time() - start_time
                student_project_move_duration.observe(duration)
                student_project_move_total.labels(status='error').inc()
                
                logger.error(
                    "Moving student failed",
                    message=ex.args[0],
                )
                return Response({'message': ex.args[0]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(is_instructor())
    @action(methods=['post'], detail=False)
    def teams(self, request):
        """Add/remove student tag for teams"""
        
        if request.method == "POST":
            start_time = time.time()
            combos = request.data.get('combos', None)
            
            for combo in combos:
                try:
                    student = NssUser.objects.get(pk=combo['student'])
                    
                    try:
                        tag = Tag.objects.get(name=combo['team'])
                    except Tag.DoesNotExist:
                        tag = Tag.objects.create(name=combo['team'])
                    
                    try:
                        StudentTag.objects.create(student=student, tag=tag)
                        team_assignment_total.labels(status='success').inc()
                        
                        logger.info(
                            "Team updated successfully",
                            tag=tag.name, 
                            moved_by=request.auth.user.username if request.auth.user.is_authenticated else 'anonymous',
                        )
                    
                    except Exception as ex:
                        team_assignment_total.labels(status='error').inc()
                        
                        logger.error(
                            "Updating team failed",
                            message=ex.args[0],
                        )
                
                except NssUser.DoesNotExist:
                    team_assignment_total.labels(status='error').inc()
            
            # Record total duration for batch
            duration = time.time() - start_time
            team_assignment_duration.observe(duration)
            
            return Response(None, status=status.HTTP_201_CREATED)

    @method_decorator(is_instructor())
    @action(methods=['post'], detail=True)
    def note(self, request, pk):
        """Add note for student"""

        if request.method == "POST":
            try:
                instructor_note = StudentNote()
                instructor_note.coach = NssUser.objects.get(
                    user=request.auth.user)
                instructor_note.student = NssUser.objects.get(pk=pk)
                instructor_note.status = request.data["note"]
                instructor_note.save()

                response = {
                    "id": instructor_note.id,
                    "status": instructor_note.status
                }

            except NssUser.DoesNotExist as ex:
                return Response({'message': ex.args[0]}, status=status.HTTP_404_NOT_FOUND)

            except Exception as ex:
                return HttpResponseServerError(ex)

            return Response(response, status=status.HTTP_201_CREATED)

        return Response({'message': 'Unsupported HTTP method'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @method_decorator(is_instructor())
    @action(methods=['post'], detail=True)
    def feedback(self, request, pk):
        """Add feedback from 1:1 session"""

        if request.method == "POST":
            try:
                student = NssUser.objects.get(pk=pk)
                note = OneOnOneNote()
                note.coach = NssUser.objects.get(user=request.auth.user)
                note.student = student
                note.notes = request.data["notes"]
                note.save()

                # Send message to student
                try:
                    headers = {
                        "Content-Type": "application/x-www-form-urlencoded"
                    }
                    channel_payload = {
                        "text": request.data.get("text", "You just received feedback from one of your coaches.\n\nVisit https://learning.nss.team to view your messages."),
                        "token": os.getenv("SLACK_BOT_TOKEN"),
                        "channel": student.slack_handle
                    }

                    requests.post(
                        "https://slack.com/api/chat.postMessage",
                        data=channel_payload,
                        headers=headers
                    )
                except Exception:
                    pass

            except NssUser.DoesNotExist as ex:
                return Response({'message': ex.args[0]}, status=status.HTTP_404_NOT_FOUND)

            except Exception as ex:
                return HttpResponseServerError(ex)

            return Response({'message': 'Student note created'}, status=status.HTTP_201_CREATED)

        return Response({'message': 'Unsupported HTTP method'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


def student_score(obj):
    """Return total learning score"""
    start_student_score = time.time()

    # First get the total of the student's technical objectives
    total = 0
    start_learning_record_query = time.time()
    with ORMQueryMonitor('learning_record_filter'):
        scores = LearningRecord.objects.\
            filter(student=obj, achieved=True).\
            order_by("-id")
    duration_learning_record_query = time.time() - start_learning_record_query
    logger.debug(f"student_score: LearningRecord query took {duration_learning_record_query:.4f} seconds")

    for score in scores:
        total += score.weight.weight

    # Get the average of the core skills' levels and adjust the
    # technical score positively by the percent
    start_core_skill_record_query = time.time()
    with ORMQueryMonitor('core_skill_record_filter'):
        core_skill_records = CoreSkillRecord.objects.filter(
            student=obj).order_by("pk")
    duration_core_skill_record_query = time.time() - start_core_skill_record_query
    logger.debug(f"student_score: CoreSkillRecord query took {duration_core_skill_record_query:.4f} seconds")
    scores = [record.level for record in core_skill_records]

    try:
        # Hannah and I did this on a Monday morning, so it may be the wrong
        # approach, but it's a step in the right direction
        mean = statistics.mean(scores)
        total = round(total * (1 + (mean / 10)))

    except statistics.StatisticsError:
        pass

    end_student_score = time.time()
    total_student_score_duration = end_student_score - start_student_score
    logger.debug(f"student_score: Total execution of student_score function took {total_student_score_duration:.4f} seconds")
    return total


class StudentNoteSerializer(serializers.ModelSerializer):
    """JSON serializer for student notes"""

    class Meta:
        model = OneOnOneNote
        fields = ['id', 'notes', 'session_date', 'author']


class InstructorNoteSerializer(serializers.ModelSerializer):
    """JSON serializer for student notes"""

    class Meta:
        model = StudentNote
        fields = ['id', 'note', 'created_on', 'author']


class LearningRecordEntrySerializer(serializers.ModelSerializer):
    """JSON serializer"""
    instructor = serializers.SerializerMethodField()

    def get_instructor(self, obj):
        return f'{obj.instructor.user.first_name} {obj.instructor.user.last_name}'

    class Meta:
        model = LearningRecordEntry
        fields = ('id', 'note', 'recorded_on', 'instructor')


class LearningRecordSerializer(serializers.ModelSerializer):
    """JSON serializer"""
    entries = LearningRecordEntrySerializer(many=True)
    objective = serializers.SerializerMethodField()

    def get_objective(self, obj):
        return obj.weight.label

    class Meta:
        model = LearningRecord
        fields = ('id', 'objective', 'achieved', 'entries', )


class PersonalitySerializer(serializers.ModelSerializer):
    """Serializer for a student's personality info"""
    briggs_myers_type = serializers.SerializerMethodField()

    def get_briggs_myers_type(self, obj):
        if obj.briggs_myers_type != "":
            return {
                "code": obj.briggs_myers_type,
                "description": myers_briggs_persona(obj.briggs_myers_type)
            }
        else:
            return {}

    class Meta:
        model = StudentPersonality
        fields = (
            'briggs_myers_type', 'bfi_extraversion',
            'bfi_agreeableness', 'bfi_conscientiousness',
            'bfi_neuroticism', 'bfi_openness',
        )


class StudentSerializer(serializers.ModelSerializer):
    """JSON serializer"""
    feedback = StudentNoteSerializer(many=True)
    notes = InstructorNoteSerializer(many=True)
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    github = serializers.SerializerMethodField()
    records = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    core_skill_records = serializers.SerializerMethodField()
    personality = PersonalitySerializer(many=False)

    def get_score(self, obj):
        start_get_score = time.time()
        score = student_score(obj)
        duration_get_score = time.time() - start_get_score
        logger.debug(f"StudentSerializer: get_score took {duration_get_score:.4f} seconds")
        return score

    def get_records(self, obj):
        start_get_records = time.time()
        with ORMQueryMonitor('learning_record_serializer'):
            records = LearningRecord.objects.filter(
                student=obj).order_by("achieved")
        duration_get_records = time.time() - start_get_records
        logger.debug(f"StudentSerializer: LearningRecord filter in get_records took {duration_get_records:.4f} seconds")
        
        start_serializer = time.time()
        serialized_data = LearningRecordSerializer(records, many=True).data
        duration_serializer = time.time() - start_serializer
        logger.debug(f"StudentSerializer: LearningRecordSerializer in get_records took {duration_serializer:.4f} seconds")
        return serialized_data

    def get_core_skill_records(self, obj):
        start_get_core_skill_records = time.time()
        with ORMQueryMonitor('core_skill_record_serializer'):
            records = CoreSkillRecord.objects.filter(student=obj).order_by("pk")
        duration_get_core_skill_records = time.time() - start_get_core_skill_records
        logger.debug(f"StudentSerializer: CoreSkillRecord filter in get_core_skill_records took {duration_get_core_skill_records:.4f} seconds")

        start_serializer = time.time()
        serialized_data = CoreSkillRecordSerializer(records, many=True).data
        duration_serializer = time.time() - start_serializer
        logger.debug(f"StudentSerializer: CoreSkillRecordSerializer in get_core_skill_records took {duration_serializer:.4f} seconds")
        return serialized_data

    def get_github(self, obj):
        start_get_github = time.time()
        with ORMQueryMonitor('socialaccount_get'):
            github = obj.user.socialaccount_set.get(user=obj.user)
        duration_get_github = time.time() - start_get_github
        logger.debug(f"StudentSerializer: socialaccount_set.get in get_github took {duration_get_github:.4f} seconds")
        return github.extra_data["login"]

    def get_name(self, obj):
        return f'{obj.user.first_name} {obj.user.last_name}'

    def get_email(self, obj):
        return obj.user.email

    class Meta:
        model = NssUser
        fields = ('id', 'name', 'email', 'github', 'score', 'core_skill_records',
                  'cohorts', 'feedback', 'records', 'notes', 'personality',
                  'capstones', 'current_cohort' )


class StudentTagSerializer(serializers.ModelSerializer):
    """JSON serializer"""
    class Meta:
        model = StudentTag
        fields = ('id', 'tag',)
        depth = 1


class CoreSkillRecordSerializer(serializers.ModelSerializer):
    """Serializer for Core Skill Record"""

    class Meta:
        model = CoreSkillRecord
        fields = ('id', 'skill', 'level', )
        depth = 1


class MicroStudents(serializers.ModelSerializer):
    """JSON serializer"""
    tags = StudentTagSerializer(many=True)
    name = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    proposals = serializers.SerializerMethodField()
    book = serializers.SerializerMethodField()
    assessment_status = serializers.SerializerMethodField()
    github = serializers.SerializerMethodField()
    archetype = serializers.SerializerMethodField()

    def get_github(self, obj):
        start_get_github = time.time()
        with ORMQueryMonitor('socialaccount_get_micro'):
            github = obj.user.socialaccount_set.get(user=obj.user)
        duration_get_github = time.time() - start_get_github
        logger.debug(f"MicroStudents: socialaccount_set.get in get_github took {duration_get_github:.4f} seconds")
        return github.extra_data["login"]

    def get_assessment_status(self, obj):
        start_get_assessment_status = time.time()
        start_student_project_filter = time.time()
        with ORMQueryMonitor('student_project_filter'):
            student_project = StudentProject.objects.filter(student=obj).last()
        duration_student_project_filter = time.time() - start_student_project_filter
        logger.debug(f"MicroStudents: StudentProject filter in get_assessment_status took {duration_student_project_filter:.4f} seconds")

        if student_project is not None:
            book = student_project.project.book

            # Not assigned book assessment yet
            assessment_status = 0

            try:
                start_student_assessment_query = time.time()
                with ORMQueryMonitor('student_assessment_annotate'):
                    student_assessment = StudentAssessment.objects.annotate(assessment_status=Case(
                            When(status__status="In Progress", then=1),
                            When(status__status="Ready for Review", then=2),
                            When(status__status="Reviewed and Incomplete", then=3),
                            When(status__status="Reviewed and Complete", then=4),
                            default=0,
                            output_field=IntegerField()
                        ))\
                        .get(assessment__book=book, student=obj)
                duration_student_assessment_query = time.time() - start_student_assessment_query
                logger.debug(f"MicroStudents: StudentAssessment query in get_assessment_status took {duration_student_assessment_query:.4f} seconds")

                assessment_status = student_assessment.assessment_status
            except StudentAssessment.DoesNotExist:
                assessment_status = 0
            
            end_get_assessment_status = time.time()
            total_get_assessment_status_duration = end_get_assessment_status - start_get_assessment_status
            logger.debug(f"MicroStudents: Total get_assessment_status took {total_get_assessment_status_duration:.4f} seconds")
            return assessment_status
        else:
            end_get_assessment_status = time.time()
            total_get_assessment_status_duration = end_get_assessment_status - start_get_assessment_status
            logger.debug(f"MicroStudents: Total get_assessment_status (no student project) took {total_get_assessment_status_duration:.4f} seconds")
            return 0

    def get_book(self, obj):
        start_get_book = time.time()
        start_student_project_filter = time.time()
        with ORMQueryMonitor('student_project_filter_book'):
            student_project = StudentProject.objects.filter(student=obj).last()
        duration_student_project_filter = time.time() - start_student_project_filter
        logger.debug(f"MicroStudents: StudentProject filter in get_book took {duration_student_project_filter:.4f} seconds")

        if student_project is None:
            start_cohort_course_get = time.time()
            with ORMQueryMonitor('cohort_course_get'):
                cohort_course = CohortCourse.objects.get(cohort__id=obj.cohorts[0]['id'], index=0)
            duration_cohort_course_get = time.time() - start_cohort_course_get
            logger.debug(f"MicroStudents: CohortCourse get in get_book took {duration_cohort_course_get:.4f} seconds")

            start_project_get = time.time()
            with ORMQueryMonitor('project_get'):
                project = Project.objects.get(book__course=cohort_course.course, book__index=0, index=0)
            duration_project_get = time.time() - start_project_get
            logger.debug(f"MicroStudents: Project get in get_book took {duration_project_get:.4f} seconds")

            return {
                "id": project.book.id,
                "name": project.book.name,
                "project": project.name
            }

        book_data = {}
        if student_project is None:
            start_cohort_course_get = time.time()
            with ORMQueryMonitor('cohort_course_get_duplicate'):
                cohort_course = CohortCourse.objects.get(cohort__id=obj.cohorts[0]['id'], index=0)
            duration_cohort_course_get = time.time() - start_cohort_course_get
            logger.debug(f"MicroStudents: CohortCourse get in get_book took {duration_cohort_course_get:.4f} seconds")

            start_project_get = time.time()
            with ORMQueryMonitor('project_get_duplicate'):
                project = Project.objects.get(book__course=cohort_course.course, book__index=0, index=0)
            duration_project_get = time.time() - start_project_get
            logger.debug(f"MicroStudents: Project get in get_book took {duration_project_get:.4f} seconds")

            book_data = {
                "id": project.book.id,
                "name": project.book.name,
                "project": project.name
            }
        else:
            book_data = {
                "id": student_project.project.book.id,
                "name": student_project.project.book.name,
                "project": student_project.project.name
            }
        
        end_get_book = time.time()
        total_get_book_duration = end_get_book - start_get_book
        logger.debug(f"MicroStudents: Total get_book took {total_get_book_duration:.4f} seconds")
        return book_data

    def get_proposals(self, obj):
        start_get_proposals = time.time()
        # Three stages - "submitted", "reviewed", "approved"
        start_capstone_query = time.time()
        with ORMQueryMonitor('capstone_annotate'):
            proposals = Capstone.objects.filter(student=obj).annotate(
                status_count=Count("statuses"),
                approved=Count(
                    'statuses',
                    filter=Q(statuses__status__status="Approved")
                ),
                mvp=Count(
                    'statuses',
                    filter=Q(statuses__status__status="MVP")
                )
            ).order_by("pk")
        duration_capstone_query = time.time() - start_capstone_query
        logger.debug(f"MicroStudents: Capstone query in get_proposals took {duration_capstone_query:.4f} seconds")

        proposal_statuses = []

        for proposal in proposals:
            proposal_status = ""

            if proposal.status_count == 0:
                proposal_status = "submitted"
            elif proposal.status_count > 0 and proposal.mvp == 1:
                proposal_status = "mvp"
            elif proposal.status_count > 0 and proposal.approved == 0:
                proposal_status = "reviewed"
            elif proposal.status_count > 0 and proposal.approved == 1:
                proposal_status = "approved"

            proposal_statuses.append({
                "id": proposal.id,
                "course": proposal.course.id,
                "status": proposal_status
            })

        end_get_proposals = time.time()
        total_get_proposals_duration = end_get_proposals - start_get_proposals
        logger.debug(f"MicroStudents: Total get_proposals took {total_get_proposals_duration:.4f} seconds")
        return proposal_statuses

    def get_score(self, obj):
        start_get_score = time.time()
        score = student_score(obj)
        duration_get_score = time.time() - start_get_score
        logger.debug(f"MicroStudents: get_score took {duration_get_score:.4f} seconds")
        return score

    def get_archetype(self, obj):
        if obj.personality.briggs_myers_type != '':
            return myers_briggs_persona(obj.personality.briggs_myers_type)["type"]

        return ""

    def get_name(self, obj):
        return f'{obj.user.first_name} {obj.user.last_name}'

    class Meta:
        model = NssUser
        fields = ('id', 'name', 'score', 'tags',
                  'proposals', 'book',
                  'assessment_status',
                  'github', 'cohorts',
                  'archetype',)


class SingleStudent(serializers.ModelSerializer):
    """JSON serializer"""
    feedback = StudentNoteSerializer(many=True)
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    github = serializers.SerializerMethodField()
    repos = serializers.SerializerMethodField()
    staff = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    date_joined = serializers.SerializerMethodField()

    def get_date_joined(self, obj):
        return obj.user.date_joined

    def get_score(self, obj):
        start_get_score = time.time()
        score = student_score(obj)
        duration_get_score = time.time() - start_get_score
        logger.debug(f"SingleStudent: get_score took {duration_get_score:.4f} seconds")
        return score

    def get_staff(self, obj):
        return False

    def get_github(self, obj):
        start_get_github = time.time()
        with ORMQueryMonitor('socialaccount_get_single'):
            github = obj.user.socialaccount_set.get(user=obj.user)
        duration_get_github = time.time() - start_get_github
        logger.debug(f"SingleStudent: socialaccount_set.get in get_github took {duration_get_github:.4f} seconds")
        return github.extra_data["login"]

    def get_repos(self, obj):
        start_get_repos = time.time()
        with ORMQueryMonitor('socialaccount_get_repos'):
            github = obj.user.socialaccount_set.get(user=obj.user)
        duration_get_repos = time.time() - start_get_repos
        logger.debug(f"SingleStudent: socialaccount_set.get in get_repos took {duration_get_repos:.4f} seconds")
        return github.extra_data["repos_url"]

    def get_name(self, obj):
        return f'{obj.user.first_name} {obj.user.last_name}'

    def get_email(self, obj):
        return obj.user.email

    class Meta:
        model = NssUser
        fields = ('id', 'name', 'email', 'github', 'staff', 'slack_handle',
                  'cohorts', 'feedback', 'repos', 'score', 'date_joined',
                  'current_cohort')
