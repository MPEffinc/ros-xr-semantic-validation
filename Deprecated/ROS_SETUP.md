# ROS 2 Setup

Docker 설치 직후라면 한 번 로그아웃한 뒤 다시 로그인해 `docker` 그룹 권한을 반영한다.

## 1. 환경 Build

```bash
docker compose -f ros_env/compose.yaml build
```

## 2. Container 실행

```bash
docker compose -f ros_env/compose.yaml up -d
```

## 3. Container Shell 접속

```bash
docker compose -f ros_env/compose.yaml exec ros bash
```

## 4. ROS 환경 source

```bash
source /opt/ros/humble/setup.bash
```

## 5. 기본 동작 확인

두 개의 Container Shell에서 ROS 환경을 source한 뒤 각각 실행한다.

```bash
ros2 run demo_nodes_cpp talker
```

```bash
ros2 run demo_nodes_cpp listener
```

## 6. Container 종료

```bash
docker compose -f ros_env/compose.yaml down
```
