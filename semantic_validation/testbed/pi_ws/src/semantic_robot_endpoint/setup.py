from setuptools import find_packages, setup

package_name = 'semantic_robot_endpoint'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='cclab',
    maintainer_email='alex0888@inu.ac.kr',
    description=(
        'Robot-side dummy ROS 2 endpoint: subscribes to pose/odometry/tf '
        'commands and logs raw reception to JSONL. No actuator, no semantic '
        'gating.'
    ),
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'semantic_robot_sink = semantic_robot_endpoint.semantic_robot_sink:main',
        ],
    },
)
