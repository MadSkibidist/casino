import subprocess, os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
try:
    subprocess.run([
        "openssl","req","-x509","-newkey","rsa:2048",
        "-keyout","key.pem","-out","cert.pem",
        "-days","365","-nodes","-subj","/CN=localhost"
    ], check=True)
    print("cert.pem and key.pem created.")
except FileNotFoundError:
    print("openssl not found — server will fall back to plain TCP automatically.")
    sys.exit(1)