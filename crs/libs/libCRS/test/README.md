# LibCRS test suite

To run only the "fast" subset of tests (takes only a few seconds, useful for quick testing before each commit):

```sh
./run.sh
```

To run the full test suite (may be slow):

```sh
./run.sh --runslow
```

Any extra arguments are passed to pytest. You can use this to specify a particular module or test to run, [as explained in pytest's documentation](https://docs.pytest.org/en/stable/how-to/usage.html#specifying-which-tests-to-run).
