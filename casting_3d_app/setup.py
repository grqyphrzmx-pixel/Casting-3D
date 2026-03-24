"""
Setup script for Casting Industry 2D to 3D Converter

This script handles the installation and packaging of the application.
"""

from setuptools import setup, find_packages
from pathlib import Path
import os

# Read README file
def read_readme():
    readme_path = Path(__file__).parent / "README.md"
    if readme_path.exists():
        return readme_path.read_text(encoding='utf-8')
    return ""

# Read requirements
def read_requirements():
    req_path = Path(__file__).parent / "requirements.txt"
    if req_path.exists():
        with open(req_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

# Package data
package_data = {
    'casting_3d_app': [
        'config/*.json',
        'resources/*.png',
        'resources/*.ico',
        'resources/*.qss',
    ],
}

# Entry points
entry_points = {
    'console_scripts': [
        'casting2d3d=casting_3d_app.main:main',
    ],
    'gui_scripts': [
        'casting2d3d-gui=casting_3d_app.main:main',
    ],
}

# Classifiers
classifiers = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Manufacturing',
    'Intended Audience :: End Users/Desktop',
    'Topic :: Scientific/Engineering :: CAD',
    'Topic :: Multimedia :: Graphics :: 3D Modeling',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Operating System :: OS Independent',
    'Environment :: X11 Applications :: Qt',
    'Environment :: Win32 (MS Windows)',
    'Environment :: MacOS X',
    'Natural Language :: English',
    'Natural Language :: Chinese (Simplified)',
]

setup(
    # Basic information
    name='casting-2d3d-converter',
    version='1.0.0',
    author='Casting Industry Solutions',
    author_email='support@casting2d3d.com',
    description='2D to 3D conversion tool for the casting industry',
    long_description=read_readme(),
    long_description_content_type='text/markdown',
    url='https://github.com/casting-industry/casting-2d3d-converter',
    
    # Packages
    packages=find_packages(),
    package_data=package_data,
    include_package_data=True,
    
    # Dependencies
    python_requires='>=3.8',
    install_requires=read_requirements(),
    
    # Optional dependencies
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'black>=22.0.0',
            'flake8>=5.0.0',
            'mypy>=0.991',
            'sphinx>=5.0.0',
        ],
        'gpu': [
            'cupy-cuda11x>=11.0.0',
        ],
        'cloud': [
            'boto3>=1.26.0',
            'azure-storage-blob>=12.14.0',
        ],
    },
    
    # Entry points
    entry_points=entry_points,
    
    # Classifiers
    classifiers=classifiers,
    
    # Keywords
    keywords='casting cad 3d-modeling stl step iges manufacturing',
    
    # Project URLs
    project_urls={
        'Bug Reports': 'https://github.com/casting-industry/casting-2d3d-converter/issues',
        'Source': 'https://github.com/casting-industry/casting-2d3d-converter',
        'Documentation': 'https://casting-2d3d-converter.readthedocs.io',
    },
    
    # License
    license='MIT',
    
    # Zip safe
    zip_safe=False,
)
