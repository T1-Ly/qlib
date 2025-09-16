#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
危险品事故收集器包
Hazmat Accident Collector Package
"""

from .collector import (
    HazmatAccidentCollector,
    AccidentReport,
    AccidentDataExtractor,
    ProxyRotator,
    RateLimiter,
    RobotsChecker,
    WebScraper,
    BaseSearchEngine,
    DuckDuckGoSearchEngine
)

__version__ = "1.0.0"
__author__ = "Qlib Contributors"
__description__ = "危险品罐车事故报告收集器 - 用于动态发现和收集危险品事故报告"

__all__ = [
    'HazmatAccidentCollector',
    'AccidentReport', 
    'AccidentDataExtractor',
    'ProxyRotator',
    'RateLimiter',
    'RobotsChecker',
    'WebScraper',
    'BaseSearchEngine',
    'DuckDuckGoSearchEngine'
]