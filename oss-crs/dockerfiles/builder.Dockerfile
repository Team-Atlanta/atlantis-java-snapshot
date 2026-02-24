ARG target_base_image
FROM ${target_base_image}

COPY --from=libcrs . /libCRS
RUN /libCRS/install.sh

RUN mkdir -p /out/crs
RUN ln -s /project_dir /oss-fuzz-proj
COPY ./build.py /crs/build.py

CMD ["python3", "/crs/build.py"]
