#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import threading as td
from .test_server import predict_tikv, predict_tidb


def main():
    try:
        # t1 = td.Thread(target=predict.start_predict, args=())
        # t1.start()
        t2 = td.Thread(target=predict_tikv.start_predict_cpu,
                       args=(sys.argv[-4], sys.argv[-3], sys.argv[-2], sys.argv[-1]))
        t2.start()
        # t3 = td.Thread(target=predict_tidb.start_predict_cpu, args=())
        # t3.start()
        # t4 = td.Thread(target=predict_tidb.start_predict_cpu,
        #                args=(sys.argv[-4], sys.argv[-3], sys.argv[-2], sys.argv[-1]))
        # t4.start()

    except:
        print("Error: Unable to start thread.")

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_server.settings')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv[:-4])


if __name__ == '__main__':
    main()
