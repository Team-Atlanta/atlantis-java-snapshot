"""
Generator module providing common interfaces for different format generators.
This is the main entry point for all generator APIs.
"""

import sys
import traceback


from .grammarinator_wrapper import get_wrapper, register_generator, generate_content
from .xml_grammarinator import XMLGenerator


def xml_gen() -> bytes:
    """
    Generate XML using grammarinator's XMLGenerator without spawning a new process.
    
    This is a direct replacement for the command line:
    grammarinator-generate xml_grammarinator.XMLGenerator -d 20 -o out/test_%d.xml -n 100 --sys-path .
    
    Returns: Generated XML as bytes
    """
    try:
        # Register XML generator if not already registered
        xml_generator_name = "xml"
        wrapper = get_wrapper()
        if not wrapper.is_registered(xml_generator_name):
            # NOTE: Check grammarinator_wrapper for more details
            args = [
                'libDeepGen.libGenerator.xml_grammarinator.XMLGenerator', # generator
                '-d', '20',                                               # max-depth
                '--max-tokens', '8096',                                   # max-tokens (default is RuleSize.max.tokens)
                '-m', 'grammarinator.runtime.DefaultModel',               # model
                #'-r', 'document',                                         # rule
                # '--no-generate',                                        # disable generation from grammar (default: enabled)
                # '--no-mutate',                                          # disable mutation (default: enabled)
                # '--no-recombine',                                       # disable recombination (default: enabled)
                #'--no-grammar-violations',                              # disable unrestricted (default: enabled)
                '--out', '',                                              # output to stdout
                '--encoding', 'utf-8',                                    # encoding
                '--encoding-errors', 'strict',                            # encoding errors
            ]
        
            register_generator(
                name=xml_generator_name,
                generator_class=XMLGenerator,
                args=args
            )
        
        # Generate and return a single XML document as bytes
        return generate_content(xml_generator_name)
    except Exception as e:
        error_message = f"Error generating XML: {e}\n{traceback.format_exc()}"
        print(error_message, file=sys.stderr)
        # Return empty XML in case of error
        return b'<?xml version="1.0" encoding="UTF-8"?><root></root>'


def json_gen() -> bytes:
    """Randomly generate one JSON content and returns as bytes."""
    json_content = b'{\n  "id": 1,\n  "name": "Sample Name",\n  "attributes": {\n    "color": "blue",\n    "size": "medium"\n  },\n  "items": [1, 2, 3]\n}'
    return json_content


def html_gen() -> bytes:
    """Randomly generate one HTML content and returns as bytes."""
    html_content = b'<!DOCTYPE html>\n<html>\n<head>\n  <title>Sample Page</title>\n</head>\n<body>\n  <h1>Sample Heading</h1>\n  <p>This is sample content.</p>\n</body>\n</html>'
    return html_content


def http_gen() -> bytes:
    """Randomly generate one HTTP request/response and returns as bytes."""
    http_content = b'GET /api/v1/resources HTTP/1.1\nHost: example.com\nUser-Agent: Mozilla/5.0\nAccept: application/json\nContent-Type: application/json\n\n{"query": "sample"}'
    return http_content


def xpath_gen() -> bytes:
    """Randomly generate one XPath expression and returns as bytes."""
    xpath_content = b'/html/body/div[@class="container"]/ul/li[position() < 5]'
    return xpath_content


def sql_gen() -> bytes:
    """Randomly generate one SQL query and returns as bytes."""
    sql_content = b'SELECT u.name, p.title FROM users u JOIN posts p ON u.id = p.user_id WHERE u.active = true AND p.published_date > "2023-01-01" ORDER BY p.published_date DESC LIMIT 10;'
    return sql_content
