CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -pedantic -O2
LDFLAGS = -lcrypto

TARGET = ShmConsumer
OBJS = ShmConsumer.o SeedShmemPoolConsumer.o

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

ShmConsumer.o: ShmConsumer.cpp SeedShmemPoolConsumer.h
	$(CXX) $(CXXFLAGS) -c $<

SeedShmemPoolConsumer.o: SeedShmemPoolConsumer.cpp SeedShmemPoolConsumer.h
	$(CXX) $(CXXFLAGS) -c $<

clean:
	rm -f $(TARGET) $(OBJS)

.PHONY: all clean