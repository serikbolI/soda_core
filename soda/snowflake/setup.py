#!/usr/bin/env python
import sys

from setuptools import find_namespace_packages, setup

if sys.version_info < (3, 8):
    print("Error: Soda SQL requires at least Python 3.8")
    print("Error: Please upgrade your Python version to 3.8 or later")
    sys.exit(1)

package_name = "soda_core-snowflake"
package_version = "3.0.1"
description = "Soda Core Snowflake Package"

requires = [
    f"soda_core=={package_version}",
    "snowflake-connector-python~=2.7",
]
# TODO Fix the params
setup(
    name=package_name,
    version=package_version,
    install_requires=requires,
    packages=find_namespace_packages(include=["soda*"]),
)
