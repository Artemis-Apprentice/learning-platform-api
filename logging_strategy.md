# Logging Strategy: Implementing `structlog` in Django REST Framework API

This document outlines the step-by-step process for integrating `structlog` into the Django REST Framework API project to enable structured, context-aware logging.

## 1. Introduction to `structlog`

`structlog` is a powerful, modern logging library for Python that focuses on structured logging. Instead of traditional string-formatted log messages, `structlog` allows you to log key-value pairs, making logs easier to parse, filter, and analyze with tools like ELK stack, Splunk, or cloud logging services. `django-structlog` provides a convenient integration layer for Django projects.

## 2. Installation

Since this project runs within a Docker container and uses `pipenv` for dependency management, the installation process involves modifying the `Pipfile` and rebuilding the Docker image.

### 2.1 Add Dependencies to `Pipfile`

Add `structlog` and `django-structlog` to the `[packages]` section of your [`Pipfile`](Pipfile):

```toml
# Pipfile

[packages]
# ... existing packages
structlog = "*"
django-structlog = "*"
```

### 2.2 Update `Pipfile.lock` on Host Machine

After modifying the `Pipfile`, you **must** run `pipenv lock` on your host machine (outside the Docker container) to update the [`Pipfile.lock`](Pipfile.lock) file. This file pins the exact versions of your dependencies, ensuring consistent builds.

```bash
pipenv lock
```
**Note**: If `pipenv` is not installed on your host machine, you will need to install it first (e.g., `pip3 install pipenv`).

### 2.3 Rebuild Docker Image

Once `Pipfile.lock` is updated, rebuild your Docker image to include the newly added dependencies. This will ensure that `structlog` and `django-structlog` are available within your application's container.

```bash
docker compose build
docker compose up -d
```
Or, if you prefer to rebuild and run in one command:
```bash
docker compose up --build -d
```
The `-d` flag runs the containers in detached mode.

## 3. `settings.py` Configuration

Modify your [`LearningPlatform/settings.py`](LearningPlatform/settings.py) file as follows:

### 3.1 Add `django_structlog` to `INSTALLED_APPS`

Add `'django_structlog'` to your `INSTALLED_APPS` list:

```python
# LearningPlatform/settings.py

INSTALLED_APPS = [
    # ... existing apps
    'rest_framework',
    'django_structlog', # Add this line
    'LearningAPI',
]
```

### 3.2 Configure `STRUCTLOG_DEFAULTS`

Define `STRUCTLOG_DEFAULTS` to specify how `structlog` should process log entries. This includes processors for adding timestamps, log levels, event names, and rendering the output.

```python
# LearningPlatform/settings.py

# ... (existing settings)

# Structlog Configuration
STRUCTLOG_DEFAULTS = {
    "cache_logger_on_first_use": True,
    "wrapper_class": "structlog.make_filtering_bound_logger",
    "processors": [
        # Add shared processors for all loggers
        "structlog.stdlib.add_logger_name",
        "structlog.stdlib.add_log_level",
        "structlog.processors.TimeStamper",
        "structlog.processors.StackInfoRenderer",
        "structlog.processors.format_exc_info",
        "structlog.processors.CallsiteParameterAdder", # Adds module, funcname, lineno
        "structlog.dev.ConsoleRenderer" if DEBUG else "structlog.processors.JSONRenderer",
    ],
    "logger_factory": "structlog.stdlib.LoggerFactory",
    "find_caller_level": 2,
}

# Configure CallsiteParameterAdder to include specific parameters
# This should be a tuple of strings, e.g., ("filename", "lineno", "func_name", "module")
# For example, to add module, funcname, and lineno:
STRUCTLOG_DEFAULTS["processors"].insert(
    STRUCTLOG_DEFAULTS["processors"].index("structlog.processors.CallsiteParameterAdder") + 1,
    structlog.processors.CallsiteParameterAdder(
        {
            structlog.processors.CallsiteParameter.FILENAME,
            structlog.processors.CallsiteParameter.LINENO,
            structlog.processors.CallsiteParameter.FUNC_NAME,
            structlog.processors.CallsiteParameter.MODULE,
        }
    )
)
```
**Note**: You will need to import `structlog` at the top of `settings.py` for `structlog.processors.CallsiteParameter` to be available.

