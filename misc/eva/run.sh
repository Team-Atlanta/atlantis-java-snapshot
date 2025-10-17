#export CRS_TARGET=aixcc/jvm/fuzzy
#cp /crs-workdir/beeps/test.list /crs-workdir/beeps/beep.list
#bash dev-run.sh
#mv /crs-workdir/worker-0 /crs-workdir/expkit-test

export CRS_TARGET=aixcc/jvm/fuzzy
cp /crs-workdir/beeps/fuzzy-cpv_0.list /crs-workdir/beeps/beep.list
bash dev-run.sh
mv /crs-workdir/worker-0 /crs-workdir/expkit-fuzzy-cpv_0

export CRS_TARGET=aixcc/jvm/jenkins
cp /crs-workdir/beeps/jenkins-cpv_5.list /crs-workdir/beeps/beep.list
bash dev-run.sh
mv /crs-workdir/worker-0 /crs-workdir/expkit-jenkins-cpv_5

export CRS_TARGET=aixcc/jvm/pac4j
cp /crs-workdir/beeps/pac4j-cpv_0.list /crs-workdir/beeps/beep.list
bash dev-run.sh
mv /crs-workdir/worker-0 /crs-workdir/expkit-pac4j-cpv_0

export CRS_TARGET=aixcc/jvm/r1-zookeeper
cp /crs-workdir/beeps/r1-zookeeper-cpv_3.list /crs-workdir/beeps/beep.list
bash dev-run.sh
mv /crs-workdir/worker-0 /crs-workdir/expkit-r1-zookeeper-cpv_3

export CRS_TARGET=aixcc/jvm/r1-zookeeper
cp /crs-workdir/beeps/r1-zookeeper-cpv_4.list /crs-workdir/beeps/beep.list
bash dev-run.sh
mv /crs-workdir/worker-0 /crs-workdir/expkit-r1-zookeeper-cpv_4

export CRS_TARGET=aixcc/jvm/r2-apache-commons-compress
cp /crs-workdir/beeps/r2-apache-commons-compress-cpv_3.list /crs-workdir/beeps/beep.list
bash dev-run.sh
mv /crs-workdir/worker-0 /crs-workdir/expkit-r2-apache-commons-compress-cpv_3

export CRS_TARGET=aixcc/jvm/rdf4j
cp /crs-workdir/beeps/rdf4j-cpv_2.list /crs-workdir/beeps/beep.list
bash dev-run.sh
mv /crs-workdir/worker-0 /crs-workdir/expkit-rdf4j-cpv_2

export CRS_TARGET=aixcc/jvm/tika
cp /crs-workdir/beeps/tika-cpv_0.list /crs-workdir/beeps/beep.list
bash dev-run.sh
mv /crs-workdir/worker-0 /crs-workdir/expkit-tika-cpv_0

