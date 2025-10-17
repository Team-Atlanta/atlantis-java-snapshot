ARG parent_image

FROM $parent_image 

ARG PROJECT_PATH

RUN mkdir -p /out/crs
COPY --from=project . /oss-fuzz-proj
COPY ./build.py /crs/build.py
CMD ["python3", "/crs/build.py"]