### 3.3 Modify the `LOGGING` Dictionary

Update the `LOGGING` dictionary to integrate `structlog`'s handlers and formatters.

```python
# LearningPlatform/settings.py

# ... (existing settings)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False, # Set to False to allow structlog to take over
    'formatters': {
        'json_formatter': {
            '()': 'structlog.stdlib.ProcessorFormatter',
            'processor': 'structlog.processors.JSONRenderer',
        },
        'console_formatter': {
            '()': 'structlog.stdlib.ProcessorFormatter',
            'processor': 'structlog.dev.ConsoleRenderer',
        },
        'standard': { # Keep existing standard formatter if needed for non-structlog logs
            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'console_formatter' if DEBUG else 'json_formatter', # Use structlog formatters
        },
        'logfile': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/debug.log'),
            'maxBytes': 50000,
            'backupCount': 2,
            'formatter': 'json_formatter', # Use structlog JSON formatter for file
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'INFO', # Adjust level as needed
        },
        'django.request': {
            'handlers': ['console', 'logfile'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console', 'logfile'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO', # Adjust level as needed
            'propagate': False,
        },
        'LearningPlatform': { # Your project's main logger
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
            'propagate': False, # Prevent double logging if root logger also handles
        },
        'structlog': { # This logger captures structlog output
            'handlers': ['console', 'logfile'],
            'level': 'INFO', # Set a default level for structlog
            'propagate': False,
        },
        '': { # Root logger
            'handlers': ['console', 'logfile'],
            'level': 'INFO', # Default level for anything not explicitly configured
        }
    }
}

# Configure structlog to use the standard library logging
structlog.configure(
    processors=STRUCTLOG_DEFAULTS["processors"],
    logger_factory=STRUCTLOG_DEFAULTS["logger_factory"],
    wrapper_class=STRUCTLOG_DEFAULTS["wrapper_class"],
    cache_logger_on_first_use=STRUCTLOG_DEFAULTS["cache_logger_on_first_use"],
)
```
**Note**: You will need to import `structlog` at the top of `settings.py`. Also, ensure `disable_existing_loggers` is `False` if you want `structlog` to integrate with existing loggers.

### 3.4 Add `django_structlog` Middleware (Optional but Recommended)

For request-specific context (e.g., request ID, user ID), add `django_structlog` middleware.

```python
# LearningPlatform/settings.py

MIDDLEWARE = [
    # ... existing middleware
    'django_structlog.middlewares.RequestMiddleware', # Add this line, preferably after AuthenticationMiddleware
    'django.middleware.security.SecurityMiddleware',
    # ... rest of middleware
]
```

## 4. Application Code Integration

To use `structlog` in your application code:

### 4.1 Get a `structlog` Logger

Instead of `logging.getLogger(__name__)`, use `structlog.get_logger()`:

```python
# In any Python file (e.g., LearningAPI/views/auth.py)

import structlog

logger = structlog.get_logger(__name__)

def my_function():
    logger.info("User activity", user_id=123, action="login", ip_address="192.168.1.1")
    try:
        # some operation
        raise ValueError("Something went wrong")
    except ValueError as e:
        logger.error("Operation failed", error=str(e), user_id=123, event="data_processing_error", exc_info=True)
```

#### Example: Logging Cohort Creation in `LearningAPI/views/cohort_view.py`

To log when a new cohort is created, you would modify the `create` method in [`LearningAPI/views/cohort_view.py`](LearningAPI/views/cohort_view.py) as follows:

