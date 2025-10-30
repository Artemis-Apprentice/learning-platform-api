import sys
from django.contrib.auth.hashers import make_password
try:
    if len(sys.argv) != 2:
        sys.exit(1)
    
    password_hash = make_password(sys.argv[1])
 
except ImportError as e:
    sys.exit(1)
