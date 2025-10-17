#!/usr/bin/env python3


def cat_n(file_path: str, start_line: int = 1) -> str:
    """Mimic the behavior of 'cat -n' command, displaying file content with line numbers.

    Args:
        file_path: Path to the file to be read
        start_line: Line number to start with (default: 1)

    Returns:
        A string containing the file content with line numbers
    """
    try:
        with open(file_path) as f:
            lines = f.readlines()
    except FileNotFoundError:
        return f"cat_n: {file_path}: No such file or directory"
    except IsADirectoryError:
        return f"cat_n: {file_path}: Is a directory"
    except PermissionError:
        return f"cat_n: {file_path}: Permission denied"
    except UnicodeDecodeError:
        return f"cat_n: {file_path}: Cannot display binary file"
    except Exception as e:
        return f"cat_n: {file_path}: Unknown error: {str(e)}"

    result = []
    for i, line in enumerate(lines):
        # Line number padded to 6 spaces, followed by a tab
        line_num = start_line + i
        result.append(f"{line_num:6d}\t{line.rstrip()}")

    return "\n".join(result)


def cat_n_at_line(file_path: str, target_line: int, context_lines: int = 0) -> str:
    """Display a specific line along with context lines before and after it, with line numbers.

    This is not an existing shell command, but a utility function that shows context
    around a specific line of code.

    Args:
        file_path: Path to the file to be read
        target_line: The specific line number to show (with context)
        context_lines: Number of lines to show before and after the target line (default: 0)

    Returns:
        A string containing the target line and its context (n lines before, n lines after)
        formatted like 'cat -n' output
    """
    try:
        with open(file_path) as f:
            lines = f.readlines()
    except FileNotFoundError:
        return f"cat_n_at_line: {file_path}: No such file or directory"
    except IsADirectoryError:
        return f"cat_n_at_line: {file_path}: Is a directory"
    except PermissionError:
        return f"cat_n_at_line: {file_path}: Permission denied"
    except UnicodeDecodeError:
        return f"cat_n_at_line: {file_path}: Cannot display binary file"
    except Exception as e:
        return f"cat_n_at_line: {file_path}: Unknown error: {str(e)}"

    if target_line < 1 or target_line > len(lines):
        return f"cat_n_at_line: {file_path}: Line number out of range"

    start_line_idx = max(0, target_line - context_lines - 1)
    end_line_idx = min(target_line + context_lines - 1, len(lines) - 1)

    result = []
    for line_idx in range(start_line_idx, end_line_idx + 1):
        line_content = lines[line_idx].rstrip()
        # Line number padded to 6 spaces, followed by a tab
        result.append(f"{line_idx + 1:6d}\t{line_content}")

    return "\n".join(result)


def hexdump_C(data: bytes) -> str:
    """Generate a hexdump similar to 'hexdump -C' format.

    Args:
        data: Bytes to be displayed in hexdump format.

    Returns:
        A string containing the formatted hexdump.

    Format:
    00000000  xx xx xx xx xx xx xx xx  xx xx xx xx xx xx xx xx  |ascii_representation|
    000000xx
    """
    result = []
    byte_count = len(data)

    for i in range(0, byte_count, 16):
        # Chunk: one line up to 16 bytes
        chunk = data[i : i + 16]

        addr = f"{i:08x}"

        # Format hex values
        hex_vals = []
        for j in range(0, len(chunk)):
            hex_vals.append(f"{chunk[j]:02x}")

        # Format the output based on whether we have >= 8 bytes or not
        if len(chunk) <= 8:
            hex_section = " ".join(hex_vals)
            # No special spacing for small chunks
        else:
            # Split into two sections for more than 8 bytes
            first_section = " ".join(hex_vals[:8])
            second_section = " ".join(hex_vals[8:])
            hex_section = f"{first_section} {second_section}"

        # ASCII representation
        ascii_chars = []
        for byte in chunk:
            # Printable ASCII range (32-126)
            if 32 <= byte <= 126:
                ascii_chars.append(chr(byte))
            else:
                ascii_chars.append(".")
        ascii_repr = "".join(ascii_chars)

        # Combine all parts
        line = f"{addr}  {hex_section}  |{ascii_repr}|"
        result.append(line)

    # Add the byte count at the end, matching hexdump -C format
    result.append(f"{byte_count:08x}")

    return "\n".join(result)
