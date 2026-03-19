from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from LearningAPI.models.coursework import PocJob
from LearningAPI.messaging.publisher import publish_poc_message
import logging

logger = logging.getLogger(__name__)

class PocJobViewSet(viewsets.ViewSet):
    """
    Simple POC endpoint to test async job creation.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='create')
    def create_job(self, request):
        """
        POST /api/poc-jobs/create/

        Body: {"test_data": "anything you want"}

        Returns: 202 Accepted with job_id
        """
        # Create job record
        job = PocJob.objects.create(
            created_by=request.user,
            status='PENDING',
            message_data=request.data
        )

        # Publish to RabbitMQ
        success = publish_poc_message(
            job_id=job.id,
            message_data={
                "data": {
                    "task_type": "github_issue_migration",
                    "source_repo": { "owner": "Artemis-Apprentice", "name": "issue_source" },
                    "target_repo": { "owner": "Artemis-Apprentice", "name": "target_a" },
                    "options": { "state": "open", "migrate_labels": True }
                }
            }
        )

        if not success:
            job.status = 'FAILED'
            job.result_data = {'error': 'Failed to publish message'}
            job.save()
            return Response(
                {'error': 'Failed to publish to RabbitMQ'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        logger.info(f"Created POC job {job.id}")

        return Response({
            'job_id': str(job.id),
            'status': job.status,
            'message': 'Job created and message published to RabbitMQ'
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['get'], url_path='status')
    def get_status(self, request, pk=None):
        """
        GET /api/poc-jobs/{job_id}/status/

        Returns current job status and results
        """
        try:
            job = PocJob.objects.get(pk=pk)
        except PocJob.DoesNotExist:
            return Response(
                {'error': 'Job not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'job_id': str(job.id),
            'status': job.status,
            'message_data': job.message_data,
            'result_data': job.result_data,
            'created_at': job.created_at,
            'updated_at': job.updated_at
        })
