# C++ ZeroMQ Dealer Implementation

This is a C++ implementation of the dealer component using cppzmq. It mirrors the functionality of the Python version.

## Features

- Uses ZeroMQ DEALER socket to connect to a ROUTER
- Sends periodic heartbeats
- Processes SEED messages and sends ACK responses
- Maintains statistics on processed seeds
- Clean shutdown on interrupt signals

## Requirements

- C++17 compatible compiler
- CMake 3.10+
- ZeroMQ library [cppzmq](https://github.com/zeromq/cppzmq)
- nlohmann/json (fetched automatically via CMake)

## Building

```bash
mkdir -p build
cd build
cmake ..
make
```

## Usage

```bash
./dealer [--router ADDR] [--harness NAME] [--heartbeat SECONDS]
```

Options:
- `--router ADDR`: ZeroMQ router address (default: tcp://localhost:5555)
- `--harness NAME`: Harness name (default: Rdf4jOne)
- `--heartbeat SECONDS`: Heartbeat interval in seconds (default: 5)
- `--help`: Show usage information

## Example

```bash
./dealer --router tcp://192.168.1.100:5555 --harness CustomHarness --heartbeat 10
```
