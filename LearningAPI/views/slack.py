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
        try:
            res = requests.post("https://slack.com/api/conversations.create", timeout=10, data=channel_payload, headers=headers)
            channel_res = res.json()
            
            if channel_res['ok']:
                logger.info(
                    "slack_channel_created_successfully",
                    channel_name=request.data["name"],
                    students=student_slack_ids,
                    slack_response=channel_res
                )
            else:
                logger.error(
                    "slack_channel_creation_failed",
                    channel_name=request.data["name"],
                    slack_response=channel_res
                )
                return Response(channel_res, status=status.HTTP_502_BAD_GATEWAY)
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
        except Exception as ex:
            logger.error(
                "slack_channel_creation_failed",
                reason=str(ex),
                channel_name=request.data.get("name"),
                created_by=request.auth.user.username if request.auth.user.is_authenticated else 'anonymous',
                exc_info=True
            )
            return Response({"reason": ex.args[0]}, status=status.HTTP_400_BAD_REQUEST)
