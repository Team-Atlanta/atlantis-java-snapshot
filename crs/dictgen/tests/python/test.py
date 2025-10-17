class bar:
    def __init__(self):
        pass


def foo(a, b, c):
    print("Hello, world!")
    bar()
    d = b
    if a == 0xBEAF:
        print("ok")
    elif d == "token1":
        print("ok2")
    baz("not_token")
    if not_parameter == "not_token2":
        pass
    data = c[10:16]
    if data in ("token2", "token3"):
        print("ok3")
