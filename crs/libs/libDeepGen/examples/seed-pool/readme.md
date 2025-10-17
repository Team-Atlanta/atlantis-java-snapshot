```
# build
$ javac SeedShmemPoolConsumer.java ShmConsumer.java

# run python script to create shm and upload seed file
$ python3.12 shm_producer.py

(libdeepgen) javacrs@javacrs-fuzz-1:/data/workspace/libDeepGen/examples/jvm$ python3.12 shm_producer.py
JINA_API_KEY not found
[+] created shared memory 'test-seed-shm-pool'
Enter file path to upload (blank / q to quit)
path> /data/workspace/libDeepGen/examples/jvm/ShmConsumer.class
[OK] seed_id=0  shm_name=test-seed-shm-pool  sha256=dde3ce04ee3a2f9a02354609d7841c45d4021222db884cb032fa8a343e082c49
path>

# run java script to dump seed file 
$ java ShmConsumer test-seed-shm-pool 0

(libdeepgen) javacrs@javacrs-fuzz-1:/data/workspace/libDeepGen/examples/jvm$ java ShmConsumer test-seed-shm-pool 0
length = 2833 bytes
sha256 = dde3ce04ee3a2f9a02354609d7841c45d4021222db884cb032fa8a343e082c49
00000000  ca fe ba be 00 00 00 3d  00 9b 0a 00 02 00 03 07  |.......=........|
00000010  00 04 0c 00 05 00 06 01  00 10 6a 61 76 61 2f 6c  |..........java/l|
00000020  61 6e 67 2f 4f 62 6a 65  63 74 01 00 06 3c 69 6e  |ang/Object...<in|
00000030  69 74 3e 01 00 03 28 29  56 08 00 08 01 00 07 53  |it>...()V......S|
...

# build C++ consumer (requires OpenSSL development libraries)
$ cd cpp
$ make

# run C++ script to dump seed file
$ ./ShmConsumer test-seed-shm-pool 0

length = 2833 bytes
sha256 = dde3ce04ee3a2f9a02354609d7841c45d4021222db884cb032fa8a343e082c49
00000000  ca fe ba be 00 00 00 3d  00 9b 0a 00 02 00 03 07  |.......=........|
00000010  00 04 0c 00 05 00 06 01  00 10 6a 61 76 61 2f 6c  |..........java/l|
00000020  61 6e 67 2f 4f 62 6a 65  63 74 01 00 06 3c 69 6e  |ang/Object...<in|
00000030  69 74 3e 01 00 03 28 29  56 08 00 08 01 00 07 53  |it>...()V......S|
...
```
