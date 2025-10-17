def check_state(state: dict, keys: set[str]) -> None:
    """
    Checking state whether keys exist or not

    Args:
        state: State that need to be checked.
        keys: Keys should be in the state.

    Returns:
        None

    Raises:
        RuntimeError: When there are any keys that are not in the state
    """
    missing_keys: set[str] = keys - set(state.keys())
    if len(missing_keys) > 0:
        raise RuntimeError(f"Invalid State (No Key: {", ".join(missing_keys)})")
