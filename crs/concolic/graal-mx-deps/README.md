# MX cache for GraalVM

## SETUP

1. run script/build-jvm-ce-whole.sh from the concolic directory
2. copy out .mx contents to ./mx-cache
```bash
sudo ./copy-mx-files.py # requires root access to copy from volume
```
3. Docker build
```bash
sudo ./build.py <version> # (e.g., v1.0.0)
```

4. publish!

5. update Dockerfile.crs


