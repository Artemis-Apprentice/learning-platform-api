"""View module for handling requests about park areas"""
import os
import structlog 
import requests
from rest_framework import status
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from LearningAPI.models.people import NssUser

logger = structlog.get_logger("LearningAPI") 
class SlackChannel(ViewSet):
    """For creating Slack channels"""

    def create(self, request):
        """Handle POST requests to create team Slack channels"""

        # Create the Slack channel
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        channel_payload = {
            "name": request.data["name"],
            "token": os.getenv("SLACK_BOT_TOKEN")
        }

        student_slack_ids = set()
        for student_id in request.data["students"]:
            student = NssUser.objects.get(pk=student_id)
            if student.slack_handle is not None:
                student_slack_ids.add(student.slack_handle)

        res = requests.post("https://slack.com/api/conversations.create", timeout=10, data=channel_payload, headers=headers)
        channel_res = res.json()
        
        logger.info(
            channel_name=request.data["name"],
            students=student_slack_ids
        )

        # Add students to Slack channel
        invitation_payload = {
            "channel": channel_res["channel"]["id"],
            "users": ",".join(list(student_slack_ids)),
            "token": os.getenv("SLACK_BOT_TOKEN")
        }

        res = requests.post("https://slack.com/api/conversations.invite", timeout=10, data=invitation_payload, headers=headers)
        students_res = res.json()
        
        if res.status_code == 200:
            logger.info(
                "slack_students_invited_successfully",
                channel_name=request.data["name"],
                channel_id=channel_res["channel"]["id"],
                student_count=len(student_slack_ids)
            )
        else:
            logger.warning(
                "Slack Student Invitation Failed",
                channel_name=request.data["name"],
                channel_id=channel_res["channel"]["id"],
                student_count=len(student_slack_ids),
                error=students_res.get("error")
            )

        combined_response = {
            "channel": channel_res,
            "invitations": students_res
        }

        return Response(combined_response, status=status.HTTP_201_CREATED)
