#!/usr/bin/env python
"""
Simple RabbitMQ consumer for POC testing.
Runs outside Docker for easier debugging.
Connects directly to PostgreSQL - no Django dependency.
"""
import pika
import json
import time
import os
import psycopg2
import psycopg2.extras
from datetime import datetime
import urllib.request
import urllib.parse
from dotenv import load_dotenv


load_dotenv()


# ---------------------------------------------------------------------------
# Standalone settings — no Django imports, no shared settings module
# ---------------------------------------------------------------------------
GITHUB_SETTINGS = {
    'token': os.environ.get('GITHUB_API_TOKEN', ''),
    'api_base': 'https://api.github.com',
}

DB_SETTINGS = {
    'host':     os.environ.get('DB_HOST',     'localhost'),
    'port':     int(os.environ.get('DB_PORT', 6543)),
    'dbname':   os.environ.get('DB_NAME',     'learnopsdev'),
    'user':     os.environ.get('DB_USER',     'learnopsdev'),
    'password': os.environ.get('DB_PASSWORD', 'Admin8*'),
}

RABBITMQ_SETTINGS = {
    'host':     os.environ.get('RABBITMQ_HOST',     'localhost'),
    'port':     int(os.environ.get('RABBITMQ_PORT', 5672)),
    'user':     os.environ.get('RABBITMQ_USER',     'admin'),
    'password': os.environ.get('RABBITMQ_PASSWORD', 'admin123'),
}

# ---------------------------------------------------------------------------

def get_db_connection():
    """Return a new psycopg2 connection using the standalone DB settings."""
    return psycopg2.connect(**DB_SETTINGS)

def fetch_github_issues(source_repo, options):
    owner = source_repo['owner']
    repo  = source_repo['name']

    params = urllib.parse.urlencode({
        'state':    options.get('state', 'open'),
        'per_page': 100,
    })
    url = f"https://api.github.com/repos/{owner}/{repo}/issues?{params}"

    print(GITHUB_SETTINGS['token'])

    req = urllib.request.Request(url, headers={
        'Authorization':      f"Bearer {GITHUB_SETTINGS['token']}",
        'Accept':             'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    })

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())

def post_github_issue(target_repo, issue, options):
    """
    POST a single issue to the target repo.
    target_repo: {"owner": "...", "name": "..."}
    issue:       a single issue object from the source GET response
    options:     {"state": "open", "migrate_labels": True}
    """
    owner = target_repo['owner']
    repo  = target_repo['name']
    url   = f"https://api.github.com/repos/{owner}/{repo}/issues"

    payload = {
        'title': issue['title'],
        'body':  issue['body'] or '',
    }

    if options.get('migrate_labels') and issue.get('labels'):
        payload['labels'] = [label['name'] for label in issue['labels']]

    body_bytes = json.dumps(payload).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=body_bytes,               # presence of data= makes this a POST
        headers={
            'Authorization':          f"Bearer {GITHUB_SETTINGS['token']}",
            'Accept':                 'application/vnd.github+json',
            'Content-Type':           'application/json',
            'X-GitHub-Api-Version':   '2022-11-28',
        }
    )

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def process_message(job_id, data):
    """
    Simulate processing the job.
    In real implementation, this would call GitHub API, etc.
    Updates the poc_jobs table directly via psycopg2.
    """
    print(f"\n{'='*60}")
    print(f"🔄 Processing job: {job_id}")
    print(f"📦 Received data: {data}")
    print(f"{'='*60}\n")

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Verify the job exists
        cur.execute("SELECT id FROM poc_jobs WHERE id = %s", (job_id,))
        if cur.fetchone() is None:
            print(f"❌ Job {job_id} not found in database\n")
            return False

        # Update status to IN_PROGRESS
        cur.execute(
            "UPDATE poc_jobs SET status = %s, updated_at = NOW() WHERE id = %s",
            ('IN_PROGRESS', job_id)
        )
        conn.commit()
        print("✓ Updated job status to IN_PROGRESS")

        #print("⏳ Fetching GitHub issues...")
        issues = fetch_github_issues(data['source_repo'], data['options'])
        print(f"✓ Fetched {len(issues)} issues from GitHub")

        migrated = []
        for issue in issues:
            created = post_github_issue(data['target_repo'], issue, data['options'])
            migrated.append(created['number'])
            print(f"   ↳ Created issue #{created['number']}: {created['title']}")

        final_result = json.dumps({
            'completed_at':   datetime.now().isoformat(),
            'issue_count':    len(issues),
            'migrated_count': len(migrated),
            'migrated_ids':   migrated,
            'message':        'GitHub issues migrated successfully!'
        })

        cur.execute(
            "UPDATE poc_jobs SET status = %s, result_data = %s, updated_at = NOW() WHERE id = %s",
            ('COMPLETED', final_result, job_id)
        )
        conn.commit()

        print(f"✅ Job {job_id} completed successfully!\n")
        return True

    except Exception as e:
        print(f"❌ Error processing job: {e}\n")

        # Try to mark job as failed
        try:
            if conn:
                conn.rollback()
                cur = conn.cursor()
                error_result = json.dumps({'error': str(e)})
                cur.execute(
                    "UPDATE poc_jobs SET status = %s, result_data = %s, updated_at = NOW() WHERE id = %s",
                    ('FAILED', error_result, job_id)
                )
                conn.commit()
        except Exception:
            pass

        return False

    finally:
        if conn:
            conn.close()


def callback(ch, method, properties, body):
    """
    Callback function when message is received.
    """
    print("\n📨 Received message from RabbitMQ")

    try:
        # Parse message
        message = json.loads(body)
        job_id = message['job_id']
        data = message['data']

        # Process the job
        success = process_message(job_id, data)

        # Acknowledge message (remove from queue)
        if success:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print("✓ Message acknowledged and removed from queue")
        else:
            # Reject and don't requeue if processing failed
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            print("⚠ Message rejected (processing failed)")

    except Exception as e:
        print(f"❌ Error in callback: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    """
    Start the consumer and listen for messages.
    """
    print("\n" + "="*60)
    print("🐰 RabbitMQ POC Consumer Starting...")
    print("="*60 + "\n")

    # Connect to RabbitMQ using standalone settings
    credentials = pika.PlainCredentials(
        RABBITMQ_SETTINGS['user'],
        RABBITMQ_SETTINGS['password']
    )
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_SETTINGS['host'],
            port=RABBITMQ_SETTINGS['port'],
            credentials=credentials
        )
    )
    channel = connection.channel()

    # Declare queue (ensure it exists)
    channel.queue_declare(queue='poc_queue', durable=True)

    # Set QoS to process one message at a time
    channel.basic_qos(prefetch_count=1)

    # Set up consumer
    channel.basic_consume(
        queue='poc_queue',
        on_message_callback=callback
    )

    print("👂 Waiting for messages. Press Ctrl+C to exit.\n")

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down consumer...")
        channel.stop_consuming()

    connection.close()
    print("✓ Consumer stopped\n")


if __name__ == '__main__':
    main()
