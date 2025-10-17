{
  description = "python devshell";

  inputs =
    {
      flake-utils.url = "github:numtide/flake-utils";
      nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    };

  outputs = { self, nixpkgs, flake-utils, ... }@inputs:
    flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = nixpkgs.legacyPackages.${system};
    in
    {
      devShells.default =
        pkgs.mkShell
          {
            nativeBuildInputs = with pkgs; [
              protobuf
              (nixpkgs.lib.hiPrio (python3.withPackages (python-pkgs: with python-pkgs; [
                # NOTE need to venv, pip install protoletariat
                # python3 -m venv --system-site-packages venv-nix
                virtualenv
                pip
                protobuf
                grpcio
                grpcio-tools
                pytest
                setuptools
                wheel
              ])))
            ];
            shellHook = ''
              export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib/
            '';
          };
    });
}