```python
# LearningAPI/views/cohort_view.py

import structlog # Add this import at the top of the file

logger = structlog.get_logger(__name__) # Initialize the logger at the module level

class CohortViewSet(ViewSet):
    # ... existing code ...

    def create(self, request):
        # ... existing code to get client_side, server_side, and create cohort object ...

        try:
            cohort.save()
            logger.info(
                "Cohort created successfully",
                cohort_id=cohort.id,
                cohort_name=cohort.name,
                slack_channel=cohort.slack_channel,
                start_date=str(cohort.start_date),
                end_date=str(cohort.end_date),
                created_by=request.auth.user.username if request.auth.user.is_authenticated else 'anonymous',
                event="cohort_creation"
            )

            # ... existing code for assigning courses and returning response ...

        except IntegrityError as ex:
            logger.error(
                "Cohort creation failed due to integrity error",
                reason=str(ex),
                cohort_name=request.data.get("name"),
                slack_channel=request.data.get("slackChannel"),
                created_by=request.auth.user.username if request.auth.user.is_authenticated else 'anonymous',
                event="cohort_creation_failure",
                exc_info=True
            )
            if "cohort_name_key" in ex.args[0]:
                return Response({"reason": "Duplicate cohort name."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"reason": "Duplicate cohort Slack channel."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as ex:
            logger.error(
                "Cohort creation failed unexpectedly",
                reason=str(ex),
                cohort_name=request.data.get("name"),
                slack_channel=request.data.get("slackChannel"),
                created_by=request.auth.user.username if request.auth.user.is_authenticated else 'anonymous',
                event="cohort_creation_failure",
                exc_info=True
            )
            return Response({"reason": ex.args[0]}, status=status.HTTP_400_BAD_REQUEST)
```

### 4.2 Context-Aware Logging

`structlog` allows you to bind context to a logger, which means you can attach additional key-value pairs to a logger instance. These bound values will then be automatically included in all subsequent log messages generated by that specific bound logger. This is incredibly powerful for adding request-specific, user-specific, or transaction-specific information to your logs without having to explicitly pass those values to every single log call.

For example, in a web application, you might want to include a `request_id` or `user_id` in all logs related to a particular HTTP request. By binding these values once at the beginning of the request processing, all subsequent log messages within that request's scope will automatically carry this context, making it much easier to trace and debug issues.

The `django-structlog` middleware (if enabled as per section 3.4) automatically binds some request-specific context, but you can further enhance this by manually binding additional context in your views or service functions.

```python
# Example in a Django view or a function that processes a request

import structlog

def process_request(request):
    # Bind request-specific context
    request_logger = logger.bind(request_id=str(request.META.get('X-Request-ID', 'N/A')), user_id=request.user.id if request.user.is_authenticated else 'anonymous')

    request_logger.info("Processing incoming request", path=request.path)

    # ... perform operations ...

    request_logger.debug("Database query executed", query="SELECT * FROM users")
    return HttpResponse("OK")
```

## 5. Verification

After implementing, run your Django application and observe the logs.

### 5.1 Controlling the `DEBUG` Variable

The `DEBUG` setting in Django controls various aspects of your application's behavior, including how logs are formatted in this `structlog` setup.

In this project, the `DEBUG` variable is typically controlled via an environment variable, as seen in your [`LearningPlatform/settings.py`](LearningPlatform/settings.py) file:

```python
# LearningPlatform/settings.py
DEBUG = os.getenv("DEBUG", "False")
```

This means:
- To enable human-readable, colored console output (for development): Set the `DEBUG` environment variable to `"True"` (e.g., `DEBUG="True"`).
- To enable JSON formatted log entries (for production/staging): Ensure the `DEBUG` environment variable is not set, or set to `"False"` (e.g., `DEBUG="False"`).

You can set this environment variable in your shell before running the Django development server, or in your `docker-compose.yml` if you are using Docker.

### 5.2 Observing Log Output

- If `DEBUG` is `True`, you should see human-readable, colored output in your console.
- If `DEBUG` is `False`, your console and `logs/debug.log` file should contain JSON formatted log entries.
- Check that custom fields (e.g., `user_id`, `action`, `request_id`) are present in the log output.

This structured approach will greatly enhance the observability and debuggability of your Django application.