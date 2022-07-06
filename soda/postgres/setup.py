#!/usr/bin/env python
import sys

from setuptools import find_namespace_packages, setup

if sys.version_info < (3, 8):
    print("Error: Soda SQL requires at least Python 3.8")
    print("Error: Please upgrade your Python version to 3.8 or later")
    sys.exit(1)

package_name = "soda_core-postgres"
package_version = "3.0.1"
# TODO Add proper description
description = "Soda Core Postgres Package"

requires = [f"soda_core=={package_version}", "psycopg2-binary>=2.8.5, <3.0"]
# TODO Fix the params
setup(
    name=package_name,
    version=package_version,
    install_requires=requires,
    packages=find_namespace_packages(include=["soda*"]),
)
