"""Gunicorn production configuration for Exam Jingga DATH Stack CBT.

Optimized for Ubuntu 24.04 LTS ARM64 (4 vCPU / 24GB RAM) serving 722+ simultaneous students.
"""
import os
import multiprocessing

# Server socket binding (Port 8005 avoids collision with Kong on 8000)
bind = os.environ.get('GUNICORN_BIND', '127.0.0.1:8005')
backlog = 2048

# Worker processes and threading model
# gthread worker class allows high concurrency for I/O bound requests (HTMX polling, auto-save)
workers = int(os.environ.get('GUNICORN_WORKERS', 4))
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'gthread')
threads = int(os.environ.get('GUNICORN_THREADS', 4))
worker_connections = 1000

# Worker lifecycle and memory leak mitigation
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', 2000))
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', 400))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 120))
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', 5))
graceful_timeout = 30

# Process naming
proc_name = 'exam_jingga_gunicorn'

# Logging configuration
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')
errorlog = os.environ.get('GUNICORN_ERROR_LOG', '-')
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'
capture_output = True

# Server hooks
def on_starting(server):
    """Log server startup parameters."""
    server.log.info("Starting Exam Jingga Gunicorn server on %s (Workers: %s, Threads: %s)", bind, workers, threads)

def worker_int(worker):
    """Log worker termination."""
    worker.log.info("Worker received INT or QUIT signal (pid: %s)", worker.pid)

def worker_abort(worker):
    """Log worker abort."""
    worker.log.error("Worker received SIGABRT signal (pid: %s)", worker.pid)
