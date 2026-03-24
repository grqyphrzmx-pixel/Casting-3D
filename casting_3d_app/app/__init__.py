"""
应用程序模块

提供应用程序的核心功能：
- main_application: 主应用程序类
"""

from .main_application import (
    MainApplication,
    ApplicationContext,
    ServiceLocator,
    create_application
)

__all__ = [
    'MainApplication',
    'ApplicationContext',
    'ServiceLocator',
    'create_application'
]
