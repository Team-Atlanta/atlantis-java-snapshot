import grpc
from code_browser_client import CodeBrowserClient, CodeBrowserError, DEFAULT_SHARED_DIR
from argparse import ArgumentParser
from pathlib import Path

if __name__ == '__main__':
    parser = ArgumentParser()
    choices = ['build', 'function', 'xref', 'struct', 'enum', 'union', 'typedef', 'any_type']
    parser.add_argument('kind', help='Which query', choices=choices)
    parser.add_argument('name', help='Symbol name for query, or project path')
    parser.add_argument('--project', help='Name of project database')
    parser.add_argument('--force', help='Force rebuild', action='store_true')
    parser.add_argument('-a', '--address', help='Address of gRPC server')
    parser.add_argument('--shared', default=DEFAULT_SHARED_DIR, help='Path to shared FS')
    parser.add_argument('--relative', help='Return relative paths, otherwise absolute', action='store_true')

    args = parser.parse_args()


    try:
        # NOTE CodeBrowserClient will raise exception if server is not ready
        if args.address:
            client = CodeBrowserClient(args.address)
        else:
            client = CodeBrowserClient()

        match args.kind:
            case 'build':
                response = client.build(args.name, args.force, args.shared)
            case 'function':
                response = client.get_function_definition(args.name, project=args.project, relative=args.relative)
            case 'xref':
                response = client.get_function_cross_references(args.name, project=args.project, relative=args.relative)
            case 'struct':
                response = client.get_struct_definition(args.name, project=args.project, relative=args.relative)
            case 'enum':
                response = client.get_enum_definition(args.name, project=args.project, relative=args.relative)
            case 'union':
                response = client.get_union_definition(args.name, project=args.project, relative=args.relative)
            case 'typedef':
                response = client.get_typedef_definition(args.name, project=args.project, relative=args.relative)
            case 'any_type':
                response = client.get_any_type_definition(args.name, project=args.project, relative=args.relative)
        print(response)

    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.UNAVAILABLE:
            print("Code browser server unavailable:", e.details())
        elif e.code() == grpc.StatusCode.NOT_FOUND:
            print("Resource not found:", e.details())
        else:
            print("gRPC error:", e.code(), e.details())

    except CodeBrowserError as e:
        print("{}", e)
