cmake_minimum_required(VERSION 3.8)
project(origin_test)

find_package(ament_cmake REQUIRED)

install(
  PROGRAMS scripts/origin_test.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME origin_test
)

install(
  PROGRAMS scripts/quest_tcp_probe.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME quest_tcp_probe
)

ament_package()
