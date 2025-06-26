import sys
from django.contrib.auth.hashers import make_password
print ("this is the djangopass file")
try:
    if len(sys.argv) != 2:
        print("Usage: python djangopass.py <password>", file=sys.stderr)
        sys.exit(1)
    
    password_hash = make_password(sys.argv[1])
    print(password_hash)
    # sys.exit(0)
except ImportError as e:
    print(f"Error importing Django modules: {str(e)}", file=sys.stderr)
    sys.exit(1)
