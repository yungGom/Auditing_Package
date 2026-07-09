"""OpenDART API 클라이언트 (수신 전용).

dart_benchmark_finder.py의 API 호출 코드를 모듈로 분리한 것 (패치 B-1).
"""
from .opendart import OpenDartClient, OpenDartError  # noqa: F401
