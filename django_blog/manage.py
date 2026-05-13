#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prepared_blog.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django import 실패. 의존성 설치 여부를 확인하세요 (도커 컨테이너 안에서 실행하세요)."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
