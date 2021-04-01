#!/usr/bin/python3
# -*- coding: utf-8 -*-

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name = 'pixelblaze-async',
    version = "1.0.0",
    description = 'Asyncronous Library for Pixelblaze addressable LED controller.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    #url = 'https://github.com/zranger1/pixelblaze-client',
    author = 'Nick Waterton',
    license='MIT',
    classifiers=[
      "Development Status :: 4 - Beta",    
      "License :: OSI Approved :: MIT License",
      "Programming Language :: Python :: 3",
      "Operating System :: OS Independent",
      "Topic :: Software Development :: Libraries :: Python Modules",
      "Topic :: System :: Hardware",
      "Intended Audience :: Developers",
    ],
    keywords = 'pixelblaze',
    install_requires=["aiohttp", "paho-mqtt"],
    packages=["pixelblaze_async"],    
    python_requires='>=3.6',    
)