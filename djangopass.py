import sys
from django.contrib.auth.hashers import make_password
try:
    if len(sys.argv) != 2:
        sys.exit(1)
    
    password_hash = make_password(sys.argv[1])
    print(password_hash)
 
except ImportError as e:
    print(f"Error importing Django modules: {str(e)}", file=sys.stderr)
    sys.exit(1)
